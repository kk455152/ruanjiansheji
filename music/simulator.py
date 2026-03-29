import argparse
import time
import threading
import random
import csv
import os
from datetime import datetime

# ==========================================
# 1. 初始化设置与文件准备 (适配 Docker 路径映射)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
CSV_FILE = os.path.join(LOG_DIR, "data.csv")
file_lock = threading.Lock()

def init_env():
    """初始化环境：创建目录并写入 CSV 表头"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["时间戳", "设备ID", "数据类型", "数值"])

def write_data_safe(device_id, metric_type, value):
    """线程安全的文件写入函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, device_id, metric_type, value])
    # 强制刷新缓冲区，适配 Docker 实时日志输出
    print(f"[{timestamp}] 设备: {device_id} | {metric_type}: {value}", flush=True)

# ==========================================
# 2. 核心数学与统计工具
# ==========================================
def generate_normal_data(mu, sigma, min_val, max_val):
    """
    生成符合正态分布的数据，并强制限制在极值范围内
    加入严格大于 0 的底层逻辑保护
    """
    val = random.gauss(mu, sigma)
    
    # 强制截断，并且通过 max(..., 0.01) 确保即使 min_val 传错了，最终结果也绝对 > 0
    clamped_val = max(min(val, max_val), min_val)
    if clamped_val <= 0:
        clamped_val = 0.01
        
    return round(clamped_val, 2)

# ==========================================
# 3. 核心数据模拟线程 (所有数据严格 > 0)
# ==========================================
def simulate_hardware_status(device_id):
    """线程 1：模拟硬件层数据"""
    while True:
        # 1. 信号强度：(原PPT是负数，现平移为正数表示信号质量分数，均值60，范围10-100)
        wifi_signal = generate_normal_data(60.0, 5.2, 10.0, 100.0)
        write_data_safe(device_id, "信号强度", wifi_signal)
        
        # 2. 智能音量：最小值从 0 改为 1，确保绝对 > 0
        current_hour = datetime.now().hour
        if 7 <= current_hour < 22:
            volume = generate_normal_data(50, 10, 1.0, 100.0)
            write_data_safe(device_id, "音量（白天）", volume)
        else:
            volume = generate_normal_data(20, 5, 1.0, 100.0)
            write_data_safe(device_id, "音量（夜间）", volume)
            
        time.sleep(3)

def simulate_playback_status(device_id):
    """线程 2：模拟用户播放行为"""
    genres = ["pop", "rock", "classical"]
    
    while True:
        current_genre = random.choice(genres)
        
        # 低音增益：(原PPT有负数，现将下限改为 0.1 强制大于 0，古典模式均值调整为 6.0 防止频出 0.1)
        if current_genre == "pop":
            bass_gain = generate_normal_data(4.5, 1.5, 0.1, 12.0)
            write_data_safe(device_id, "低音增益（流行）", bass_gain)
        elif current_genre == "rock":
            bass_gain = generate_normal_data(8.0, 1.5, 0.1, 12.0)
            write_data_safe(device_id, "低音增益（摇滚）", bass_gain)
        else:
            bass_gain = generate_normal_data(6.0, 1.0, 0.1, 12.0) # 古典均值由 0.0 改为 6.0
            write_data_safe(device_id, "低音增益（古典）", bass_gain)
            
        # 喜欢状态（保持不变，它是布尔值 true/false）
        is_liked = "true" if random.random() < 0.3 else "false"
        write_data_safe(device_id, "喜欢状态", is_liked)
        
        time.sleep(5)

# ==========================================
# 4. 主程序入口
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能音箱数据模拟器")
    parser.add_argument("--id", type=str, default="speaker_01", help="设置设备唯一标识符 (例如 speaker_01)")
    args = parser.parse_args()
    
    device_id = args.id
    print(f"=== 智能音箱模拟器已启动 | 当前设备 ID: {device_id} ===", flush=True)
    print(f"=== 数据保存路径: {CSV_FILE} ===", flush=True)
    print("正在基于正态分布算法实时生成数据 (已开启强制>0限制)，请按 Ctrl+C 停止...\n", flush=True)
    
    init_env()
    
    thread_hardware = threading.Thread(target=simulate_hardware_status, args=(device_id,))
    thread_playback = threading.Thread(target=simulate_playback_status, args=(device_id,))
    
    thread_hardware.daemon = True
    thread_playback.daemon = True
    
    thread_hardware.start()
    thread_playback.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n=== 用户已停止模拟器 ===")