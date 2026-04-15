import os

from gunicorn.app.base import BaseApplication

from app import app, normalize_pem_file


class GatewayApplication(BaseApplication):
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


def main():
    cert_path = normalize_pem_file(
        'cert.pem',
        '-----BEGIN CERTIFICATE-----',
        '-----END CERTIFICATE-----',
    )
    key_path = normalize_pem_file(
        'key.pem',
        '-----BEGIN PRIVATE KEY-----',
        '-----END PRIVATE KEY-----',
    )

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
