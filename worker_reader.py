# worker_reader.py
import pika
from mq_config import get_connection, EXCHANGE_NAME, RAW_DATA_QUEUE

def start_reader():
    conn = get_connection()
    ch = conn.channel()
    
    # 确保交换机存在
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
    # 确保原始队列存在
    ch.queue_declare(queue=RAW_DATA_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        print(f" [读取模块] 📥 成功抓取原始数据包: {body.decode()}")
        # 将读到的数据广播给其他所有模块
        ch.basic_publish(exchange=EXCHANGE_NAME, routing_key='', body=body)
        # 确认读取成功
        ch.basic_ack(delivery_tag=method.delivery_tag)

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=RAW_DATA_QUEUE, on_message_callback=callback)
    
    print(' [*] 读取模块启动成功，正在搬运数据...')
    ch.start_consuming()

if __name__ == "__main__":
    start_reader()