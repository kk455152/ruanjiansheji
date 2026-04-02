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
            print(f" ⚠️ [SECURITY] 拦截非法 Token | 设备: {data.get('device_id', 'Unknown')}")
            return
        
        # 2. 获取设备ID和接口类型 (API Type)
        dev_id = data.get("device_id", "unknown_device")
        api_type = data.get("type", "others")
        
        # 3. 【核心修改】构造嵌套路径：data_db/设备名/接口名.json
        # 先确保设备专属文件夹存在
        dev_path = os.path.join(DB_DIR, dev_id)
        if not os.path.exists(dev_path):
            os.makedirs(dev_path)
            
        # 再构造具体接口文件路径（例如: data_db/Speaker_01/volume.json）
        file_path = os.path.join(dev_path, f"{api_type}.json")

        # 4. 执行持久化写入
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        print(f" 💾 [STORAGE] 写入成功 | 路径: {file_path}")

    except Exception as e:
        print(f" ❌ [ERROR] 写入异常: {e}")
    finally:
        # 无论成功失败，都给 MQ 应答，保证任务不堆积
        ch.basic_ack(delivery_tag=method.delivery_tag)

# MQ 初始化
try:
    conn = get_connection()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')

    q = ch.queue_declare(queue='writer_v2', durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)

    # 🔴 负载均衡补丁：支持 Jenkins 开启多个 Writer 平分任务
    ch.basic_qos(prefetch_count=1)

    ch.basic_consume(queue='writer_v2', on_message_callback=callback)
    print(f' [*] 写入模块就绪 | 存储模式: [设备ID/接口名.json] | 等待流量...')
    ch.start_consuming()
except Exception as conn_err:
    print(f" 🚨 [CRITICAL] 无法连接到 RabbitMQ 服务器: {conn_err}")

