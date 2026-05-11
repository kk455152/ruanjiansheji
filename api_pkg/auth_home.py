import secrets
from datetime import datetime, timedelta

from . import api_bp
from .common import (
    body_json,
    current_user_id,
    get_device,
    get_song,
    history_rows,
    load_state,
    mysql_conn,
    mysql_one,
    ok,
    plain,
    save_state,
    now_str,
)


@api_bp.get("/_health")
def health():
    return ok("api routes loaded", {"time": now_str(), "mode": "database-first-with-mock-fallback"})


@api_bp.post("/auth/wechat-login")
def wechat_login():
    body = body_json()

    if not str(body.get("code", "")).strip():
        return ok("bad request", {"field": "code", "reason": "code is required"}, 400)

    if not body.get("encryptedData") or not body.get("iv"):
        return ok("bad request", {"field": "encryptedData/iv", "reason": "encryptedData and iv are required"}, 400)

    token = secrets.token_hex(16)
    user_id = 10001
    username = "wechat_" + str(body.get("code"))[:32]

    row = mysql_one("SELECT user_id FROM `user` WHERE username=%s LIMIT 1", (username,))
    if row:
        user_id = int(row["user_id"])
    else:
        conn = mysql_conn()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO `user` (username,password_hash,phone) VALUES (%s,%s,%s)",
                        (username, secrets.token_hex(16), None),
                    )
                    user_id = cursor.lastrowid
                    cursor.execute(
                        """
                        INSERT INTO auth_token
                        (user_id,platform_type,access_token,refresh_token,expires_at)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        (user_id, "wechat_mini", token, secrets.token_hex(32), datetime.now() + timedelta(days=7)),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                conn.close()

    state = load_state()
    state["tokens"][token] = user_id
    save_state(state)

    return plain(
        {
            "token": token,
            "userId": user_id,
            "nickname": body.get("nickname") or body.get("nickName") or "Miniapp User",
            "avatar": body.get("avatar") or body.get("avatarUrl") or "",
            "hasDevice": True,
        }
    )


@api_bp.get("/home/overview")
def home_overview():
    device = get_device()
    song = get_song()

    return plain(
        {
            "device": {
                "deviceId": device["deviceId"],
                "name": device["deviceName"],
                "model": device["modelName"],
                "online": device["online"],
                "battery": device["battery"],
            },
            "playing": {
                "songId": song["songId"],
                "songName": song["songName"],
                "artist": song["artist"],
                "source": song["source"],
                "isPlaying": song["isPlaying"],
            },
            "historyCount": len(history_rows(limit=200)),
        }
    )
