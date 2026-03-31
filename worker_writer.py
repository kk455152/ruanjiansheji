# worker_writer.py
import pika, json, os
from mq_config import get_connection, EXCHANGE_NAME

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        # 根据数据类型自动分拣到不同文件
        data_type = data.get("type", "unknown")
        file_name = f"db_{data_type}.json"
        
        with open(file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        print(f" 💾 [写入模块] 已存入本地文件: {file_name}")
    except Exception as e:
        print(f" ❌ [写入失败]: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

conn = get_connection()
ch = conn.channel()
ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
q = ch.queue_declare(queue='writer_v2', durable=True)
ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)

ch.basic_consume(queue='writer_v2', on_message_callback=callback)
print(' [*] 写入模块已启动，正在持久化数据...')
ch.start_consuming()