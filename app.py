# app.py
from flask import Flask, request, jsonify
from mq_config import get_connection, EXCHANGE_NAME
import json

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def receive_data():
    # 1. 接收 HTTP POST 数据
    data = request.json
    
    # 2. 身份验证
    if not data or data.get("token") != "smart_speaker_2026":
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 3. 将数据转发给 RabbitMQ
    try:
        connection = get_connection()
        channel = connection.channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key='',
            body=json.dumps(data)
        )
        connection.close()
        # 4. 响应时间在 1s 以内
        return jsonify({"status": "success", "message": "Data Sent to MQ"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # 如果没用 Nginx，可以这里挂载 SSL 实现 HTTPS
    # app.run(host='0.0.0.0', port=5000, ssl_context='adhoc') 
    app.run(host='0.0.0.0', port=5000)
