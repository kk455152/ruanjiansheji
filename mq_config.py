import os

import pika

MQ_HOST = os.environ.get('MQ_HOST', '8.137.165.220')
MQ_PORT = int(os.environ.get('MQ_PORT', '5672'))
MQ_USER = os.environ.get('MQ_USER', 'migrate')
MQ_PASSWORD = os.environ.get('MQ_PASSWORD', '2728')
MQ_HEARTBEAT = int(os.environ.get('MQ_HEARTBEAT', '600'))
MQ_SOCKET_TIMEOUT = float(os.environ.get('MQ_SOCKET_TIMEOUT', '10'))
MQ_BLOCKED_TIMEOUT = float(os.environ.get('MQ_BLOCKED_TIMEOUT', '30'))
MQ_CONNECTION_ATTEMPTS = int(os.environ.get('MQ_CONNECTION_ATTEMPTS', '3'))
MQ_RETRY_DELAY = float(os.environ.get('MQ_RETRY_DELAY', '2'))
MQ_EXCHANGE_DURABLE = os.environ.get('MQ_EXCHANGE_DURABLE', 'false').lower() == 'true'

EXCHANGE_NAME = 'smart_speaker_exchange'
RAW_DATA_QUEUE = 'speaker_data'


def build_connection_parameters():
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASSWORD)
    return pika.ConnectionParameters(
        host=MQ_HOST,
        port=MQ_PORT,
        credentials=credentials,
        heartbeat=MQ_HEARTBEAT,
        socket_timeout=MQ_SOCKET_TIMEOUT,
        blocked_connection_timeout=MQ_BLOCKED_TIMEOUT,
        connection_attempts=MQ_CONNECTION_ATTEMPTS,
        retry_delay=MQ_RETRY_DELAY,
        client_properties={
            'connection_name': os.environ.get('MQ_CONNECTION_NAME', 'smart-speaker-app'),
        },
    )


def get_connection():
    return pika.BlockingConnection(build_connection_parameters())


def declare_exchange(channel):
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type='fanout',
        durable=MQ_EXCHANGE_DURABLE,
    )
