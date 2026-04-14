# mq_config.py
import os

import pika

MQ_HOST = os.environ.get('MQ_HOST', '8.137.165.220')
MQ_PORT = int(os.environ.get('MQ_PORT', '5672'))
MQ_USER = os.environ.get('MQ_USER', 'migrate')
MQ_PASSWORD = os.environ.get('MQ_PASSWORD', '2728')

def get_connection():
    """统一获取 RabbitMQ 连接"""
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASSWORD)

    parameters = pika.ConnectionParameters(
        host=MQ_HOST,
        port=MQ_PORT,
        credentials=credentials,
        heartbeat=600,          # 保持长连接
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

# 交换机和队列定义
EXCHANGE_NAME = 'smart_speaker_exchange'
RAW_DATA_QUEUE = 'speaker_data'
