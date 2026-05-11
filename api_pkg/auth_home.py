from . import api_bp
from .common import (
    body_json,
    create_or_get_wechat_user,
    create_token,
    current_user_id,
    current_user_profile,
    device_list,
    get_device,
    get_song,
    history_rows,
    ok,
    plain,
    now_str,
)


@api_bp.get("/_health")
def health():
    return ok("api routes loaded", {"time": now_str(), "mode": "mysql-mongo-real-with-visible-fallback"})


@api_bp.post("/auth/wechat-login")
def wechat_login():
    body = body_json()
    code = str(body.get("code", "")).strip()
    encrypted_data = body.get("encryptedData")
    iv = body.get("iv")

    if not code:
        return ok("请求参数错误", {"field": "code", "reason": "微信登录 code 不能为空"}, 400)

    if not encrypted_data or not iv:
        return ok("请求参数错误", {"field": "encryptedData/iv", "reason": "encryptedData 和 iv 不能为空"}, 400)

    nickname = body.get("nickname") or body.get("nickName") or "【兜底数据】微信用户"
    avatar = body.get("avatar") or body.get("avatarUrl") or ""

    user_id, nickname = create_or_get_wechat_user(code, nickname=nickname)
    token = create_token(user_id)

    has_device = len(device_list(user_id)) > 0

    return plain(
        {
            "token": token,
            "userId": int(user_id),
            "nickname": nickname,
            "avatar": avatar,
            "hasDevice": bool(has_device),
        }
    )


@api_bp.get("/home/overview")
def home_overview():
    user_id = current_user_id()
    device = get_device(user_id=user_id)
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
                "isPlaying": bool(song.get("isPlaying", True)),
            },
            "historyCount": len(history_rows(user_id=user_id, limit=200)),
        }
    )
