from flask import request

from . import api_bp
from .common import (
    body_json,
    current_user_id,
    current_user_profile,
    get_device,
    get_song,
    mysql_all,
    mysql_exec,
    mysql_one,
    next_id,
    now_str,
    ok,
    plain,
)


@api_bp.get("/friends/listening")
def friends_listening():
    room = mysql_one(
        """
        SELECT *
        FROM listen_room
        WHERE status='active'
        ORDER BY created_at DESC
        LIMIT 1
        """
    )

    if room:
        members = mysql_all(
            """
            SELECT m.user_id, m.role, m.online_status, u.username
            FROM listen_room_member m
            LEFT JOIN `user` u ON u.user_id=m.user_id
            WHERE m.room_id=%s AND m.left_at IS NULL
            ORDER BY m.joined_at ASC
            """,
            (room["room_id"],),
        )
        song = get_song(room.get("current_song_id"))
        room_data = {
            "roomId": str(room["room_id"]),
            "roomName": room.get("room_name") or "一起听歌",
            "songName": song["songName"],
            "memberCount": len(members),
            "members": [m.get("username") or f"用户{m.get('user_id')}" for m in members],
        }
    else:
        room_data = {"roomId": "room_001", "roomName": "【兜底数据】雨后电台", "songName": get_song()["songName"], "memberCount": 3, "members": ["【兜底数据】我", "【兜底数据】阿青", "【兜底数据】小北"]}

    friends = friend_rows(limit=10)

    return plain({"room": room_data, "recentFriends": friends})


def friend_rows(limit=10, keyword=None):
    user_id = current_user_id()
    params = [user_id, user_id]
    where = "(f.user_id_1=%s OR f.user_id_2=%s)"

    rows = mysql_all(
        f"""
        SELECT
            u.user_id,
            u.username
        FROM friendship f
        JOIN `user` u
          ON u.user_id = CASE WHEN f.user_id_1=%s THEN f.user_id_2 ELSE f.user_id_1 END
        WHERE {where}
        LIMIT {int(limit)}
        """,
        (user_id, user_id, user_id),
    )

    if keyword:
        rows = [row for row in rows if keyword in str(row.get("username", ""))]

    if not rows:
        rows = [
            {"user_id": "u_002", "username": "【兜底数据】阿青"},
            {"user_id": "u_003", "username": "【兜底数据】小北"},
        ]

    result = []
    for row in rows[:limit]:
        name = row.get("username") or f"用户{row.get('user_id')}"
        result.append(
            {
                "friendId": str(row.get("user_id")),
                "name": name,
                "nickname": name,
                "avatar": "",
                "status": "【兜底数据】正在听歌" if name != "【兜底数据】阿青" else "【兜底数据】刚分享了《晨光》",
                "isOnline": True,
            }
        )
    return result


@api_bp.get("/friends/search")
def friends_search():
    keyword = (request.args.get("keyword") or "").strip()
    friends = friend_rows(limit=20, keyword=keyword)

    return ok("搜索好友成功", {"total": len(friends), "page": 1, "pageSize": 10, "list": friends})


@api_bp.post("/listen-room/create")
def listen_room_create():
    body = body_json()
    user_id = current_user_id()
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    song = get_song(song_id)
    requested_room_name = str(body.get("roomName") or "").strip()
    room_name = requested_room_name or (song["songName"] + "一起听")
    room_id = next_id("listen_room", "room_id")
    room_code = f"room_{room_id}"

    mysql_exec(
        """
        INSERT INTO listen_room
        (room_id, room_code, owner_user_id, device_id, current_song_id, room_name,
         source_platform, status, created_at, ended_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NULL)
        """,
        (room_id, room_code, user_id, device_id if str(device_id).isdigit() else None, song_id, room_name, song["source"], "active"),
    )

    mysql_exec(
        """
        INSERT INTO listen_room_member
        (id, room_id, user_id, role, online_status, joined_at, left_at)
        VALUES (%s,%s,%s,%s,%s,NOW(),NULL)
        """,
        (next_id("listen_room_member", "id"), room_id, user_id, "owner", 1),
    )

    return ok(
        "一起听房间创建成功",
        {
            "roomId": str(room_id),
            "roomName": room_name,
            "songId": song_id,
            "songName": song["songName"],
            "deviceId": device_id,
            "ownerUserId": user_id,
            "memberCount": 1,
            "role": "owner",
            "status": "active",
        },
    )


@api_bp.post("/listen-room/join")
def listen_room_join():
    body = body_json()
    room_id = str(body.get("roomId") or "room_001")
    user_id = current_user_id()

    if room_id.isdigit():
        room = mysql_one("SELECT * FROM listen_room WHERE room_id=%s LIMIT 1", (room_id,))
    else:
        room = mysql_one("SELECT * FROM listen_room WHERE room_code=%s LIMIT 1", (room_id,))

    if room:
        exists = mysql_one(
            "SELECT id FROM listen_room_member WHERE room_id=%s AND user_id=%s AND left_at IS NULL LIMIT 1",
            (room["room_id"], user_id),
        )
        if not exists:
            mysql_exec(
                """
                INSERT INTO listen_room_member
                (id, room_id, user_id, role, online_status, joined_at, left_at)
                VALUES (%s,%s,%s,%s,%s,NOW(),NULL)
                """,
                (next_id("listen_room_member", "id"), room["room_id"], user_id, "member", 1),
            )
        members = room_members(room["room_id"])
        song = get_song(room.get("current_song_id"))
        return ok(
            "加入一起听房间成功",
            {
                "roomId": str(room["room_id"]),
                "roomName": room.get("room_name") or "一起听歌",
                "songId": song["songId"],
                "songName": song["songName"],
                "memberCount": len(members),
                "members": members,
                "syncDelay": 0.2,
                "status": room.get("status") or "active",
            },
        )

    song = get_song()
    return ok(
        "加入一起听房间成功",
        {
            "roomId": room_id,
            "roomName": "【兜底数据】雨后电台",
            "songId": song["songId"],
            "songName": song["songName"],
            "memberCount": 4,
            "members": [{"userId": 10001, "nickname": "【兜底数据】我", "role": "owner"}],
            "syncDelay": 0.2,
            "status": "active",
        },
    )


def room_members(room_id):
    rows = mysql_all(
        """
        SELECT m.user_id, m.role, m.online_status, u.username
        FROM listen_room_member m
        LEFT JOIN `user` u ON u.user_id=m.user_id
        WHERE m.room_id=%s AND m.left_at IS NULL
        ORDER BY m.joined_at ASC
        """,
        (room_id,),
    )

    return [
        {
            "userId": int(row.get("user_id")),
            "nickname": row.get("username") or f"用户{row.get('user_id')}",
            "avatar": "",
            "role": row.get("role") or "member",
            "online": bool(row.get("online_status")),
        }
        for row in rows
    ]


@api_bp.get("/listen-room/detail")
def listen_room_detail():
    room_id = request.args.get("roomId")
    room = None

    if room_id and str(room_id).isdigit():
        room = mysql_one("SELECT * FROM listen_room WHERE room_id=%s LIMIT 1", (room_id,))
    elif room_id:
        room = mysql_one("SELECT * FROM listen_room WHERE room_code=%s LIMIT 1", (room_id,))
    else:
        room = mysql_one("SELECT * FROM listen_room WHERE status='active' ORDER BY created_at DESC LIMIT 1")

    if room:
        song = get_song(room.get("current_song_id"))
        members = room_members(room["room_id"])
        return ok(
            "获取房间详情成功",
            {
                "roomId": str(room["room_id"]),
                "roomName": room.get("room_name") or "一起听歌",
                "status": room.get("status") or "active",
                "syncDelay": 0.2,
                "source": room.get("source_platform") or song["source"],
                "currentSong": {
                    "songId": song["songId"],
                    "songName": song["songName"],
                    "artist": song["artist"],
                    "coverUrl": song["coverUrl"],
                    "isPlaying": True,
                },
                "currentUser": {"userId": current_user_id(), "role": "owner", "isHost": current_user_id() == int(room.get("owner_user_id") or 0)},
                "members": members,
            },
        )

    song = get_song()
    return ok(
        "获取房间详情成功",
        {
            "roomId": room_id or "room_001",
            "roomName": "【兜底数据】雨后电台",
            "status": "active",
            "syncDelay": 0.2,
            "source": song["source"],
            "currentSong": {
                "songId": song["songId"],
                "songName": song["songName"],
                "artist": song["artist"],
                "coverUrl": song["coverUrl"],
                "isPlaying": True,
            },
            "currentUser": {"userId": current_user_id(), "role": "owner", "isHost": True},
            "members": [{"userId": current_user_id(), "nickname": "【兜底数据】我", "avatar": "", "role": "owner", "online": True}],
        },
    )


@api_bp.post("/listen-room/comment")
def listen_room_comment():
    body = body_json()
    content = str(body.get("content", "")).strip()
    room_id = str(body.get("roomId") or "")

    if not content:
        return ok("评论内容不能为空", {"field": "content"}, 400)

    comment_id = next_id("listen_room_comment", "comment_id")
    mysql_room_id = int(room_id) if room_id.isdigit() else None

    if mysql_room_id:
        mysql_exec(
            """
            INSERT INTO listen_room_comment
            (comment_id, room_id, user_id, content, created_at)
            VALUES (%s,%s,%s,%s,NOW())
            """,
            (comment_id, mysql_room_id, current_user_id(), content),
        )

    profile = current_user_profile()

    return ok(
        "评论发送成功",
        {
            "commentId": str(comment_id),
            "roomId": room_id or "room_001",
            "content": content,
            "sender": {"userId": profile["userId"], "nickname": profile["nickname"], "avatar": profile["avatar"]},
            "createdAt": now_str(),
        },
    )


@api_bp.post("/listen-room/leave")
def listen_room_leave():
    body = body_json()
    room_id = str(body.get("roomId") or "")
    user_id = current_user_id()

    if not room_id:
        return ok("房间 ID 不能为空", {"field": "roomId"}, 400)

    if room_id.isdigit():
        mysql_exec(
            "UPDATE listen_room_member SET left_at=NOW(), online_status=0 WHERE room_id=%s AND user_id=%s AND left_at IS NULL",
            (room_id, user_id),
        )
        count_row = mysql_one("SELECT COUNT(*) AS cnt FROM listen_room_member WHERE room_id=%s AND left_at IS NULL", (room_id,))
        member_count = int(count_row.get("cnt") or 0) if count_row else 0
    else:
        member_count = 2

    return ok(
        "退出一起听成功",
        {
            "roomId": room_id,
            "leftUserId": user_id,
            "memberCount": member_count,
            "roomStatus": "active",
            "isRoomClosed": False,
        },
    )
