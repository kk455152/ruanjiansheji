from datetime import datetime
from functools import wraps

from flask import request, g, jsonify

from db import get_mysql_conn


def response(code, msg, data=None, error_details=None):
    body = {
        "code": code,
        "msg": msg
    }
    if error_details is not None:
        body["error_details"] = error_details
    else:
        body["data"] = data
    return jsonify(body), code


def get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.replace("Bearer ", "", 1).strip()


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()

        if not token:
            return response(
                401,
                "未登录",
                error_details="缺少 Authorization: Bearer <token>"
            )

        conn = get_mysql_conn()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        t.user_id,
                        t.access_token,
                        t.expires_at,
                        u.username,
                        u.phone
                    FROM auth_token t
                    JOIN `user` u ON u.user_id = t.user_id
                    WHERE t.access_token = %s
                    ORDER BY t.expires_at DESC
                    LIMIT 1
                    """,
                    (token,)
                )

                row = cursor.fetchone()

            if not row:
                return jsonify({
                    "code": 403,
                    "msg": "登录已过期或无权访问",
                    "data": {
                        "reason": "Invalid token",
                        "expired_at": None
                    }
                }), 403

            if row["expires_at"] < datetime.now():
                return jsonify({
                    "code": 403,
                    "msg": "登录已过期或无权访问",
                    "data": {
                        "reason": "Token expired",
                        "expired_at": row["expires_at"].strftime("%Y-%m-%d %H:%M:%S")
                    }
                }), 403

            g.current_user = row
            g.user_id = row["user_id"]

            return func(*args, **kwargs)

        finally:
            conn.close()

    return wrapper
