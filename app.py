import atexit
import hashlib
import json
import os
import queue
import tempfile
import threading
import time

import pika
from flask import Flask, jsonify, request

from mq_config import EXCHANGE_NAME, get_connection
from security_utils import TOKEN_SALT, decrypt_data

app = Flask(__name__)
_TEMP_PEM_FILES = []


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
            self._channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type='fanout',
                durable=True,
            )

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
        item = {'body': serialized, 'attempt': 1}
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            return False

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
                        self._queue.put_nowait({'body': body, 'attempt': attempt + 1})
                    except queue.Full:
                        app.logger.error('Gateway publish queue is full while retrying a message.')
                else:
                    app.logger.error('Gateway dropped a message after %s publish attempts.', attempt)
            finally:
                self._queue.task_done()


dispatcher = BufferedMessageDispatcher()
dispatcher.start()
atexit.register(dispatcher.stop)


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
    return response


@app.route('/api/bass', methods=['POST'])
@app.route('/api/signal', methods=['POST'])
@app.route('/api/volume', methods=['POST'])
@app.route('/api/status/connection', methods=['POST'])
@app.route('/api/status/like', methods=['POST'])
def handle_simulator_data():
    request_json = request.get_json(silent=True)
    if not isinstance(request_json, dict):
        return jsonify({'status': 'error', 'message': 'Invalid JSON Payload'}), 400

    auth_token = request.headers.get('Authorization')
    timestamp = request_json.get('timestamp')
    data_decrypted, error_msg = validate_and_decrypt(request_json, auth_token, timestamp)
    if error_msg:
        return jsonify({'status': 'error', 'message': error_msg}), 401

    data_decrypted['api_path'] = request.path
    if not dispatcher.submit(data_decrypted):
        return jsonify({'status': 'error', 'message': 'Gateway queue is busy, please retry'}), 503

    return jsonify({
        'status': 'success',
        'message': f'Verified data from {request.path} queued for broker delivery',
    }), 200


if __name__ == '__main__':
    cert_path = normalize_pem_file('cert.pem', '-----BEGIN CERTIFICATE-----', '-----END CERTIFICATE-----')
    key_path = normalize_pem_file('key.pem', '-----BEGIN PRIVATE KEY-----', '-----END PRIVATE KEY-----')
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('APP_PORT', '443')),
        threaded=True,
        ssl_context=(cert_path, key_path),
    )
