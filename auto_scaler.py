import os
import time
import requests

# 1. 配置参数
# 注意：在 Docker 内部，可以用服务名 'rabbitmq' 访问
RABBITMQ_API = "http://rabbitmq:15672/api/queues/%2f/speaker_data"
AUTH = ('guest', 'guest')

# 2. 阈值设定 (演示时可以调小一点)
UP_THRESHOLD = 15   # 消息堆积超过 15，扩容到 3 个工人
DOWN_THRESHOLD = 5  # 消息少于 5，缩减回 1 个工人

def scale(count):
    print(f"检测到访问量变化，自动调整 Worker 数量至: {count}")
    # 调用 Docker Compose 指令实现物理层面的启停
    os.system(f"docker-compose up -d --scale worker-writer={count}")

while True:
    try:
        r = requests.get(RABBITMQ_API, auth=AUTH)
        if r.status_code == 200:
            msg_count = r.json().get('messages', 0)
            print(f"当前队列压力: {msg_count}")
            
            if msg_count > UP_THRESHOLD:
                scale(3)
            elif msg_count < DOWN_THRESHOLD:
                scale(1)
    except Exception as e:
        print(f"监控异常: {e}")
    
    time.sleep(5) # 每 5 秒自动检查一次