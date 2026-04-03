# worker_writer.py
import pika, json, os
from mq_config import get_connection, EXCHANGE_NAME

PROJECT_TOKEN = "smart_speaker_2026"

# 🔴 运维修改：使用绝对路径，确保文件生成位置固定
# 注意：请确保运行程序的用户（如 jenkins 或 root）对该目录有写入权限
DB_DIR = "/www/wwwroot/mysite/data_db"

if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR, exist_ok=True)
        print(f" 📂 [运维提示] 已自动创建绝对路径存储目录: {DB_DIR}")
    except Exception as e:
        print(f" ❌ [权限报错] 无法创建目录，请检查权限: {e}")

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        
        if data.get("token") != PROJECT_TOKEN:
            return
        
        dev_id = data.get("device_id", "unknown_device")
        api_type = data.get("type", "others")
        
        # 嵌套路径：/www/wwwroot/mysite/data_db/设备ID/接口名.json
        dev_path = os.path.join(DB_DIR, dev_id)
        if not os.path.exists(dev_path):
            os.makedirs(dev_path, exist_ok=True)
            
        file_path = os.path.join(dev_path, f"{api_type}.json")

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        print(f" 💾 [STORAGE] 写入成功 | 路径: {file_path}")

    except Exception as e:
        print(f" ❌ [ERROR] 写入异常: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

# MQ 初始化逻辑保持不变...
try:
    conn = get_connection()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
    q = ch.queue_declare(queue='writer_v2', durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue='writer_v2', on_message_callback=callback)
    print(f' [*] 写入模块就绪 | 目标目录: {DB_DIR} | 等待流量...')
    ch.start_consuming()
except Exception as conn_err:
    print(f" 🚨 [CRITICAL] 无法连接到 RabbitMQ: {conn_err}")
