# app.py
from flask import Flask, request, jsonify
from mq_config import get_connection, EXCHANGE_NAME
import json

app = Flask(__name__)

# ==========================================
# 路由区域：精准匹配模拟器的 5 个 API 接口
# ==========================================
@app.route('/api/bass', methods=['POST'])
@app.route('/api/signal', methods=['POST'])
@app.route('/api/volume', methods=['POST'])
@app.route('/api/status/connection', methods=['POST'])
@app.route('/api/status/like', methods=['POST'])
def handle_simulator_data():
    """
    统一处理来自模拟器的所有 POST 请求
    """
    # 1. 解析收到的 JSON 数据
    data = request.json
    
    # 2. 安全机制验证 (Token验证，满足“良”等考核要求)
    # 注意：这里的 token 值必须和你们模拟器里配置的一致
    if not data or data.get("token") != "smart_speaker_2026":
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 💡 核心小技巧：告诉 Worker 数据是从哪个接口来的
    # request.path 会自动获取当前请求的路径（比如 '/api/bass'）
    # 我们把它悄悄塞进数据里，这样你的 worker_writer 存文件时就能分门别类了
    data['api_path'] = request.path

    # 3. 将验证通过的数据打包发给 RabbitMQ
    try:
        connection = get_connection()
        channel = connection.channel()
        
        # 将字典转换为 JSON 字符串格式发送
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key='',  # 默认广播到绑定该交换机的所有队列
            body=json.dumps(data)
        )
        connection.close()
        
        # 4. 快速响应，要求响应时间 < 1s
        return jsonify({
            "status": "success", 
            "message": f"Data from {request.path} safely queued!"
        }), 200
        
    except Exception as e:
        # 如果 MQ 没开或者连不上，返回 500 错误
        return jsonify({"status": "error", "message": f"MQ Error: {str(e)}"}), 500


if __name__ == '__main__':
    # 默认启动在 5000 端口
    # 如果你要自己测试 HTTPS，可以解开下面那行的注释，并注释掉最后一行
    # app.run(host='0.0.0.0', port=5000, ssl_context='adhoc') 
    app.run(host='0.0.0.0', port=5000)
