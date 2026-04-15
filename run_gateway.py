import os
import ssl

from app import app, normalize_pem_file
from werkzeug.serving import make_server


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


def run_with_local_https_server():
    cert_path, key_path = get_ssl_paths()
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = int(os.environ.get('APP_PORT', '443'))
    default_processes = '4' if os.name != 'nt' and host == '0.0.0.0' else '1'
    processes = max(1, int(os.environ.get('APP_PROCESSES', default_processes)))
    threaded = processes == 1
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_path, key_path)

    server = make_server(
        host,
        port,
        app,
        threaded=threaded,
        processes=processes,
        ssl_context=ssl_context,
    )
    print(f'[gateway] HTTPS gateway listening at https://{host}:{port}', flush=True)
    if host == '0.0.0.0':
        print('[gateway] Bound to all interfaces for remote access.', flush=True)
    if threaded:
        print('[gateway] Running in threaded mode.', flush=True)
    else:
        print(f'[gateway] Running with {processes} worker processes.', flush=True)
    print('[gateway] Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[gateway] Local gateway stopped.', flush=True)


def main():
    run_with_local_https_server()


if __name__ == '__main__':
    main()
