import atexit
from collections import deque
import hashlib
import json
import os
import queue
import glob
import tempfile
import threading
import time

import pika
from flask import Flask, jsonify, render_template, request

from mq_config import EXCHANGE_NAME, declare_exchange, get_connection
from security_utils import TOKEN_SALT, decrypt_data
from storage_backends import persist_payload
from daily_stats_job import run_daily_stats_once

# =========================
# Flask App
# =========================
app = Flask(__name__)

# =========================
# 注册数据库查询 API 接口
# 这些文件现在都在项目根目录，所以直接这样 import
# =========================
from auth_routes import auth_bp
from device_routes import device_bp
from stats_routes import stats_bp
from mongo_routes import mongo_bp
from api_routes import api_bp
from c_observe_routes import c_observe_bp
from admin_routes import admin_bp, admin_compat_bp
from db_api_service import db_api
app.register_blueprint(auth_bp)
app.register_blueprint(device_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(mongo_bp)
app.register_blueprint(api_bp)
app.register_blueprint(c_observe_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_compat_bp)
app.register_blueprint(db_api)
# =========================
# 原来的网关配置，不要乱改
# =========================
_TEMP_PEM_FILES = []

METRICS_WINDOW_SECONDS = float(os.environ.get('GATEWAY_METRICS_WINDOW_SECONDS', '10'))
METRICS_FILE = os.environ.get('GATEWAY_METRICS_FILE', '/runtime/gateway_metrics.json')
METRICS_FILE_PATTERN = os.environ.get('GATEWAY_METRICS_FILE_PATTERN')
METRICS_MULTIPROCESS = os.environ.get('GATEWAY_METRICS_MULTIPROCESS', 'false').lower() in (
    '1',
    'true',
    'yes',
    'on'
)
METRICS_FLUSH_INTERVAL = float(os.environ.get('GATEWAY_METRICS_FLUSH_INTERVAL', '1'))

_metrics_lock = threading.Lock()
_accepted_timestamps = deque()


def _cleanup_temp_pems():
    for path in _TEMP_PEM_FILES:
        try:
            os.remove(path)
        except OSError:
            pass


atexit.register(_cleanup_temp_pems)


def normalize_pem_file(path, begin_marker, end_marker):
    with open(path, 'r', encoding='ascii') as file:
        content = file.read().strip()

    if content.startswith('-----BEGIN'):
        return path

    fd, temp_path = tempfile.mkstemp(suffix='.pem')
    with os.fdopen(fd, 'w', encoding='ascii', newline='\n') as file:
        file.write(f'{begin_marker}\n{content}\n{end_marker}\n')

    _TEMP_PEM_FILES.append(temp_path)
    return temp_path


class RabbitPublisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._lock = threading.Lock()

    def _close_unlocked(self):
        channel = self._channel
        connection = self._connection
        self._channel = None
        self._connection = None

        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._close_unlocked()

    def _ensure_channel_unlocked(self):
        if self._connection and self._connection.is_closed:
            self._close_unlocked()

        if self._channel and self._channel.is_closed:
            self._close_unlocked()

        if self._channel is None:
            self._connection = get_connection()
            self._channel = self._connection.channel()
            declare_exchange(self._channel)

        return self._channel

    def publish(self, body):
        with self._lock:
            channel = self._ensure_channel_unlocked()
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key='',
                body=body,
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2,
                ),
            )


class BufferedMessageDispatcher:
    def __init__(self):
        self.maxsize = int(os.environ.get('GATEWAY_QUEUE_MAXSIZE', '2000'))
        self.max_retries = int(os.environ.get('GATEWAY_PUBLISH_RETRIES', '5'))
        self.retry_delay = float(os.environ.get('GATEWAY_PUBLISH_RETRY_DELAY', '1.5'))

        self._queue = queue.Queue(maxsize=self.maxsize)
        self._publisher = RabbitPublisher()
        self._stop_event = threading.Event()

        self._worker = threading.Thread(
            target=self._run,
            name='gateway-publisher',
            daemon=True,
        )

        self._started = False
        self._start_lock = threading.Lock()

    def start(self):
        with self._start_lock:
            if not self._started:
                self._worker.start()
                self._started = True

    def stop(self):
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

        self._publisher.close()

    def submit(self, payload):
        self.start()

        serialized = json.dumps(payload, ensure_ascii=False)
        item = {
            'body': serialized,
            'attempt': 1
        }

        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            return False

    def queue_size(self):
        return self._queue.qsize()

    def _run(self):
        while not self._stop_event.is_set():
            item = self._queue.get()

            if item is None:
                self._queue.task_done()
                continue

            body = item['body']
            attempt = item['attempt']

            try:
                self._publisher.publish(body)

            except Exception as exc:
                app.logger.warning(
                    'Broker publish attempt %s failed: %s',
                    attempt,
                    exc,
                )

                self._publisher.close()

                if attempt < self.max_retries and not self._stop_event.is_set():
                    time.sleep(self.retry_delay)

                    try:
                        self._queue.put_nowait({
                            'body': body,
                            'attempt': attempt + 1
                        })
                    except queue.Full:
                        app.logger.error(
                            'Gateway publish queue is full while retrying a message.'
                        )
                else:
                    app.logger.error(
                        'Gateway dropped a message after %s publish attempts.',
                        attempt
                    )

            finally:
                self._queue.task_done()


dispatcher = BufferedMessageDispatcher()
dispatcher.start()
atexit.register(dispatcher.stop)


def _trim_metric_window(now):
    cutoff = now - METRICS_WINDOW_SECONDS

    while _accepted_timestamps and _accepted_timestamps[0] < cutoff:
        _accepted_timestamps.popleft()


def record_accepted_request():
    now = time.time()

    with _metrics_lock:
        _accepted_timestamps.append(now)
        _trim_metric_window(now)


def get_gateway_metrics():
    now = time.time()

    with _metrics_lock:
        _trim_metric_window(now)
        accepted_count = len(_accepted_timestamps)

    window = max(METRICS_WINDOW_SECONDS, 1.0)

    return {
        'updated_at': now,
        'accepted_per_second': accepted_count / window,
        'accepted_in_window': accepted_count,
        'window_seconds': METRICS_WINDOW_SECONDS,
        'dispatcher_queue_size': dispatcher.queue_size(),
        'pid': os.getpid(),
    }


def get_metrics_write_path():
    if not METRICS_MULTIPROCESS:
        return METRICS_FILE

    base, ext = os.path.splitext(METRICS_FILE)
    return f'{base}.{os.getpid()}{ext or ".json"}'


def aggregate_gateway_metrics():
    pattern = METRICS_FILE_PATTERN or METRICS_FILE
    paths = glob.glob(pattern)

    if not paths and METRICS_FILE:
        paths = [METRICS_FILE]

    now = time.time()
    accepted_count = 0
    dispatcher_queue_size = 0
    latest_updated_at = 0.0
    process_count = 0

    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                payload = json.load(file)

        except (OSError, json.JSONDecodeError):
            continue

        updated_at = float(payload.get('updated_at', 0) or 0)

        if now - updated_at > max(METRICS_WINDOW_SECONDS * 2, 15.0):
            continue

        accepted_count += int(payload.get('accepted_in_window', 0) or 0)
        dispatcher_queue_size += int(payload.get('dispatcher_queue_size', 0) or 0)
        latest_updated_at = max(latest_updated_at, updated_at)
        process_count += 1

    window = max(METRICS_WINDOW_SECONDS, 1.0)

    return {
        'updated_at': latest_updated_at or now,
        'accepted_per_second': accepted_count / window,
        'accepted_in_window': accepted_count,
        'window_seconds': METRICS_WINDOW_SECONDS,
        'dispatcher_queue_size': dispatcher_queue_size,
        'process_count': process_count,
    }


def write_gateway_metrics_file():
    if not METRICS_FILE:
        return

    metrics_path = get_metrics_write_path()
    metrics_dir = os.path.dirname(metrics_path)

    if metrics_dir:
        os.makedirs(metrics_dir, exist_ok=True)

    tmp_path = f'{metrics_path}.tmp'

    with open(tmp_path, 'w', encoding='utf-8') as file:
        json.dump(get_gateway_metrics(), file, ensure_ascii=False)

    os.replace(tmp_path, metrics_path)


def gateway_metrics_writer():
    while True:
        try:
            write_gateway_metrics_file()

        except Exception as exc:
            app.logger.warning(
                'Failed to write gateway metrics file: %s',
                exc
            )

        time.sleep(METRICS_FLUSH_INTERVAL)


threading.Thread(
    target=gateway_metrics_writer,
    name='gateway-metrics-writer',
    daemon=True,
).start()


def daily_stats_scheduler():
    enabled = os.environ.get('DAILY_STATS_AUTO_UPDATE', 'true').lower() in (
        '1',
        'true',
        'yes',
        'on',
    )
    if not enabled:
        return

    interval = int(os.environ.get('DAILY_STATS_INTERVAL_SECONDS', str(24 * 60 * 60)))
    generate_count = int(os.environ.get('DAILY_STATS_GENERATE_COUNT', '50'))
    auto_demo_data = os.environ.get('DAILY_STATS_AUTO_DEMO_DATA', 'true').lower() in (
        '1',
        'true',
        'yes',
        'on',
    )
    while True:
        try:
            result = run_daily_stats_once(
                generate_count=generate_count,
                skip_seed=auto_demo_data,
                skip_generate=auto_demo_data,
                generate_demo_data=auto_demo_data,
                demo_user_count=int(os.environ.get('DAILY_STATS_DEMO_USER_COUNT', '36')),
                demo_device_count=int(os.environ.get('DAILY_STATS_DEMO_DEVICE_COUNT', '19')),
                demo_order_count=int(os.environ.get('DAILY_STATS_DEMO_ORDER_COUNT', '28')),
                demo_play_count=int(os.environ.get('DAILY_STATS_DEMO_PLAY_COUNT', '8600')),
            )
            app.logger.info('daily_stats auto update finished: %s', result)
        except Exception as exc:
            app.logger.warning('daily_stats auto update failed: %s', exc)
        time.sleep(max(interval, 60))


threading.Thread(
    target=daily_stats_scheduler,
    name='daily-stats-scheduler',
    daemon=True,
).start()


def validate_and_decrypt(request_json, auth_token, timestamp):
    if not timestamp:
        return None, 'Missing Timestamp'

    raw_string = f'{TOKEN_SALT}{timestamp}'
    expected_token = hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    if auth_token != expected_token:
        return None, 'Unauthorized: Invalid Token'

    encrypted_payload = request_json.get('data')

    if not encrypted_payload:
        return None, 'Missing Payload'

    decrypted_dict = decrypt_data(encrypted_payload)

    if not decrypted_dict:
        return None, 'Decryption Failed: Illegal data or Key mismatch'

    return decrypted_dict, None


@app.after_request
def ensure_connection_close(response):
    response.headers['Connection'] = 'close'
    response.headers['Access-Control-Allow-Origin'] = os.environ.get(
        'CORS_ALLOW_ORIGIN',
        '*'
    )
    response.headers['Access-Control-Allow-Methods'] = (
        'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    )
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type,Authorization'
    )
    return response


# =========================
# 原有模拟器 / 设备上报接口
# 这些接口不要和前端查询接口混在一起
# =========================
@app.route('/api/bass', methods=['POST'])
@app.route('/api/signal', methods=['POST'])
@app.route('/api/volume', methods=['POST'])
@app.route('/api/status/connection', methods=['POST'])
@app.route('/api/status/like', methods=['POST'])
@app.route('/api/song-info', methods=['POST'])
@app.route('/api/runtime', methods=['POST'])
@app.route('/api/player/state', methods=['POST'])
@app.route('/api/play-queue', methods=['POST'])
@app.route('/api/bind-progress', methods=['POST'])
@app.route('/api/music-sync/progress', methods=['POST'])
def handle_simulator_data():
    request_json = request.get_json(silent=True)

    if not isinstance(request_json, dict):
        return jsonify({
            'status': 'error',
            'message': 'Invalid JSON Payload'
        }), 400

    auth_token = request.headers.get('Authorization')
    timestamp = request_json.get('timestamp')

    data_decrypted, error_msg = validate_and_decrypt(
        request_json,
        auth_token,
        timestamp
    )

    if error_msg:
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 401

    data_decrypted['timestamp'] = int(timestamp)
    data_decrypted['api_path'] = request.path

    if data_decrypted.get('type') in (
        'song_info',
        '歌曲信息',
        '姝屾洸淇℃伅'
    ):
        try:
            backend_name = persist_payload(data_decrypted)

        except Exception as exc:
            app.logger.error(
                'Song info persistence failed: %s',
                exc
            )

            return jsonify({
                'status': 'error',
                'message': 'Song info persistence failed'
            }), 502

        record_accepted_request()

        return jsonify({
            'status': 'success',
            'message': f'Verified song info from {request.path} persisted via {backend_name}',
        }), 200

    if not dispatcher.submit(data_decrypted):
        return jsonify({
            'status': 'error',
            'message': 'Gateway queue is busy, please retry'
        }), 503

    record_accepted_request()

    return jsonify({
        'status': 'success',
        'message': f'Verified data from {request.path} queued for broker delivery',
    }), 200


@app.route('/internal/metrics', methods=['GET'])
def internal_metrics():
    if METRICS_MULTIPROCESS:
        return jsonify(aggregate_gateway_metrics()), 200

    return jsonify(get_gateway_metrics()), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'code': 200,
        'msg': 'ok'
    }), 200


@app.route('/api/db/daily-stats/run', methods=['POST'])
def run_daily_stats_now():
    body = request.get_json(silent=True) or {}
    try:
        result = run_daily_stats_once(
            date_value=body.get('date'),
            generate_count=int(body.get('generate_count') or os.environ.get('DAILY_STATS_GENERATE_COUNT', '50')),
            skip_seed=bool(body.get('skip_seed', False)),
            skip_generate=bool(body.get('skip_generate', False)),
            keywords=body.get('keywords'),
            generate_demo_data=bool(body.get('generate_demo_data', False)),
            demo_user_count=int(body.get('demo_user_count') or os.environ.get('DAILY_STATS_DEMO_USER_COUNT', '36')),
            demo_device_count=int(body.get('demo_device_count') or os.environ.get('DAILY_STATS_DEMO_DEVICE_COUNT', '19')),
            demo_order_count=int(body.get('demo_order_count') or os.environ.get('DAILY_STATS_DEMO_ORDER_COUNT', '28')),
            demo_play_count=int(body.get('demo_play_count') or body.get('generate_count') or os.environ.get('DAILY_STATS_DEMO_PLAY_COUNT', '8600')),
            reset_demo_data=bool(body.get('reset_demo_data', False)),
        )
        return jsonify({'status': 'success', 'data': result}), 200
    except Exception as exc:
        app.logger.warning('manual daily_stats update failed: %s', exc)
        return jsonify({'status': 'error', 'message': str(exc)}), 500


@app.route('/db-admin', methods=['GET'])
@app.route('/api/db-admin', methods=['GET'])
def db_admin_page():
    return render_template('db_admin.html')


if __name__ == '__main__':
    cert_path = normalize_pem_file(
        'cert.pem',
        '-----BEGIN CERTIFICATE-----',
        '-----END CERTIFICATE-----'
    )

    key_path = normalize_pem_file(
        'key.pem',
        '-----BEGIN PRIVATE KEY-----',
        '-----END PRIVATE KEY-----'
    )

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('APP_PORT', '443')),
        threaded=True,
        ssl_context=(cert_path, key_path),
    )

