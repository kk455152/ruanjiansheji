import os

try:
    from gunicorn.app.base import BaseApplication
except ModuleNotFoundError:
    BaseApplication = None

from app import app, normalize_pem_file


_GunicornBase = BaseApplication if BaseApplication is not None else object


class GatewayApplication(_GunicornBase):
    def __init__(self, application, options=None):
        self.options = options or {}
        self.application = application
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key, value)

    def load(self):
        return self.application


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


def run_with_flask():
    cert_path, key_path = get_ssl_paths()
    port = int(os.environ.get('APP_PORT', '443'))
    print('[gateway] Gunicorn unavailable in this environment, falling back to Flask dev server.')
    app.run(
        host='0.0.0.0',
        port=port,
        ssl_context=(cert_path, key_path),
    )


def main():
    if BaseApplication is None or os.name == 'nt':
        run_with_flask()
        return

    cert_path, key_path = get_ssl_paths()

    options = {
        'bind': f"0.0.0.0:{os.environ.get('APP_PORT', '443')}",
        'workers': int(os.environ.get('GUNICORN_WORKERS', '2')),
        'threads': int(os.environ.get('GUNICORN_THREADS', '4')),
        'worker_class': 'gthread',
        'timeout': int(os.environ.get('GUNICORN_TIMEOUT', '60')),
        'graceful_timeout': int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30')),
        'certfile': cert_path,
        'keyfile': key_path,
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': os.environ.get('GUNICORN_LOG_LEVEL', 'info'),
    }

    GatewayApplication(app, options).run()


if __name__ == '__main__':
    main()
