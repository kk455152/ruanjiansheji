# mq_config.py
import pika
import os

def get_connection():
    """统一获取 RabbitMQ 连接"""
    # 💡 核心修改：如果是 Docker 运行，host 会从环境变量读取 'rabbitmq'
    # 如果是本地直接跑，则使用你原来的公网 IP
    mq_host = os.environ.get('MQ_HOST', '8.137.165.220')
    
    # 凭据保持不变
    credentials = pika.PlainCredentials('migrate', '2728')
    
    parameters = pika.ConnectionParameters(
        host=mq_host, 
        port=5672, 
        credentials=credentials,
        heartbeat=600,          # 保持长连接
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

# 交换机和队列定义
EXCHANGE_NAME = 'smart_speaker_exchange'
RAW_DATA_QUEUE = 'speaker_data'
