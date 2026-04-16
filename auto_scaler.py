import math
import glob
import json
import os
import signal
import time

import docker
import requests
import urllib3
from docker.errors import APIError, NotFound
from docker.types import Mount


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GATEWAY_METRICS_URL = os.environ.get('GATEWAY_METRICS_URL', 'https://gateway/internal/metrics')
GATEWAY_METRICS_FILE = os.environ.get('GATEWAY_METRICS_FILE', '/runtime/gateway_metrics.json')
GATEWAY_METRICS_FILE_PATTERN = os.environ.get('GATEWAY_METRICS_FILE_PATTERN')
GATEWAY_METRICS_STALE_SECONDS = float(os.environ.get('GATEWAY_METRICS_STALE_SECONDS', '15'))
RABBITMQ_QUEUE_API = os.environ.get(
    'MQ_QUEUE_API',
    os.environ.get('MQ_MANAGEMENT_URL', 'http://8.137.165.220:15672/api/queues/%2f/writer_v2'),
)
AUTH = (
    os.environ.get('MQ_USER', 'migrate'),
    os.environ.get('MQ_PASSWORD', '2728'),
)

BASE_CONTAINER_NAME = os.environ.get(
    'SCALE_BASE_CONTAINER',
    'smart-speaker-full-deploy_worker-writer_1',
)
SCALE_CONTAINER_PREFIX = os.environ.get('SCALE_CONTAINER_PREFIX', 'smart-speaker-autoscale-writer')
ROLE_LABEL = os.environ.get('SCALE_ROLE_LABEL', 'smart-speaker.worker-writer.autoscaled')

MIN_WORKERS = int(os.environ.get('SCALE_MIN_WORKERS', '1'))
MAX_WORKERS = int(os.environ.get('SCALE_MAX_WORKERS', '5'))
CHECK_INTERVAL = float(os.environ.get('SCALE_CHECK_INTERVAL', '5'))
COOLDOWN_SECONDS = float(os.environ.get('SCALE_COOLDOWN_SECONDS', '20'))
DOWN_STABLE_CHECKS = int(os.environ.get('SCALE_DOWN_STABLE_CHECKS', '3'))

UP_BACKLOG = int(os.environ.get('SCALE_UP_BACKLOG', '50'))
DOWN_BACKLOG = int(os.environ.get('SCALE_DOWN_BACKLOG', '10'))
UP_PUBLISH_RATE = float(os.environ.get('SCALE_UP_PUBLISH_RATE', '20'))
DOWN_PUBLISH_RATE = float(os.environ.get('SCALE_DOWN_PUBLISH_RATE', '5'))

TARGET_RATE_PER_WORKER = float(os.environ.get('SCALE_TARGET_RATE_PER_WORKER', '15'))
TARGET_BACKLOG_PER_WORKER = int(os.environ.get('SCALE_TARGET_BACKLOG_PER_WORKER', '40'))


def log(message):
    print(f'[auto-scaler] {message}', flush=True)


def get_queue_metrics():
    response = requests.get(RABBITMQ_QUEUE_API, auth=AUTH, timeout=8)
    response.raise_for_status()
    payload = response.json()
    message_stats = payload.get('message_stats') or {}
    publish_details = message_stats.get('publish_details') or {}
    ack_details = message_stats.get('ack_details') or {}
    deliver_details = message_stats.get('deliver_get_details') or {}

    return {
        'messages': int(payload.get('messages', 0) or 0),
        'ready': int(payload.get('messages_ready', 0) or 0),
        'unacked': int(payload.get('messages_unacknowledged', 0) or 0),
        'publish_rate': float(publish_details.get('rate', 0) or 0),
        'ack_rate': float(ack_details.get('rate', 0) or 0),
        'deliver_rate': float(deliver_details.get('rate', 0) or 0),
    }


def get_gateway_metrics():
    response = requests.get(GATEWAY_METRICS_URL, timeout=8, verify=False)
    response.raise_for_status()
    payload = response.json()
    accepted_rate = float(payload.get('accepted_per_second', 0) or 0)
    dispatcher_queue_size = int(payload.get('dispatcher_queue_size', 0) or 0)
    return {
        'messages': dispatcher_queue_size,
        'ready': dispatcher_queue_size,
        'unacked': 0,
        'publish_rate': accepted_rate,
        'ack_rate': 0.0,
        'deliver_rate': accepted_rate,
    }


def load_fresh_gateway_metrics_payloads():
    paths = []
    if GATEWAY_METRICS_FILE_PATTERN:
        paths.extend(glob.glob(GATEWAY_METRICS_FILE_PATTERN))
    elif GATEWAY_METRICS_FILE:
        paths.append(GATEWAY_METRICS_FILE)

    payloads = []
    seen = set()
    now = time.time()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)

        try:
            with open(path, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        updated_at = float(payload.get('updated_at', 0) or 0)
        if now - updated_at <= GATEWAY_METRICS_STALE_SECONDS:
            payloads.append(payload)

    return payloads


def get_gateway_file_metrics():
    payloads = load_fresh_gateway_metrics_payloads()
    if not payloads:
        return {
            'messages': 0,
            'ready': 0,
            'unacked': 0,
            'publish_rate': 0.0,
            'ack_rate': 0.0,
            'deliver_rate': 0.0,
        }

    accepted_rate = sum(float(payload.get('accepted_per_second', 0) or 0) for payload in payloads)
    dispatcher_queue_size = sum(int(payload.get('dispatcher_queue_size', 0) or 0) for payload in payloads)
    return {
        'messages': dispatcher_queue_size,
        'ready': dispatcher_queue_size,
        'unacked': 0,
        'publish_rate': accepted_rate,
        'ack_rate': 0.0,
        'deliver_rate': accepted_rate,
    }


def get_traffic_metrics():
    try:
        metrics = get_gateway_file_metrics()
        metrics['source'] = 'gateway-file'
        return metrics
    except Exception as file_exc:
        log(f'gateway metrics file unavailable: {file_exc}; trying gateway HTTP metrics')

    try:
        metrics = get_gateway_metrics()
        metrics['source'] = 'gateway'
        return metrics
    except Exception as gateway_exc:
        log(f'gateway metrics unavailable: {gateway_exc}; falling back to RabbitMQ queue metrics')
        metrics = get_queue_metrics()
        metrics['source'] = 'rabbitmq'
        return metrics


def get_docker_client():
    return docker.from_env()


def get_base_container(client):
    return client.containers.get(BASE_CONTAINER_NAME)


def list_autoscaled_containers(client):
    containers = client.containers.list(
        all=True,
        filters={'label': f'{ROLE_LABEL}=true'},
    )
    return sorted(containers, key=lambda item: item.name)


def get_running_worker_count(client):
    base_running = 0
    try:
        base = get_base_container(client)
        base.reload()
        base_running = 1 if base.status == 'running' else 0
    except NotFound:
        base_running = 0

    autoscaled_running = 0
    for container in list_autoscaled_containers(client):
        container.reload()
        if container.status == 'running':
            autoscaled_running += 1

    return base_running + autoscaled_running


def find_next_container_name(client):
    existing_names = {container.name for container in list_autoscaled_containers(client)}
    for index in range(1, MAX_WORKERS + 10):
        name = f'{SCALE_CONTAINER_PREFIX}-{index}'
        if name not in existing_names:
            return name
    raise RuntimeError('Unable to allocate a new autoscaled worker container name')


def build_mounts_from_base(base_container):
    mounts = []
    for item in base_container.attrs.get('Mounts', []):
        if item.get('Type') != 'bind':
            continue
        mounts.append(
            Mount(
                target=item['Destination'],
                source=item['Source'],
                type='bind',
                read_only=not item.get('RW', True),
            )
        )
    return mounts


def get_primary_network(base_container):
    networks = base_container.attrs.get('NetworkSettings', {}).get('Networks', {})
    if not networks:
        return None
    return next(iter(networks.keys()))


def start_extra_worker(client):
    base = get_base_container(client)
    base.reload()
    image = base.attrs['Config']['Image']
    command = base.attrs['Config'].get('Cmd')
    env = base.attrs['Config'].get('Env') or []
    mounts = build_mounts_from_base(base)
    network = get_primary_network(base)
    name = find_next_container_name(client)

    log(f'starting extra writer worker: {name}')
    client.containers.run(
        image=image,
        command=command,
        name=name,
        detach=True,
        environment=env,
        labels={
            ROLE_LABEL: 'true',
            'smart-speaker.autoscaled': 'true',
            'smart-speaker.role': 'worker-writer',
        },
        mounts=mounts,
        network=network,
        restart_policy={'Name': 'always'},
    )


def stop_extra_worker(client):
    containers = list_autoscaled_containers(client)
    if not containers:
        return False

    container = containers[-1]
    log(f'stopping extra writer worker: {container.name}')
    try:
        container.stop(timeout=10)
    except APIError as exc:
        log(f'failed to stop {container.name}: {exc}')
        kill_container_process(container)
    try:
        container.remove(force=True)
    except APIError as exc:
        log(f'failed to remove {container.name}: {exc}')
        kill_container_process(container)
        try:
            container.remove(force=True)
        except APIError as remove_exc:
            log(f'failed to remove {container.name} after pid kill: {remove_exc}')
            return False
    return True


def kill_container_process(container):
    try:
        container.reload()
        pid = int(container.attrs.get('State', {}).get('Pid') or 0)
    except Exception as exc:
        log(f'failed to inspect {container.name} pid: {exc}')
        return False

    if pid <= 0:
        log(f'{container.name} has no running host pid to kill')
        return False

    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        log(f'killed host pid {pid} for {container.name}')
        return True
    except PermissionError as exc:
        log(f'permission denied killing host pid {pid} for {container.name}: {exc}')
    except ProcessLookupError:
        log(f'host pid {pid} for {container.name} already exited')
        return True
    except OSError as exc:
        log(f'failed to kill host pid {pid} for {container.name}: {exc}')
    return False


def calculate_desired_count(metrics, current_workers, low_traffic_cycles):
    messages = metrics['messages']
    publish_rate = metrics['publish_rate']

    high_pressure = messages >= UP_BACKLOG or publish_rate >= UP_PUBLISH_RATE
    low_pressure = messages <= DOWN_BACKLOG and publish_rate <= DOWN_PUBLISH_RATE

    if high_pressure:
        by_rate = math.ceil(publish_rate / TARGET_RATE_PER_WORKER) if publish_rate > 0 else MIN_WORKERS
        by_backlog = math.ceil(messages / TARGET_BACKLOG_PER_WORKER) if messages > 0 else MIN_WORKERS
        desired = max(current_workers + 1, by_rate, by_backlog, MIN_WORKERS)
        return min(MAX_WORKERS, max(MIN_WORKERS, desired)), 0

    if low_pressure:
        low_traffic_cycles += 1
        if low_traffic_cycles >= DOWN_STABLE_CHECKS:
            return max(MIN_WORKERS, current_workers - 1), 0
        return current_workers, low_traffic_cycles

    return current_workers, 0


def apply_scale(client, desired_count):
    current_count = get_running_worker_count(client)
    if desired_count == current_count:
        return current_count

    if desired_count > current_count:
        for _ in range(desired_count - current_count):
            start_extra_worker(client)
    else:
        for _ in range(current_count - desired_count):
            if not stop_extra_worker(client):
                break

    return get_running_worker_count(client)


def main():
    log(f'watching gateway metrics file: {GATEWAY_METRICS_FILE}')
    if GATEWAY_METRICS_FILE_PATTERN:
        log(f'watching gateway metrics file pattern: {GATEWAY_METRICS_FILE_PATTERN}')
    log(f'watching gateway metrics: {GATEWAY_METRICS_URL}')
    log(f'fallback RabbitMQ queue metrics: {RABBITMQ_QUEUE_API}')
    log(f'scaling worker-writer containers between {MIN_WORKERS} and {MAX_WORKERS}')

    client = get_docker_client()
    low_traffic_cycles = 0
    last_scale_at = 0.0

    while True:
        try:
            metrics = get_traffic_metrics()
            current_workers = get_running_worker_count(client)
            desired_workers, low_traffic_cycles = calculate_desired_count(
                metrics,
                current_workers,
                low_traffic_cycles,
            )

            log(
                'source={source} messages={messages} ready={ready} unacked={unacked} '
                'publish_rate={publish_rate:.2f}/s ack_rate={ack_rate:.2f}/s '
                'deliver_rate={deliver_rate:.2f}/s workers={workers} desired={desired}'.format(
                    **metrics,
                    workers=current_workers,
                    desired=desired_workers,
                )
            )

            now = time.time()
            if desired_workers != current_workers:
                if now - last_scale_at >= COOLDOWN_SECONDS:
                    final_count = apply_scale(client, desired_workers)
                    last_scale_at = now
                    log(f'scale operation completed: workers={final_count}')
                else:
                    log('scale skipped during cooldown window')
        except Exception as exc:
            log(f'monitoring error: {exc}')

        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
