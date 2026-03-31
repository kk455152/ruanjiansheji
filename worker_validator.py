# worker_validator.py
import pika, json
from mq_config import get_connection, EXCHANGE_NAME

def clean_and_validate(data):
    """详细的数据清洗逻辑"""
    d_type = data.get("type")
    val = data.get("value")
    dev_id = data.get("device_id")

    if not dev_id:
        return False, "缺失设备ID"

    # 针对不同数据的清洗规则
    if d_type == "volume":
        if not (0 <= val <= 100):
            return False, f"音量超出范围(0-100): {val}"
    
    elif d_type == "signal_strength":
        # 信号强度通常为负数 dBm
        if val > 0 or val < -120:
            return False, f"信号强度异常(应为负值): {val}"
    
    elif d_type == "bass_gain":
        if not (0 <= val <= 12):
            return False, f"低音增益超出范围(0-12): {val}"
            
    elif d_type == "is_connected" or d_type == "like_status":
        if not isinstance(val, bool):
            return False, f"布尔值类型错误: {val}"

    return True, "数据合法"

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        success, info = clean_and_validate(data)
        if success:
            print(f" ✅ [验证模块] 数据合格 | 设备: {data.get('device_id')} | 类型: {data.get('type')}")
        else:
            print(f" ❌ [清洗拦截] 发现脏数据! 原因: {info}")
    except Exception as e:
        print(f" ⚠️ [解析失败] 格式非JSON: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

conn = get_connection()
ch = conn.channel()
ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
# 每个模块拥有自己的独立队列，实现并行
q = ch.queue_declare(queue='validator_v2', durable=True)
ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)

ch.basic_consume(queue='validator_v2', on_message_callback=callback)
print(' [*] 验证模块（清洗中心）已启动...')
ch.start_consuming()