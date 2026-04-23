import json

from mq_config import EXCHANGE_NAME, declare_exchange, get_connection
from storage_backends import persist_payload


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("[WRITER] Dropped a non-JSON message.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        backend_name = persist_payload(data)
        print(
            f"[STORAGE] Persisted {data.get('device_id', 'unknown_device')} "
            f"{data.get('type', 'unknown_type')} via {backend_name}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        print(f"[ERROR] Database persistence failed: {exc}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_writer():
    conn = get_connection()
    ch = conn.channel()
    declare_exchange(ch)
    q = ch.queue_declare(queue="writer_v2", durable=True)
    ch.queue_bind(exchange=EXCHANGE_NAME, queue=q.method.queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue="writer_v2", on_message_callback=callback)
    print(" [*] Writer is ready and will persist data to MongoDB/MySQL.")
    ch.start_consuming()


if __name__ == "__main__":
    try:
        start_writer()
    except Exception as conn_err:
        print(f"[CRITICAL] Writer failed to start: {conn_err}")
