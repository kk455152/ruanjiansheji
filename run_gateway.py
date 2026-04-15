import os

from app import app, normalize_pem_file


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


def run_with_local_https_server():
    cert_path, key_path = get_ssl_paths()
    host = get_runtime_host()
    port = get_runtime_port()
    display_host = get_display_host(host)

    print(f'[gateway] HTTPS gateway listening at https://{display_host}:{port}', flush=True)
    if host == '0.0.0.0':
        print('[gateway] Bound to all interfaces for remote access.', flush=True)
    print('[gateway] Running in threaded Flask HTTPS mode.', flush=True)
    print('[gateway] Press Ctrl+C to stop.', flush=True)
    try:
        # Keep the launcher dependency-light and compatible across Windows and Linux.
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
            ssl_context=(cert_path, key_path),
        )
    except KeyboardInterrupt:
        print('\n[gateway] Local gateway stopped.', flush=True)


def main():
    run_with_local_https_server()


if __name__ == '__main__':
    main()
