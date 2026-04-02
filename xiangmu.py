import argparse
import time
import threading
import random
import csv
import os
import json
import pika
from datetime import datetime

# ==========================================
# 1. 初始化设置与文件准备 
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
CSV_FILE = os.path.join(LOG_DIR, "data.csv")
CACHE_FILE = os.path.join(LOG_DIR, "failed_messages.json")
file_lock = threading.Lock()
cache_lock = threading.Lock()

# 全局变量：对齐云端配置
MQ_HOST = "8.137.165.220"
MQ_PORT = 5672
MQ_USER = "migrate"
MQ_PASS = "2728"
MQ_EXCHANGE = "smart_speaker_exchange" 
BUSINESS_TOKEN = "smart_speaker_2026"  

def init_env():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["时间戳", "设备ID", "数据类型", "数值"])
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, mode='w', encoding='utf-8') as f:
            json.dump([], f)

# ==========================================
# 2. 核心：MQ 发送与重传机制
# ==========================================
def push_to_mq(payload):
    try:
        credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
        parameters = pika.ConnectionParameters(
            host=MQ_HOST, port=MQ_PORT, virtual_host='/', 
            credentials=credentials, connection_attempts=1, socket_timeout=3       
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        channel.basic_publish(
            exchange=MQ_EXCHANGE, 
            routing_key='', 
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        return True
    except Exception as e:
        print(f"  [底层调试] MQ断开原因: {e}")
        return False

def save_to_local_cache(payload):
    with cache_lock:
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cache_data = []
        cache_data.append(payload)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4)
            
def background_retry_worker():
    while True:
        time.sleep(5)
        with cache_lock:
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if not cache_data:
                continue
                
            print(f"\n🔄 [后台重传] 检测到 {len(cache_data)} 条积压数据，尝试向云端重传...")
            remaining_cache = []
            reconnect_success = False
            
            for index, payload in enumerate(cache_data):
                if push_to_mq(payload):
                    reconnect_success = True
                    print(f"  └─ ✅ 重发成功: {payload['device_id']} | {payload['type']} -> {payload['value']}")
                else:
                    print("  └─ ❌ 云端依然拒绝连接，停止本次重发。")
                    remaining_cache.extend(cache_data[index:])
                    break
            
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(remaining_cache, f, indent=4)
                
            if reconnect_success and not remaining_cache:
                print("🎉 [重传完毕] 所有积压数据已成功同步至云端！\n")

def process_data(device_id, metric_type, value):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, device_id, metric_type, value])

    payload = {
      "token": BUSINESS_TOKEN,    
      "device_id": device_id,     
      "type": metric_type,        
      "value": value,             
      "timestamp": timestamp
    }
    
    print(f"📡 [尝试发送] {device_id} | {metric_type}: {value} (类型: {type(value).__name__})", flush=True)

    if push_to_mq(payload):
        print(f"✅ [入队成功] {device_id} 的数据已推送到 Exchange")
    else:
        print(f"⚠️ [网络/权限异常] {device_id} 无法送达云端，已存入本地缓存...")
        save_to_local_cache(payload)

# ==========================================
# 3. 核心数学与统计工具
# ==========================================
def generate_normal_data(mu, sigma, min_val, max_val):
    val = random.gauss(mu, sigma)
    clamped_val = max(min(val, max_val), min_val)
    return round(clamped_val, 2)

# ==========================================
# 4. 数据模拟线程 
# ==========================================
def simulate_hardware_status(device_id):
    time.sleep(random.uniform(0.1, 1.5)) 
    while True:
        sig_str = generate_normal_data(-60.0, 15.0, -120.0, 0.0)
        process_data(device_id, "signal_strength", sig_str)
        
        current_hour = datetime.now().hour
        vol = int(generate_normal_data(50, 10, 0, 100)) if 7 <= current_hour < 22 else int(generate_normal_data(20, 5, 0, 100)) 
        process_data(device_id, "volume", vol)

        is_conn = random.random() < 0.95 
        process_data(device_id, "is_connected", is_conn)
        
        is_connecting_state = random.random() < 0.15 
        process_data(device_id, "is_connecting", is_connecting_state)
        
        time.sleep(3)

def simulate_playback_status(device_id):
    time.sleep(random.uniform(0.1, 1.5))
    while True:
        bass = int(generate_normal_data(6, 2, 0, 12))
        process_data(device_id, "bass_gain", bass)
            
        is_liked = random.random() < 0.3 
        process_data(device_id, "like_status", is_liked)
        
        time.sleep(5)

# ==========================================
# 5. 主程序入口 (动态交互并发版)
# ==========================================
if __name__ == "__main__":
    print(f"=================================================")
    print(f"=== 🚀 智能音箱压测客户端已启动 (动态交互版) ===")
    print(f"=================================================\n")
    
    # 【核心修改】：通过交互式终端询问用户需要模拟多少台设备
    num_devices = 0
    while True:
        try:
            user_input = input("👉 请在键盘输入要模拟的设备数量 (纯数字，例如 5): ")
            num_devices = int(user_input.strip())
            if num_devices <= 0:
                print("⚠️ 数量必须大于 0，请重新输入！\n")
                continue
            if num_devices > 50:
                print("⚠️ 为了保护你电脑的 CPU 和云端服务器，单次最多允许模拟 50 台，请重新输入！\n")
                continue
            break # 输入合法，跳出循环
        except ValueError:
            print("⚠️ 输入格式错误！请只输入纯数字。\n")
            
    # 根据用户输入的数字，自动生成设备列表，例如：dev_01, dev_02...
    # :02d 的意思是如果是单个数字，前面自动补 0 (比如 1 变成 01)
    device_list = [f"dev_{i:02d}" for i in range(1, num_devices + 1)]
    
    print(f"\n[-] 正在准备同时启动 {len(device_list)} 台设备...")
    print(f"[-] 设备列表: {', '.join(device_list)}")
    print("[-] 3秒后开始向云端推送数据... (按 Ctrl+C 随时停止)\n")
    time.sleep(3) # 给用户3秒钟确认时间
    
    init_env()
    
    # 启动后台重传线程 (无论多少台设备，1 个清洁工就够了)
    thread_retry = threading.Thread(target=background_retry_worker)
    thread_retry.daemon = True 
    thread_retry.start()
    
    # 遍历设备列表，为每一台设备分配独立的工作线程
    for dev_id in device_list:
        thread_hw = threading.Thread(target=simulate_hardware_status, args=(dev_id,))
        thread_pb = threading.Thread(target=simulate_playback_status, args=(dev_id,))
        
        thread_hw.daemon = True
        thread_pb.daemon = True
        
        thread_hw.start()
        thread_pb.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n=== 用户已停止模拟器 ===")