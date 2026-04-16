import atexit
import os
import socket
import ssl
import tempfile

import werkzeug.serving as serving
from werkzeug.serving import WSGIRequestHandler, make_server

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


class StableTLSRequestHandler(WSGIRequestHandler):
    protocol_version = 'HTTP/1.0'

    def setup(self):
        super().setup()
        timeout = float(os.environ.get('APP_CLIENT_TIMEOUT', '15'))
        self.connection.settimeout(timeout)


def get_ssl_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = normalize_pem_file(
        os.path.join(base_dir, 'cert.pem'),
        '-----BEGIN CERTIFICATE-----',
        '-----END CERTIFICATE-----',
    )
    key_path = normalize_pem_file(
        os.path.join(base_dir, 'key.pem'),
        '-----BEGIN PRIVATE KEY-----',
        '-----END PRIVATE KEY-----',
    )
    return cert_path, key_path


def get_runtime_host():
    return os.environ.get('APP_HOST', '127.0.0.1')


def get_runtime_port():
    return int(os.environ.get('APP_PORT', '443'))


def get_listen_queue():
    return int(os.environ.get('APP_LISTEN_QUEUE', '1024'))


def get_gateway_workers():
    return int(os.environ.get('GATEWAY_WORKERS', os.environ.get('WEB_CONCURRENCY', '4')))


def get_gateway_threads():
    return int(os.environ.get('GATEWAY_THREADS', '8'))


def get_display_host(host):
    return '127.0.0.1' if host == '0.0.0.0' and os.name == 'nt' else host


def build_ssl_context(cert_path, key_path):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if hasattr(ssl, 'TLSVersion'):
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    if hasattr(ssl, 'OP_NO_COMPRESSION'):
        ssl_context.options |= ssl.OP_NO_COMPRESSION
    if hasattr(ssl, 'OP_NO_RENEGOTIATION'):
        ssl_context.options |= ssl.OP_NO_RENEGOTIATION
    ssl_context.load_cert_chain(cert_path, key_path)
    return ssl_context


def configure_server_queue(listen_queue):
    for class_name in ('BaseWSGIServer', 'ThreadedWSGIServer'):
        server_class = getattr(serving, class_name, None)
        if server_class is not None:
            server_class.request_queue_size = listen_queue


def run_with_stable_https_server():
    from app import app

    cert_path, key_path = get_ssl_paths()
    host = get_runtime_host()
    port = get_runtime_port()
    display_host = get_display_host(host)
    listen_queue = get_listen_queue()
    ssl_context = build_ssl_context(cert_path, key_path)
    configure_server_queue(listen_queue)

    server = make_server(
        host,
        port,
        app,
        threaded=True,
        request_handler=StableTLSRequestHandler,
        ssl_context=ssl_context,
    )
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    server.socket.listen(listen_queue)

    print(f'[gateway] HTTPS gateway listening at https://{display_host}:{port}', flush=True)
    if host == '0.0.0.0':
        print('[gateway] Bound to all interfaces for remote access.', flush=True)
    print('[gateway] Running in stable threaded TLS mode.', flush=True)
    print(f'[gateway] TLS listen queue size: {listen_queue}', flush=True)
    print('[gateway] Keep-alive is disabled per request to avoid long-lived TLS stalls.', flush=True)
    print('[gateway] Press Ctrl+C to stop.', flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[gateway] Local gateway stopped.', flush=True)


def run_with_gunicorn():
    try:
        import gunicorn.app.wsgiapp  # noqa: F401
    except ImportError:
        print('[gateway] Gunicorn unavailable, falling back to stable Werkzeug HTTPS server.', flush=True)
        run_with_stable_https_server()
        return

    cert_path, key_path = get_ssl_paths()
    host = get_runtime_host()
    port = get_runtime_port()
    workers = get_gateway_workers()
    threads = get_gateway_threads()
    listen_queue = get_listen_queue()

    args = [
        'gunicorn',
        'app:app',
        '--bind',
        f'{host}:{port}',
        '--worker-class',
        'gthread',
        '--workers',
        str(workers),
        '--threads',
        str(threads),
        '--backlog',
        str(listen_queue),
        '--timeout',
        os.environ.get('GATEWAY_TIMEOUT', '30'),
        '--graceful-timeout',
        os.environ.get('GATEWAY_GRACEFUL_TIMEOUT', '30'),
        '--keep-alive',
        os.environ.get('GATEWAY_KEEP_ALIVE', '2'),
        '--certfile',
        cert_path,
        '--keyfile',
        key_path,
        '--access-logfile',
        '-',
        '--error-logfile',
        '-',
        '--log-level',
        os.environ.get('GATEWAY_LOG_LEVEL', 'info'),
    ]

    print(
        f'[gateway] Starting Gunicorn HTTPS gateway on https://{get_display_host(host)}:{port} '
        f'with workers={workers}, threads={threads}, backlog={listen_queue}',
        flush=True,
    )
    os.execvp('gunicorn', args)


def main():
    if os.environ.get('GATEWAY_USE_GUNICORN', 'true').lower() in ('1', 'true', 'yes', 'on'):
        run_with_gunicorn()
    else:
        run_with_stable_https_server()


if __name__ == '__main__':
    main()
