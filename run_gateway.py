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
    host = os.environ.get('APP_HOST', '0.0.0.0')
    port = int(os.environ.get('APP_PORT', '443'))
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_path, key_path)

    server = make_server(
        host,
        port,
        app,
        threaded=True,
        ssl_context=ssl_context,
    )
    print(f'[gateway] HTTPS gateway listening at https://{host}:{port}', flush=True)
    print('[gateway] Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[gateway] Local gateway stopped.', flush=True)


def main():
    run_with_local_https_server()


if __name__ == '__main__':
    main()
