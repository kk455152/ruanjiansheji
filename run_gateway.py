import os
import socket
import ssl

from werkzeug.serving import WSGIRequestHandler, make_server

from app import app, normalize_pem_file


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


def get_display_host(host):
    return '127.0.0.1' if host == '0.0.0.0' and os.name == 'nt' else host


def build_ssl_context(cert_path, key_path):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if hasattr(ssl, 'TLSVersion'):
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.load_cert_chain(cert_path, key_path)
    return ssl_context


def run_with_stable_https_server():
    cert_path, key_path = get_ssl_paths()
    host = get_runtime_host()
    port = get_runtime_port()
    display_host = get_display_host(host)
    ssl_context = build_ssl_context(cert_path, key_path)

    server = make_server(
        host,
        port,
        app,
        threaded=True,
        request_handler=StableTLSRequestHandler,
        ssl_context=ssl_context,
    )
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    print(f'[gateway] HTTPS gateway listening at https://{display_host}:{port}', flush=True)
    if host == '0.0.0.0':
        print('[gateway] Bound to all interfaces for remote access.', flush=True)
    print('[gateway] Running in stable threaded TLS mode.', flush=True)
    print('[gateway] Keep-alive is disabled per request to avoid long-lived TLS stalls.', flush=True)
    print('[gateway] Press Ctrl+C to stop.', flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[gateway] Local gateway stopped.', flush=True)


def main():
    run_with_stable_https_server()


if __name__ == '__main__':
    main()
