import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from db import get_mysql_conn
from config import TOKEN_EXPIRE_HOURS

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def validate_phone(phone):
    return bool(re.fullmatch(r"1[3-9]\d{9}", phone or ""))


def create_token(cursor, user_id, platform_type="wechat_mini"):
    """
    A 已确认：
    1. platform_type 前端不传，后端默认 wechat_mini
    2. refresh_token 后端自动生成
    3. auth_token 表最终字段包含：
       user_id, platform_type, access_token, refresh_token, expires_at
    """
    access_token = secrets.token_hex(16)
    refresh_token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)

    cursor.execute(
        """
        INSERT INTO auth_token
        (user_id, platform_type, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, platform_type, access_token, refresh_token, expires_at)
    )

    return access_token, refresh_token, expires_at


@auth_bp.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}

    username = body.get("username", "").strip()
    password_hash = body.get("password_hash", "").strip()
    phone = body.get("phone", "").strip()

    if not username or not password_hash or not phone:
        return jsonify({
            "code": 400,
            "msg": "注册信息格式不正确",
            "error_details": "username、password_hash、phone 均不能为空"
        }), 400

    if len(username) > 50:
        return jsonify({
            "code": 400,
            "msg": "注册信息格式不正确",
            "error_details": "username 长度不能超过 50"
        }), 400

    if not validate_phone(phone):
        return jsonify({
            "code": 400,
            "msg": "注册信息格式不正确",
            "error_details": "手机号格式错误"
        }), 400

    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM `user` WHERE username = %s LIMIT 1",
                (username,)
            )

            if cursor.fetchone():
                return jsonify({
                    "code": 400,
                    "msg": "注册信息格式不正确",
                    "error_details": "用户名已存在"
                }), 400

            cursor.execute(
                """
                INSERT INTO `user` (username, password_hash, phone)
                VALUES (%s, %s, %s)
                """,
                (username, password_hash, phone)
            )

            user_id = cursor.lastrowid

            access_token, refresh_token, expires_at = create_token(
                cursor,
                user_id,
                "wechat_mini"
            )

            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "注册成功",
            "data": {
                "user_id": user_id,
                "username": username,
                "phone": phone,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "code": 400,
            "msg": "注册信息格式不正确",
            "error_details": str(e)
        }), 400

    finally:
        conn.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}

    username = body.get("username", "").strip()
    password_hash = body.get("password_hash", "").strip()

    if not username or not password_hash:
        return jsonify({
            "code": 400,
            "msg": "请求参数有误，请检查字段格式",
            "error_details": "username 和 password_hash 不能为空"
        }), 400

    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, phone, created_at
                FROM `user`
                WHERE username = %s AND password_hash = %s
                LIMIT 1
                """,
                (username, password_hash)
            )

            user = cursor.fetchone()

            if not user:
                return jsonify({
                    "code": 401,
                    "msg": "认证失败",
                    "error_details": "用户名或密码错误"
                }), 401

            access_token, refresh_token, expires_at = create_token(
                cursor,
                user["user_id"],
                "wechat_mini"
            )

            conn.commit()

        created_at = user.get("created_at")
        if created_at:
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({
            "code": 200,
            "msg": "登录成功",
            "data": {
                "user_id": user["user_id"],
                "username": user["username"],
                "phone": user["phone"],
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_at": created_at
            }
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "code": 400,
            "msg": "请求参数有误，请检查字段格式",
            "error_details": str(e)
        }), 400

    finally:
        conn.close()
