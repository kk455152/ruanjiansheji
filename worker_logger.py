# worker_logger.py
import pika, json, datetime
from mq_config import get_connection, EXCHANGE_NAME

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_text = f"[{timestamp}] Device: {data.get('device_id')} | Action: Upload {data.get('type')}\n"
        
        with open("system_access.log", "a", encoding="utf-8") as f:
            f.write(log_text)
        print(f" 📝 [日志模块] 流水记录成功")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

conn = get_connection()
ch = conn.channel()
ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
q = ch.queue_declare(queue='logger_v2', durable=True)
ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)

ch.basic_consume(queue='logger_v2', on_message_callback=callback)
print(' [*] 日志模块已启动...')
ch.start_consuming()