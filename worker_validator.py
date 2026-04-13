# worker_validator.py
import pika, json
from mq_config import get_connection, EXCHANGE_NAME

def clean_and_validate(data):
    """根据最新取值范围表进行清洗 (注意：身份令牌鉴权已完全交由 API网关 app.py 负责)"""
    # 1. 设备ID校验
    dev_id = data.get("device_id")
    if not dev_id:
        return False, "缺失设备ID"

    # 3. 业务数据清洗规则 (根据最新图片范围)
    d_type = data.get("type")
    val = data.get("value")

    if d_type == "signal_strength":
        # 信号强度: -90 ~ -30 dBm
        if not (-90 <= val <= -30):
            return False, f"信号强度超出范围(-90~-30): {val}"
    
    elif d_type == "volume":
        # 音量 (涵盖白天和夜间): 0-100
        if not (0 <= val <= 100):
            return False, f"音量超出范围(0-100): {val}"
    
    elif d_type == "bass_gain":
        # 低音增益 (涵盖流行、摇滚、古典): -12 ~ +12 dB
        if not (-12 <= val <= 12):
            return False, f"低音增益超出范围(-12~12): {val}"
            
    elif d_type == "is_connected" or d_type == "like_status":
        # 状态: true/false
        if not isinstance(val, bool):
            return False, f"布尔值类型错误: {val}"

    return True, "数据合法"

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        success, info = clean_and_validate(data)
        
        if success:
            # 只有验证通过才打印绿色勾选
            print(f" ✅ [验证中心] 准入通过 | 设备: {data.get('device_id')} | 类型: {data.get('type')} | 值: {data.get('value')}")
        else:
            # 身份不符或数据错误，直接拦截并打印警告
            print(f" ❌ [安全拦截] {info}")
            
    except Exception as e:
        print(f" ⚠️ [系统异常] 解析失败或处理出错: {e}")
    finally:
        # 无论成功失败，都给 MQ 应答，防止消息堆积
        ch.basic_ack(delivery_tag=method.delivery_tag)

# MQ 初始化与连接
try:
    conn = get_connection()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
    
    # 声明验证专用队列
    q = ch.queue_declare(queue='validator_v2', durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue='validator_v2', on_message_callback=callback)
    print(f' [*] 验证模块（清洗中心）已启动，身份鉴权已移交至网关层')
    ch.start_consuming()
except Exception as e:
    print(f" 🚨 [CRITICAL] 验证模块启动失败: {e}")
