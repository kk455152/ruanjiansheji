# worker_validator.py
import json

from mq_config import EXCHANGE_NAME, declare_exchange, get_connection


def clean_and_validate(data):
    device_id = data.get("device_id")
    if not device_id:
        return False, "missing device_id"

    data_type = data.get("type")
    value = data.get("value")

    if data_type == "signal_strength":
        if not isinstance(value, (int, float)) or not (-90 <= value <= -30):
            return False, f"signal_strength out of range: {value}"

    elif data_type == "volume":
        if not isinstance(value, (int, float)) or not (0 <= value <= 100):
            return False, f"volume out of range: {value}"

    elif data_type == "bass_gain":
        if not isinstance(value, (int, float)) or not (-12 <= value <= 12):
            return False, f"bass_gain out of range: {value}"

    elif data_type in ("is_connected", "like_status"):
        if not isinstance(value, bool):
            return False, f"boolean value expected: {value}"

    elif data_type in ("song_info", "歌曲信息"):
        if not isinstance(value, str) or not value.strip():
            return False, f"song keyword is invalid: {value}"
        if len(value.strip()) > 100:
            return False, f"song keyword too long: {value}"

    return True, "valid"


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        success, info = clean_and_validate(data)
        if success:
            print(
                f"[VALIDATOR] accepted | device: {data.get('device_id')} | "
                f"type: {data.get('type')} | value: {data.get('value')}"
            )
        else:
            print(f"[VALIDATOR] rejected | {info}")
    except Exception as exc:
        print(f"[VALIDATOR] processing failed: {exc}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


try:
    conn = get_connection()
    ch = conn.channel()
    declare_exchange(ch)
    q = ch.queue_declare(queue="validator_v2", durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue="validator_v2", on_message_callback=callback)
    print(" [*] Validator is ready.")
    ch.start_consuming()
except Exception as exc:
    print(f"[CRITICAL] Validator failed to start: {exc}")
