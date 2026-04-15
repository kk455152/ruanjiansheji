# worker_logger.py
import pika, json, datetime, os
from mq_config import get_connection, declare_exchange

# 运维微调：确保日志存放在统一的数据目录下
DB_DIR = "data_db"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def callback(ch, method, properties, body):
    try:
        # 1. 解析原始数据
        raw_data = json.loads(body)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 2. 提取信息 (鉴权已在网关 app.py 完成，直接记录合法流量)
        device_id = raw_data.get("device_id", "Unknown")
        data_type = raw_data.get("type", "Unknown")

        log_entry = f"[{timestamp}] [INFO] Device: {device_id} | Action: Upload {data_type}\n"

        # 3. 写入统一的日志文件
        log_path = os.path.join(DB_DIR, "system_access.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        # 4. 控制台输出（由 Jenkins 捕获，方便 A 实时监控）
        print(f"[LOG] 记录成功: {device_id} - {data_type}")
        
    except json.JSONDecodeError:
        print(f"[LOG_ERROR] 收到非JSON格式数据")
    except Exception as e:
        print(f"[LOG_ERROR] 发生异常: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

# MQ 初始化
try:
    conn = get_connection()
    ch = conn.channel()
    declare_exchange(ch)

    # 声明日志模块专用队列
    q = ch.queue_declare(queue='logger_v2', durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue='logger_v2', on_message_callback=callback)
    print(f' [*] 全量日志模块已就绪，存储路径: {DB_DIR}/system_access.log')
    ch.start_consuming()
except Exception as e:
    print(f"[CRITICAL] 日志模块启动失败: {e}")
