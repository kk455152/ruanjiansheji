# worker_reader.py
import pika, json
from mq_config import get_connection, EXCHANGE_NAME, RAW_DATA_QUEUE

def start_reader():
    try:
        conn = get_connection()
        ch = conn.channel()
        
        # 1. 声明交换机：使用 fanout 广播模式
        ch.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')
        
        # 2. 声明原始队列：这是 B 端（模拟器）直接投递的目标
        ch.queue_declare(queue=RAW_DATA_QUEUE, durable=True)

        def callback(ch, method, properties, body):
            try:
                # 运维微调：在进入广播前先做基础的 JSON 校验
                # 这样可以防止 B 端发了乱码导致后续所有 Worker 崩溃
                json.loads(body) 
                
                print(f"[READER] 抓取成功，正在广播至全模块...")
                
                # 3. 广播给其他所有监听该 Exchange 的 Worker (Validator, Writer, Logger)
                ch.basic_publish(
                    exchange=EXCHANGE_NAME, 
                    routing_key='', 
                    body=body,
                    properties=pika.BasicProperties(delivery_mode=2) # 消息持久化
                )
                
                # 确认消费：从 RAW_DATA_QUEUE 中移除该原始包
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except json.JSONDecodeError:
                print(f"[READER] 丢弃非法格式包 (非JSON)")
                ch.basic_ack(delivery_tag=method.delivery_tag) # 非法包也要 ACK，否则会堆积
            except Exception as e:
                print(f"[READER] 内部处理错误: {e}")

        # 负载均衡限制：一次只处理一个包
        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=RAW_DATA_QUEUE, on_message_callback=callback)
        
        print(f'[*] 读取模块启动成功，监听队列: {RAW_DATA_QUEUE}')
        ch.start_consuming()

    except Exception as conn_err:
        print(f"[CRITICAL] 读取模块连接异常: {conn_err}")

if __name__ == "__main__":
    start_reader()
