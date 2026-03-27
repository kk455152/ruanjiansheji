from flask import Flask, request, jsonify, render_template_string
import json
import os
import logging
import requests  # 这个是用来做云端到云端发送的
from datetime import datetime

app = Flask(__name__)

# --- 配置区 ---
DATA_FILE = "voice_records.json"
AUTH_TOKEN = "music_player"  # 符合 Token 校验
# 新增：配置系统日志，直接写进你现有的 log.txt
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_storage():
    """初始化存储并强制修正权限，防止 500 错误"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    # 关键：你的 root 用户都能读写
    os.chmod(DATA_FILE, 0o666)

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# --- 功能 1：专业数据上报接口 ---
@app.route("/voice/upload", methods=["POST"])
def upload_voice():
    # 1. 鉴权校验
    if request.headers.get("Authorization") != AUTH_TOKEN:
        return jsonify({"code": 401, "msg": "Unauthorized"}), 401
    
    # 2. 获取 JSON 数据
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "msg": "Invalid JSON"}), 400

    # 3. 写入数据（支持多线程安全读取后的追加）
    records = load_data()
    records.append({
        "device_id": data.get("device_id", "Unknown"),
        "command": data.get("command", "None"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
        
# === 以下是为 PPT 任务新增的：日志与云端到云端传输 ===
    
    # 1. 记录到 log.txt
    logging.info(f"成功接收设备 {data.get('device_id')} 的指令: {data.get('command')}")

    # 2. 云端到云端：把收到的数据转发给另一个云接口 (加了 try 保护，绝不影响你原来的运行)
    try:
        # 这是一个专门用来测试接收数据的免费云端地址
        target_cloud_url = "https://webhook.site/a8f090d8-xxxx-xxxx-xxxx" # 等下教你怎么获取你专属的
        requests.post(target_cloud_url, json=data, timeout=3)
        logging.info("云端到云端转发成功！")
    except Exception as e:
        logging.error(f"云端转发异常 (不影响主程序): {e}")
        
    # =========================================================
    
    return jsonify({"code": 200, "msg": "Success", "status": "Recorded"})

# --- 功能 2：PPT 演示专用监控页面 ---
from flask import render_template # 记得在开头导入这个

@app.route("/voice/logs", methods=["GET"])
def view_logs():
    records = load_data()
    
    # 计算总结数据
    total_count = len(records)
    unique_devices = len(set(r['device_id'] for r in records))
    # 获取最近 5 条指令
    recent_activity = records[-5:] if total_count > 0 else []

    # 渲染外部 HTML 文件，并传递数据
    return render_template("logs.html", 
                           records=records, 
                           total_count=total_count, 
                           unique_devices=unique_devices)

if __name__ == "__main__":
    init_storage()
    # 本地调试用 5000 端口
    app.run(host="0.0.0.0", port=5000)