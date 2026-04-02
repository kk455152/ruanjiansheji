# mq_config.py
import pika

def get_connection():
    """统一获取 RabbitMQ 连接"""
    # 使用你提供的公网 IP 和 凭据
    credentials = pika.PlainCredentials('migrate', '2728')
    parameters = pika.ConnectionParameters(
        host='8.137.165.220', 
        port=5672, 
        credentials=credentials,
        heartbeat=600,          # 保持长连接
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

# 定义交换机名称（广播模式，确保 5 个模块都能同时收到数据）
EXCHANGE_NAME = 'smart_speaker_exchange'
# 定义原始数据队列名称
RAW_DATA_QUEUE = 'speaker_data'