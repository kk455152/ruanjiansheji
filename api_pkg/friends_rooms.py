import secrets

from . import api_bp
from .common import body_json, current_user_id, get_device, get_song, mongo_one, now_str, ok, plain


@api_bp.get("/friends/listening")
def friends_listening():
    room = mongo_one("listen_rooms", {}, sort=[("updated_at", -1), ("_id", -1)]) or {}
    members = room.get("members") or [{"nickname": "我"}, {"nickname": "阿青"}, {"nickname": "小北"}]

    return plain(
        {
            "room": {
                "roomId": room.get("room_id") or "room_001",
                "roomName": room.get("room_name") or "雨后电台",
                "songName": (room.get("current_song") or {}).get("song_name") or get_song()["songName"],
                "memberCount": len(members),
                "members": [member.get("nickname") or member.get("account") for member in members],
            },
            "recentFriends": [
                {"friendId": "u_002", "name": "阿青", "status": "刚分享了歌曲"},
                {"friendId": "u_003", "name": "小北", "status": "正在听歌"},
            ],
        }
    )


@api_bp.get("/friends/search")
def friends_search():
    keyword = (request.args.get("keyword") or "").lower()
    rows = [
        {"friendId": "u_002", "nickname": "阿青", "avatar": "https://cdn.musicplayer.cn/avatar/u002.jpg", "status": "刚分享了歌曲", "isOnline": True},
        {"friendId": "u_003", "nickname": "小北", "avatar": "https://cdn.musicplayer.cn/avatar/u003.jpg", "status": "正在听歌", "isOnline": False},
    ]

    if keyword:
        rows = [row for row in rows if keyword in row["nickname"].lower() or keyword in row["status"].lower()]

    return ok("friend search success", {"total": len(rows), "page": 1, "pageSize": 10, "list": rows})


# request is imported here to keep route files small and local.
from flask import request  # noqa: E402


@api_bp.post("/listen-room/create")
def listen_room_create():
    body = body_json()
    room_id = "room_" + secrets.token_hex(4)
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song = get_song(body.get("songId"))

    return ok(
        "listen room created",
        {
            "roomId": room_id,
            "roomName": song["songName"] + "一起听",
            "songId": song["songId"],
            "songName": song["songName"],
            "deviceId": device_id,
            "ownerUserId": current_user_id(),
            "memberCount": 1,
            "role": "owner",
            "status": "active",
        },
    )


@api_bp.post("/listen-room/join")
def listen_room_join():
    song = get_song()

    return ok(
        "listen room joined",
        {
            "roomId": body_json().get("roomId", "room_001"),
            "roomName": "雨后电台",
            "songId": song["songId"],
            "songName": song["songName"],
            "memberCount": 3,
            "members": [{"userId": 10001, "nickname": "我", "role": "owner"}],
            "syncDelay": 0.2,
            "status": "active",
        },
    )


@api_bp.get("/listen-room/detail")
def listen_room_detail():
    song = get_song()

    return ok(
        "listen room detail success",
        {
            "roomId": request.args.get("roomId") or "room_001",
            "roomName": "雨后电台",
            "status": "active",
            "syncDelay": 0.2,
            "source": song["source"],
            "currentSong": {
                "songId": song["songId"],
                "songName": song["songName"],
                "artist": song["artist"],
                "coverUrl": song["coverUrl"],
                "isPlaying": song["isPlaying"],
            },
            "currentUser": {"userId": current_user_id(), "role": "owner", "isHost": True},
            "members": [{"userId": 10001, "nickname": "我", "role": "owner"}],
        },
    )


@api_bp.post("/listen-room/comment")
def listen_room_comment():
    body = body_json()

    if not str(body.get("content", "")).strip():
        return ok("comment content is required", {"field": "content"}, 400)

    return ok(
        "comment sent",
        {
            "commentId": "comment_" + secrets.token_hex(4),
            "roomId": body.get("roomId", "room_001"),
            "content": body["content"],
            "sender": {"userId": current_user_id(), "nickname": "我", "avatar": ""},
            "createdAt": now_str(),
        },
    )


@api_bp.post("/listen-room/leave")
def listen_room_leave():
    return ok(
        "listen room left",
        {
            "roomId": body_json().get("roomId", "room_001"),
            "leftUserId": current_user_id(),
            "memberCount": 2,
            "roomStatus": "active",
            "isRoomClosed": False,
        },
    )
