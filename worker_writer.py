# worker_writer.py
import pika, json, os
from mq_config import get_connection, EXCHANGE_NAME

# 与 validator 模块保持一致的身份密钥
PROJECT_TOKEN = "smart_speaker_2026"

# 🔴 云端运维微调：定义数据存储根目录
DB_DIR = "data_db"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
    print(f" 📂 [运维提示] 已在云端自动创建存储目录: {DB_DIR}")

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        
        # 1. 身份校验
        if data.get("token") != PROJECT_TOKEN:
            # 这里的输出会被 Jenkins 捕获，方便 A 监控非法请求
            print(f" ⚠️ [SECURITY] 拦截非法 Token | 设备: {data.get('device_id', 'Unknown')}")
            return

        # 2. 获取设备ID和类型
        dev_id = data.get("device_id", "unknown_device")
        data_type = data.get("type", "data")
        
        # 3. 构造路径：将文件统一存放在 data_db 目录下
        file_name = f"dev_{dev_id}_{data_type}.json"
        file_path = os.path.join(DB_DIR, file_name)
        
        # 4. 执行持久化写入
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        print(f" 💾 [STORAGE] 写入成功 | 路径: {file_path}")

    except Exception as e:
        print(f" ❌ [ERROR] 写入异常: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

# MQ 初始化
try:
    conn = get_connection()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')

    q = ch.queue_declare(queue='writer_v2', durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)

    ch.basic_consume(queue='writer_v2', on_message_callback=callback)
    print(f' [*] 写入模块已就绪，等待 Jenkins 触发流量...')
    ch.start_consuming()
except Exception as conn_err:
    print(f" 🚨 [CRITICAL] 无法连接到 RabbitMQ 服务器: {conn_err}")
