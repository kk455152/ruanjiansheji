# app.py
import atexit
import hashlib
import json
import os
import tempfile

from flask import Flask, request, jsonify

from mq_config import get_connection, EXCHANGE_NAME
from security_utils import decrypt_data, TOKEN_SALT  # 直接引用组员 B 上传的工具包

app = Flask(__name__)
_TEMP_PEM_FILES = []


def _cleanup_temp_pems():
    for path in _TEMP_PEM_FILES:
        try:
            os.remove(path)
        except OSError:
            pass


atexit.register(_cleanup_temp_pems)


def normalize_pem_file(path, begin_marker, end_marker):
    """
    兼容仓库中只保存 Base64 内容、缺少 PEM 头尾的证书文件。
    """
    with open(path, 'r', encoding='ascii') as f:
        content = f.read().strip()

    if content.startswith("-----BEGIN"):
        return path

    fd, temp_path = tempfile.mkstemp(suffix='.pem')
    with os.fdopen(fd, 'w', encoding='ascii', newline='\n') as f:
        f.write(f"{begin_marker}\n{content}\n{end_marker}\n")

    _TEMP_PEM_FILES.append(temp_path)
    return temp_path

# ==========================================
# 核心逻辑：安全解密与 Token 动态校验
# ==========================================
def validate_and_decrypt(request_json, auth_token, timestamp):
    """
    第一关：动态 Token 校验 (MD5: salt + timestamp)
    第二关：AES-128-ECB 内容解密
    """
    # 1. 验证请求头中是否有必要的时间戳
    if not timestamp:
        return None, "Missing Timestamp"
    
    # 2. 动态计算 Token：严格对齐组员 B 的算法 MD5(salt + timestamp)
    raw_str = f"{TOKEN_SALT}{timestamp}"
    expected_token = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
    
    # 3. 拦截非法 Token
    if auth_token != expected_token:
        return None, "Unauthorized: Invalid Token"

    # 4. 获取加密的 Payload 数据 (修正为对齐 music.pdf 的 'data' 字段)
    encrypted_payload = request_json.get('data')
    if not encrypted_payload:
        return None, "Missing Payload"
    
    # 5. 调用 B 提供的工具进行 AES 解密
    decrypted_dict = decrypt_data(encrypted_payload)
    if not decrypted_dict:
        return None, "Decryption Failed: Illegal data or Key mismatch"
    
    return decrypted_dict, None

# ==========================================
# 路由区域：统一处理模拟器的 5 个 API 接口
# ==========================================
@app.route('/api/bass', methods=['POST'])
@app.route('/api/signal', methods=['POST'])
@app.route('/api/volume', methods=['POST'])
@app.route('/api/status/connection', methods=['POST'])
@app.route('/api/status/like', methods=['POST'])
def handle_simulator_data():
    """
    接收来自模拟器的加密 POST 请求，解密后打入 RabbitMQ
    """
    # 从 HTTP Header 获取鉴权字段
    auth_token = request.headers.get('Authorization')
    # timestamp 在 xiangmu.py 中是放在 body 里的，对齐提取方式
    timestamp = request.json.get('timestamp')
    
    # 1. 安全层：解密并验证合法性
    data_decrypted, error_msg = validate_and_decrypt(request.json, auth_token, timestamp)
    
    if error_msg:
        return jsonify({"status": "error", "message": error_msg}), 401

    # 2. 路由元数据：记录数据来源接口，方便 Worker 后期分类存入 data_db
    data_decrypted['api_path'] = request.path

    # 3. 通信层：将解密后的干净数据发送至消息队列
    try:
        # 获取由 mq_config 动态识别环境后的连接
        connection = get_connection()
        channel = connection.channel()
        
        # 将数据以 JSON 字符串形式发布到交换机
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key='', 
            body=json.dumps(data_decrypted)
        )
        connection.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Verified data from {request.path} sent to RabbitMQ"
        }), 200
        
    except Exception as e:
        # 异常处理：如 MQ 服务未启动或连接超时
        return jsonify({"status": "error", "message": f"Broker Error: {str(e)}"}), 500

# ==========================================
# 启动配置：强制开启 HTTPS
# ==========================================
if __name__ == '__main__':
    cert_path = normalize_pem_file('cert.pem', '-----BEGIN CERTIFICATE-----', '-----END CERTIFICATE-----')
    key_path = normalize_pem_file('key.pem', '-----BEGIN PRIVATE KEY-----', '-----END PRIVATE KEY-----')

    # 生产环境使用 443 端口
    # ssl_context 指向你复制内容并保存的证书文件
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('APP_PORT', '443')),
        ssl_context=(cert_path, key_path)
    )
