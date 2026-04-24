import argparse
import time
import threading
import random
import csv
import os
import json
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter

# 【引入核心安全包】
from security_utils import encrypt_data, generate_token
from song_info_provider import fetch_song_info

# ==========================================
# 1. 初始化设置与文件准备 
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
CSV_FILE = os.path.join(LOG_DIR, "data.csv")
CACHE_FILE = os.path.join(LOG_DIR, "failed_messages.json")
file_lock = threading.Lock()
cache_lock = threading.Lock()
print_lock = threading.Lock()
http_local = threading.local()

# ==========================================
# 2. 云端 API 路由配置
# ==========================================
BASE_URL = os.environ.get("BASE_URL", "https://8.137.165.220").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "15"))

# 路由映射表
ENDPOINT_MAP = {
    "bass_gain": "/api/bass",
    "signal_strength": "/api/signal",
    "volume": "/api/volume",
    "is_connected": "/api/status/connection",
    "is_connecting": "/api/status/connection",
    "like_status": "/api/status/like",
    "song_info": "/api/song-info",
    "歌曲信息": "/api/song-info",
}

SONG_KEYWORDS = [
    "稻香",
    "晴天",
    "夜曲",
    "青花瓷",
    "七里香",
]

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


def log_message(message):
    with print_lock:
        print(message, flush=True)


def get_http_session():
    session = getattr(http_local, "session", None)
    if session is None:
        session = requests.Session()
        session.trust_env = False
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=0)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        http_local.session = session
    return session


def is_retryable_payload(payload):
    metric_type = payload.get("type")
    return ENDPOINT_MAP.get(metric_type) is not None


def build_user_profile(device_id):
    normalized = str(device_id).replace("dev_", "user_")
    return {
        "user_account": f"{normalized}@smart-speaker.local",
        "user_password": f"{normalized}_pwd_2026",
    }


def get_song_keyword():
    return random.choice(SONG_KEYWORDS)


def send_song_info(device_id, keyword=None):
    process_data(device_id, "歌曲信息", keyword or get_song_keyword())

# ==========================================
# 3. 核心：带加密与鉴权的 HTTP 发送机制 (已对齐队友 C)
# ==========================================
def get_target_url(metric_type):
    """根据数据类型获取对应的完整接口 URL"""
    path = ENDPOINT_MAP.get(metric_type, "/api/unknown_malicious")
    return BASE_URL + path

def send_via_http(payload):
    """核心发送函数：负责鉴权、加密并发送 HTTP POST 请求"""
    metric_type = payload.get("type")
    device_id = payload.get("device_id")
    target_url = get_target_url(metric_type)
    
    # 1. 严格按照队友 C 的算法获取 Token 和整型时间戳 (不再需要传入 device_id)
    token, timestamp = generate_token()
    
    # 2. 将真实 Payload 进行 AES 加密
    encrypted_str = encrypt_data(payload)
    if not encrypted_str:
        log_message(f"  [加密失败] {device_id} 的数据加密异常，取消发送。")
        return False
        
    # 3. 【核心修改】严格对齐规范期望的 JSON 格式，补充文档要求的 sign
    secure_payload = {
        "timestamp": timestamp,
        "token": token,
        "data": encrypted_str,  # 这里装 AES 加密后的密文
        "sign": token           # 暂时以 token 作为 sign 发送，确保结构完整
    }

    # 4. 根据 music.pdf 要求增加 Authorization Header
    headers = {
        "Authorization": token
    }

    response = None
    try:
        # 发送请求（增加 headers）
        session = get_http_session()
        response = session.post(
            target_url,
            headers=headers,
            json=secure_payload,
            timeout=HTTP_TIMEOUT,
            verify=False
        )
        
        if response.status_code in [200, 201]:
            return True
            
        # 拦截机制：被网关 403 拒绝，直接丢弃，不重传
        elif response.status_code in [401, 403]:
            log_message(f"  [网关拦截 {response.status_code}] 鉴权失败或秘钥错误，当前数据已丢弃。")
            return True 
        elif response.status_code == 404:
            log_message(f"  [接口不存在 404] {target_url}，当前数据不再重试。")
            return True
            
        else:
            log_message(f"  [云端拒绝] 接口: {target_url}, 状态码: {response.status_code}, 响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        log_message(f"  [请求超时] 无法在规定时间内连接到 {target_url}")
        return False
    except requests.exceptions.RequestException as e:
        log_message(f"  [网络异常] {target_url}: {e}")
        return False

    finally:
        if response is not None:
            response.close()

def save_to_local_cache(payload):
    """将发送失败的【明文原始字典】存入本地，重传时会重新获取新时间戳并加密"""
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
    """后台重传线程"""
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

            retryable_cache = [item for item in cache_data if isinstance(item, dict) and is_retryable_payload(item)]
            dropped_count = len(cache_data) - len(retryable_cache)
            if dropped_count:
                log_message(f"[缓存清理] 已丢弃 {dropped_count} 条无效或不可重试的历史消息。")
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(retryable_cache, f, indent=4)

            cache_data = retryable_cache
            if not cache_data:
                continue
                
            log_message(f"\n[后台重传] 检测到 {len(cache_data)} 条积压数据，尝试向云端重传...")
            remaining_cache = []
            reconnect_success = False
            
            for index, payload in enumerate(cache_data):
                if send_via_http(payload):
                    reconnect_success = True
                    log_message(f"  [重发成功] {payload['device_id']} -> {get_target_url(payload['type'])}")
                else:
                    log_message("  [重发失败] 接口依然拒绝连接，停止本次重发。")
                    remaining_cache.extend(cache_data[index:])
                    break
            
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(remaining_cache, f, indent=4)
                
            if reconnect_success and not remaining_cache:
                log_message("[重传完毕] 所有积压数据已成功同步至云端！\n")

def process_data(device_id, metric_type, value):
    """数据处理与分发中心"""
    log_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([log_timestamp, device_id, metric_type, value])

    # 原始明文数据载体
    payload = {
      "device_id": device_id,     
      "type": metric_type,        
      "value": value
    }
    if metric_type in ("song_info", "姝屾洸淇℃伅"):
        try:
            payload["song_payload"] = fetch_song_info(value)
        except Exception as exc:
            log_message(f"[歌曲信息获取失败] {device_id} | {value}: {exc}")
            return
    payload.update(build_user_profile(device_id))
    
    target_endpoint = ENDPOINT_MAP.get(metric_type, "/api/unknown_malicious")
    
    if device_id == "dev_false":
        log_message(f"[毒数据注入] {device_id} | {metric_type}: {value} -> {target_endpoint}")
    else:
        log_message(f"[尝试发送] {device_id} | {metric_type}: {value} -> {target_endpoint}")

    # 触发安全发送机制
    if send_via_http(payload):
        if device_id != "dev_false":
            log_message(f"[发送成功] {device_id} 的数据已安全送达 {target_endpoint}")
    else:
        if target_endpoint == "/api/unknown_malicious":
            log_message(f"[非法类型已丢弃] {device_id} | {metric_type} 不进入重试缓存。")
        else:
            log_message(f"[网络/请求异常] {device_id} 无法送达，已存入本地缓存...")
            save_to_local_cache(payload)

# ==========================================
# 4. 核心数学与统计工具
# ==========================================
def generate_normal_data(mu, sigma, min_val, max_val):
    val = random.gauss(mu, sigma)
    clamped_val = max(min(val, max_val), min_val)
    return round(clamped_val, 2)

# ==========================================
# 5. 数据模拟线程 
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

def simulate_malicious_status(device_id):
    time.sleep(2)
    while True:
        process_data(device_id, "volume", "非常大声")
        process_data(device_id, "signal_strength", 999.99)
        process_data(device_id, "is_connected", None)
        process_data(device_id, "self_destruct_mode", True)
        time.sleep(4) 

# ==========================================
# 6. 主程序入口
# ==========================================
if __name__ == "__main__":
    # 忽略 requests 库在不验证证书时报的烦人 Warning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    log_message("=================================================")
    log_message("=== 智能音箱压测客户端 (安全架构联调版) ======")
    log_message("=================================================\n")
    
    num_devices = 0
    while True:
        try:
            user_input = input("请输入要模拟的【正常设备】数量 (纯数字，例如 2): ")
            num_devices = int(user_input.strip())
            if num_devices <= 0 or num_devices > 50:
                log_message("数量必须在 1 到 50 之间，请重新输入！\n")
                continue
            break 
        except ValueError:
            log_message("输入格式错误！请只输入纯数字。\n")
            
    device_list = [f"dev_{i:02d}" for i in range(1, num_devices + 1)]
    
    include_false = input("是否召唤 'dev_false' 注入脏数据测试网关防线？(y/n): ")
    if include_false.lower() == 'y':
        device_list.append("dev_false")
    
    log_message(f"\n[-] 正在准备同时启动 {len(device_list)} 台设备...")
    log_message(f"[-] 基础服务器 API: {BASE_URL}")
    log_message("[-] 3秒后开始向云端推送加密数据... (按 Ctrl+C 随时停止)\n")
    time.sleep(3) 
    
    init_env()
    
    thread_retry = threading.Thread(target=background_retry_worker)
    thread_retry.daemon = True 
    thread_retry.start()
    
    for dev_id in device_list:
        if dev_id == "dev_false":
            thread_bad = threading.Thread(target=simulate_malicious_status, args=(dev_id,))
            thread_bad.daemon = True
            thread_bad.start()
        else:
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
        log_message("\n=== 用户已停止模拟器 ===")
