from datetime import datetime

from flask import Blueprint, request, jsonify, g

from db import get_mysql_conn
from auth_guard import require_auth

device_bp = Blueprint("device", __name__, url_prefix="/device")


def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


@device_bp.route("/list", methods=["GET"])
@require_auth
def device_list():
    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    d.device_id,
                    d.device_number,
                    b.custom_device_name,
                    d.model_name,
                    COALESCE(d.status, 0) AS status,
                    d.last_active
                FROM user_device_binding b
                JOIN device d ON d.device_id = b.device_id
                WHERE b.user_id = %s
                ORDER BY d.device_id ASC
                """,
                (g.user_id,)
            )

            devices = cursor.fetchall()

        for item in devices:
            item["last_active"] = format_datetime(item.get("last_active"))

        return jsonify({
            "code": 200,
            "msg": "获取设备列表成功",
            "data": devices
        }), 200

    except Exception as e:
        return jsonify({
            "code": 400,
            "msg": "获取设备列表失败",
            "error_details": str(e)
        }), 400

    finally:
        conn.close()


@device_bp.route("/bind", methods=["POST"])
@require_auth
def bind_device():
    body = request.get_json(silent=True) or {}

    device_number = body.get("device_number", "").strip()
    custom_device_name = body.get("custom_device_name", "").strip()

    if not device_number:
        return jsonify({
            "code": 400,
            "msg": "绑定失败",
            "error_details": "device_number 不能为空"
        }), 400

    if not custom_device_name:
        custom_device_name = "我的智能小音箱"

    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT device_id, device_number, model_name
                FROM device
                WHERE device_number = %s
                LIMIT 1
                """,
                (device_number,)
            )

            device = cursor.fetchone()

            if not device:
                return jsonify({
                    "code": 400,
                    "msg": "绑定失败",
                    "error_details": "未找到该序列号对应的硬件设备，请检查输入是否正确。"
                }), 400

            cursor.execute(
                """
                SELECT binding_id, user_id
                FROM user_device_binding
                WHERE device_id = %s
                LIMIT 1
                """,
                (device["device_id"],)
            )

            existing = cursor.fetchone()

            if existing:
                return jsonify({
                    "code": 403,
                    "msg": "禁止操作",
                    "error_details": "该设备已被其他账号绑定，请先在原账号解绑。"
                }), 403

            cursor.execute(
                """
                INSERT INTO user_device_binding
                (user_id, device_id, custom_device_name)
                VALUES (%s, %s, %s)
                """,
                (g.user_id, device["device_id"], custom_device_name)
            )

            binding_id = cursor.lastrowid

            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "设备绑定成功",
            "data": {
                "binding_id": binding_id,
                "user_id": g.user_id,
                "device_id": device["device_id"],
                "custom_device_name": custom_device_name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "code": 400,
            "msg": "绑定失败",
            "error_details": str(e)
        }), 400

    finally:
        conn.close()
