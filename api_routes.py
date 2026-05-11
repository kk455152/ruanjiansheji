import json
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:
    pymysql = None
    DictCursor = None

try:
    from bson import ObjectId
    from pymongo import MongoClient
except Exception:
    ObjectId = None
    MongoClient = None


api_bp = Blueprint("api_routes", __name__, url_prefix="/api")

BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, "runtime", "api_mock_state.json")
_mongo_client = None


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_safe(value):
    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(val) for key, val in value.items()}
    return value


def default_state():
    return {
        "tokens": {},
        "device": {
            "deviceId": "dev_001",
            "deviceSn": "SHMINI-A1-0001",
            "deviceName": "Living Room Speaker",
            "modelName": "SH-Mini A1",
            "online": True,
            "battery": 82,
            "volume": 60,
            "signalStrength": -65,
            "bassGain": 8,
            "currentNetwork": "Home-5G",
            "volumeLimit": 80,
            "lowBatteryThreshold": 20,
            "powerSaveEnabled": False,
            "isCharging": False,
            "fullChargeNotice": True,
            "isConnecting": False,
        },
        "playing": {
            "songId": "song_001",
            "songName": "City Night Flight",
            "artist": "Luna Echo",
            "source": "netease",
            "isPlaying": True,
            "coverUrl": "https://cdn.musicplayer.cn/song_001.jpg",
            "album": "After Rain Radio",
            "durationMs": 262060,
        },
        "history": [
            {"historyId": 1, "songId": "song_001", "songName": "City Night Flight", "artist": "Luna Echo", "source": "netease", "playedAt": "2026-05-08 22:14", "coverUrl": "https://xxx.jpg"}
        ],
        "queue": [],
        "music_services": {
            "qq": {"service": "qq", "serviceName": "QQ Music", "bound": True, "accountName": "Demo User", "syncStatus": "synced"},
            "netease": {"service": "netease", "serviceName": "Netease Cloud Music", "bound": True, "accountName": "Netease User", "syncStatus": "syncing"},
        },
    }


def load_state():
    state = default_state()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        save_state(state)
        return state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            stored = json.load(file)
    except Exception:
        save_state(state)
        return state
    for key, value in state.items():
        stored.setdefault(key, value)
    return stored


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(json_safe(state), file, ensure_ascii=False, indent=2)


def body_json():
    return request.get_json(silent=True) or {}


def ok(message, data=None, code=200):
    return jsonify({"code": code, "message": message, "data": json_safe(data)}), code


def plain(data, code=200):
    return jsonify(json_safe(data)), code


def mysql_conn():
    if pymysql is None:
        return None
    try:
        return pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", ""),
            database=os.environ.get("MYSQL_DATABASE", os.environ.get("MYSQL_DB", "smart_speaker")),
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=2,
            read_timeout=3,
            write_timeout=3,
            autocommit=False,
        )
    except Exception:
        return None


def mysql_one(sql, params=()):
    conn = mysql_conn()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        conn.close()


def mysql_all(sql, params=()):
    conn = mysql_conn()
    if conn is None:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall() or []
    except Exception:
        return []
    finally:
        conn.close()


def mysql_exec(sql, params=()):
    conn = mysql_conn()
    if conn is None:
        return 0
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            affected = cursor.rowcount
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        return 0
    finally:
        conn.close()


def mongo_db():
    global _mongo_client
    if MongoClient is None:
        return None
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(
                os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017"),
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500,
                socketTimeoutMS=1500,
            )
            _mongo_client.admin.command("ping")
        return _mongo_client[os.environ.get("MONGO_DATABASE", os.environ.get("MONGO_DB", "musicplayer"))]
    except Exception:
        return None


def mongo_one(collection, query=None, sort=None):
    db = mongo_db()
    if db is None:
        return None
    try:
        return db[collection].find_one(query or {}, sort=sort)
    except Exception:
        return None


def mongo_many(collection, query=None, sort=None, limit=20):
    db = mongo_db()
    if db is None:
        return []
    try:
        return list(db[collection].find(query or {}, sort=sort, limit=limit))
    except Exception:
        return []


def mongo_update(collection, query, update, upsert=True):
    db = mongo_db()
    if db is None:
        return False
    try:
        db[collection].update_one(query, update, upsert=upsert)
        return True
    except Exception:
        return False


def current_user_id():
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        auth = auth[7:].strip()
    row = mysql_one(
        "SELECT user_id FROM auth_token WHERE access_token=%s AND expires_at > NOW() ORDER BY auth_id DESC LIMIT 1",
        (auth,),
    )
    if row and row.get("user_id"):
        return int(row["user_id"])
    return int(load_state().get("tokens", {}).get(auth, 10001))


def get_device(device_id=None):
    fallback = load_state()["device"]
    if device_id:
        row = mysql_one(
            """
            SELECT d.device_id,d.device_number,d.model_name,COALESCE(d.status,0) status,d.last_active,b.custom_device_name
            FROM device d LEFT JOIN user_device_binding b ON b.device_id=d.device_id
            WHERE d.device_id=%s OR d.device_number=%s LIMIT 1
            """,
            (device_id, device_id),
        )
    else:
        row = mysql_one(
            """
            SELECT d.device_id,d.device_number,d.model_name,COALESCE(d.status,0) status,d.last_active,b.custom_device_name
            FROM user_device_binding b JOIN device d ON d.device_id=b.device_id
            WHERE b.user_id=%s ORDER BY COALESCE(b.is_primary,1) DESC,d.device_id ASC LIMIT 1
            """,
            (current_user_id(),),
        )
    if not row:
        return fallback
    runtime = mongo_one("device_runtime", {"device_id": str(row.get("device_id"))}) or {}
    metrics = runtime.get("metrics") if isinstance(runtime.get("metrics"), dict) else {}
    return {
        "deviceId": str(row.get("device_id") or fallback["deviceId"]),
        "deviceSn": row.get("device_number") or fallback["deviceSn"],
        "deviceName": row.get("custom_device_name") or fallback["deviceName"],
        "modelName": row.get("model_name") or fallback["modelName"],
        "online": bool(row.get("status")),
        "battery": int(metrics.get("battery", fallback["battery"]) or 0),
        "volume": int(metrics.get("volume", fallback["volume"]) or 0),
        "signalStrength": metrics.get("signal_strength", fallback["signalStrength"]),
        "bassGain": metrics.get("bass_gain", fallback["bassGain"]),
        "currentNetwork": metrics.get("current_network", fallback["currentNetwork"]),
        "volumeLimit": int(metrics.get("volume_limit", fallback["volumeLimit"]) or fallback["volumeLimit"]),
        "lowBatteryThreshold": int(metrics.get("low_battery_threshold", fallback["lowBatteryThreshold"]) or fallback["lowBatteryThreshold"]),
        "powerSaveEnabled": bool(metrics.get("power_save_enabled", fallback["powerSaveEnabled"])),
        "isCharging": bool(metrics.get("is_charging", fallback["isCharging"])),
        "fullChargeNotice": bool(metrics.get("full_charge_notice", fallback["fullChargeNotice"])),
        "isConnecting": bool(metrics.get("is_connecting", fallback["isConnecting"])),
    }


def get_song(song_id=None):
    fallback = load_state()["playing"]
    doc = None
    if song_id:
        doc = mongo_one("media_metadata", {"song_id": str(song_id)}) or mongo_one("song_info", {"song_id": str(song_id)})
    doc = doc or mongo_one("player_state", {}, sort=[("updated_at", -1), ("_id", -1)]) or {}
    artists = doc.get("artists") or doc.get("artist") or fallback["artist"]
    if isinstance(artists, list):
        artist_text = " / ".join([str(item.get("name") if isinstance(item, dict) else item) for item in artists])
        artist_list = [str(item.get("name") if isinstance(item, dict) else item) for item in artists]
    else:
        artist_text = str(artists)
        artist_list = [artist_text]
    duration_ms = doc.get("duration_ms") or fallback["durationMs"]
    return {
        "songId": str(doc.get("song_id") or doc.get("songId") or doc.get("external_id") or song_id or fallback["songId"]),
        "songName": doc.get("song_name") or doc.get("name") or fallback["songName"],
        "name": doc.get("name") or doc.get("song_name") or fallback["songName"],
        "artist": doc.get("artist_text") or artist_text or fallback["artist"],
        "artistText": doc.get("artist_text") or artist_text or fallback["artist"],
        "artists": artist_list,
        "album": doc.get("album") or fallback["album"],
        "source": doc.get("platform") or (doc.get("source") if isinstance(doc.get("source"), str) else None) or fallback["source"],
        "isPlaying": bool(doc.get("is_playing", fallback["isPlaying"])),
        "coverUrl": doc.get("cover_url") or fallback["coverUrl"],
        "durationMs": int(duration_ms or 0),
        "durationSeconds": int((duration_ms or 0) / 1000),
    }


def history_rows(limit=20, source=None, keyword=None):
    query = {}
    if source:
        query["platform"] = source
    if keyword:
        query["$or"] = [{"song_name": {"$regex": keyword, "$options": "i"}}, {"artist_text": {"$regex": keyword, "$options": "i"}}]
    docs = mongo_many("play_logs", query, sort=[("played_at", -1), ("_id", -1)], limit=limit)
    rows = [
        {
            "historyId": str(doc.get("event_id") or doc.get("_id")),
            "songId": str(doc.get("song_id") or ""),
            "songName": doc.get("song_name") or "",
            "artist": doc.get("artist_text") or " / ".join(doc.get("artists") or []),
            "source": doc.get("platform") or "netease",
            "playedAt": json_safe(doc.get("played_at") or doc.get("created_at") or ""),
            "coverUrl": doc.get("cover_url") or "",
        }
        for doc in docs
    ]
    if not rows:
        rows = load_state()["history"]
    if source:
        rows = [row for row in rows if row.get("source") == source]
    if keyword:
        rows = [row for row in rows if keyword in row.get("songName", "") or keyword in row.get("artist", "")]
    return rows


@api_bp.before_app_request
def legacy_device_list():
    if request.path == "/device/list" and request.method == "GET":
        return jsonify({"code": 200, "msg": "success", "data": device_list_data()}), 200


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
                    cursor.execute("INSERT INTO `user` (username,password_hash,phone) VALUES (%s,%s,%s)", (username, secrets.token_hex(16), None))
                    user_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO auth_token (user_id,platform_type,access_token,refresh_token,expires_at) VALUES (%s,%s,%s,%s,%s)",
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
    return plain({"token": token, "userId": user_id, "nickname": body.get("nickname") or body.get("nickName") or "Miniapp User", "avatar": body.get("avatar") or body.get("avatarUrl") or "", "hasDevice": True})


@api_bp.get("/home/overview")
def home_overview():
    d = get_device()
    p = get_song()
    return plain({"device": {"deviceId": d["deviceId"], "name": d["deviceName"], "model": d["modelName"], "online": d["online"], "battery": d["battery"]}, "playing": {"songId": p["songId"], "songName": p["songName"], "artist": p["artist"], "source": p["source"], "isPlaying": p["isPlaying"]}, "historyCount": len(history_rows(limit=200))})


@api_bp.post("/player/control")
def player_control():
    body = body_json()
    action = str(body.get("action", "")).lower()
    if action not in ("play", "pause", "previous", "next"):
        return ok("invalid player action", {"action": action}, 400)
    d = str(body.get("deviceId") or get_device()["deviceId"])
    p = get_song()
    is_playing = action != "pause"
    mongo_update("player_state", {"device_id": d}, {"$set": {"device_id": d, "song_id": p["songId"], "song_name": p["songName"], "artist": p["artist"], "source": body.get("source") or p["source"], "is_playing": is_playing, "updated_at": datetime.now()}})
    return ok("player control success", {"deviceId": d, "action": action, "isPlaying": is_playing, "currentSong": {"songId": p["songId"], "songName": p["songName"], "artist": p["artist"]}})


@api_bp.post("/player/volume")
def player_volume():
    body = body_json()
    try:
        volume = max(0, min(100, int(body.get("volume", 60))))
    except Exception:
        return ok("invalid volume", {"field": "volume"}, 400)
    d = str(body.get("deviceId") or get_device()["deviceId"])
    mongo_update("device_runtime", {"device_id": d}, {"$set": {"device_id": d, "metrics.volume": volume, "updated_at": datetime.now()}})
    return ok("volume set success", {"deviceId": d, "volume": volume, "isMuted": volume == 0})


@api_bp.post("/player/play-song")
def play_song():
    body = body_json()
    d = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    p = get_song(song_id)
    mongo_update("player_state", {"device_id": d}, {"$set": {"device_id": d, "song_id": song_id, "song_name": p["songName"], "artist": p["artist"], "source": p["source"], "is_playing": True, "updated_at": datetime.now()}})
    return ok("song play success", {"deviceId": d, "songId": song_id, "songName": p["songName"], "artist": p["artist"], "source": p["source"], "isPlaying": True, "playTime": 0})


@api_bp.post("/player/add-next")
def add_next():
    body = body_json()
    d = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    state = load_state()
    if song_id in [str(item.get("songId")) for item in state.get("queue", [])]:
        return ok("song already queued next", {"deviceId": d, "songId": song_id, "queuePosition": 1}, 409)
    p = get_song(song_id)
    item = {"deviceId": d, "songId": song_id, "songName": p["songName"], "artist": p["artist"], "queuePosition": 1}
    state.setdefault("queue", []).insert(0, item)
    save_state(state)
    mongo_update("play_queue", {"device_id": d}, {"$push": {"queue": {"$each": [{"song_id": song_id, "song_name": p["songName"], "artist": p["artist"], "position": 1}], "$position": 0}}, "$set": {"updated_at": datetime.now()}})
    return ok("song queued next", item)


@api_bp.get("/friends/listening")
def friends_listening():
    room = mongo_one("listen_rooms", {}, sort=[("updated_at", -1), ("_id", -1)]) or {}
    members = room.get("members") or [{"nickname": "Me"}, {"nickname": "Aqing"}, {"nickname": "Xiaobei"}]
    return plain({"room": {"roomId": room.get("room_id") or "room_001", "roomName": room.get("room_name") or "After Rain Radio", "songName": (room.get("current_song") or {}).get("song_name") or get_song()["songName"], "memberCount": len(members), "members": [m.get("nickname") or m.get("account") for m in members]}, "recentFriends": [{"friendId": "u_002", "name": "Aqing", "status": "just shared a song"}, {"friendId": "u_003", "name": "Xiaobei", "status": "listening"}]})


@api_bp.get("/friends/search")
def friends_search():
    keyword = (request.args.get("keyword") or "").lower()
    rows = [{"friendId": "u_002", "nickname": "Aqing", "avatar": "https://cdn.musicplayer.cn/avatar/u002.jpg", "status": "just shared a song", "isOnline": True}, {"friendId": "u_003", "nickname": "Xiaobei", "avatar": "https://cdn.musicplayer.cn/avatar/u003.jpg", "status": "listening", "isOnline": False}]
    if keyword:
        rows = [row for row in rows if keyword in row["nickname"].lower() or keyword in row["status"].lower()]
    return ok("friend search success", {"total": len(rows), "page": 1, "pageSize": 10, "list": rows})


@api_bp.post("/listen-room/create")
def listen_room_create():
    body = body_json()
    room_id = "room_" + secrets.token_hex(4)
    d = str(body.get("deviceId") or get_device()["deviceId"])
    p = get_song(body.get("songId"))
    return ok("listen room created", {"roomId": room_id, "roomName": p["songName"] + " Listen Together", "songId": p["songId"], "songName": p["songName"], "deviceId": d, "ownerUserId": current_user_id(), "memberCount": 1, "role": "owner", "status": "active"})


@api_bp.post("/listen-room/join")
def listen_room_join():
    return ok("listen room joined", {"roomId": body_json().get("roomId", "room_001"), "roomName": "After Rain Radio", "songId": get_song()["songId"], "songName": get_song()["songName"], "memberCount": 3, "members": [{"userId": 10001, "nickname": "Me", "role": "owner"}], "syncDelay": 0.2, "status": "active"})


@api_bp.get("/listen-room/detail")
def listen_room_detail():
    p = get_song()
    return ok("listen room detail success", {"roomId": request.args.get("roomId") or "room_001", "roomName": "After Rain Radio", "status": "active", "syncDelay": 0.2, "source": p["source"], "currentSong": {"songId": p["songId"], "songName": p["songName"], "artist": p["artist"], "coverUrl": p["coverUrl"], "isPlaying": p["isPlaying"]}, "currentUser": {"userId": current_user_id(), "role": "owner", "isHost": True}, "members": [{"userId": 10001, "nickname": "Me", "role": "owner"}]})


@api_bp.post("/listen-room/comment")
def listen_room_comment():
    body = body_json()
    if not str(body.get("content", "")).strip():
        return ok("comment content is required", {"field": "content"}, 400)
    return ok("comment sent", {"commentId": "comment_" + secrets.token_hex(4), "roomId": body.get("roomId", "room_001"), "content": body["content"], "sender": {"userId": current_user_id(), "nickname": "Me", "avatar": ""}, "createdAt": now_str()})


@api_bp.post("/listen-room/leave")
def listen_room_leave():
    return ok("listen room left", {"roomId": body_json().get("roomId", "room_001"), "leftUserId": current_user_id(), "memberCount": 2, "roomStatus": "active", "isRoomClosed": False})


@api_bp.post("/share/song-link")
def share_song_link():
    body = body_json()
    share_id = "share_" + secrets.token_hex(4)
    return ok("share link created", {"shareId": share_id, "songId": body.get("songId", "song_001"), "roomId": body.get("roomId", "room_001"), "shareUrl": "https://api.musicplayer.cn/share/" + share_id, "expireAt": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")})


@api_bp.post("/share/song-card")
def share_song_card():
    body = body_json()
    card_id = "card_" + secrets.token_hex(4)
    return ok("share card created", {"cardId": card_id, "songId": body.get("songId", "song_001"), "roomId": body.get("roomId", "room_001"), "imageUrl": "https://cdn.musicplayer.cn/share/" + card_id + ".png", "previewUrl": "https://cdn.musicplayer.cn/share/preview/" + card_id + ".png", "expireAt": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")})


@api_bp.get("/listening-data/summary")
def listening_data_summary():
    return plain({"code": 200, "data": {"minutes": 428, "songCount": len(history_rows(limit=200)), "favoriteStyle": "Chinese Pop", "activeTime": "21:00-23:00", "topPercent": "Top 12%"}})


@api_bp.get("/song-info")
def song_info():
    p = get_song(request.args.get("songId") or "1491830535")
    return plain({"code": 200, "data": {"songId": p["songId"], "name": p["name"], "album": p["album"], "artistText": p["artistText"], "artists": p["artists"], "coverUrl": p["coverUrl"], "durationMs": p["durationMs"], "durationSeconds": p["durationSeconds"], "source": p["source"]}})


@api_bp.get("/listening-data/weekly-report")
def weekly_report():
    return ok("weekly report success", {"year": int(request.args.get("year") or datetime.now().year), "week": int(request.args.get("week") or datetime.now().isocalendar().week), "rank": "Top 12%", "minutes": 428, "compareLastWeek": "23% more than last week", "summaryText": "Night listening increased.", "topArtist": {"artistName": "Luna Echo", "songCount": 12}, "topPlaylist": {"playlistName": "Night Focus", "playCount": 18}})


@api_bp.post("/listening-data/generate-card")
def generate_card():
    body = body_json()
    return ok("summary card generated", {"imageUrl": "https://xxx.com/report/week19.png", "year": int(body.get("year", 2026)), "week": int(body.get("week", 19)), "cardType": body.get("cardType", "weekly")})


@api_bp.get("/play-history/list")
def play_history_list():
    return plain({"code": 200, "data": {"list": history_rows(source=request.args.get("source"), keyword=request.args.get("keyword"))}})


@api_bp.delete("/play-history/clear-old")
def clear_old_history():
    days = int(body_json().get("days", 30) or 30)
    deleted = mysql_exec("DELETE FROM play_history WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)", (days,)) or 18
    return ok("old history cleared", {"days": days, "deletedCount": deleted})


@api_bp.delete("/play-history/delete")
def delete_history():
    history_id = str(body_json().get("historyId", "")).strip()
    if not history_id:
        return ok("historyId is required", {"field": "historyId"}, 400)
    mysql_exec("DELETE FROM play_history WHERE history_id=%s", (history_id,))
    return ok("play history deleted", {"historyId": history_id})


def device_list_data():
    rows = mysql_all(
        """
        SELECT d.device_id,d.device_number,b.custom_device_name,COALESCE(b.is_primary,1) is_primary,d.model_name,COALESCE(d.status,0) status,d.last_active
        FROM device d LEFT JOIN user_device_binding b ON b.device_id=d.device_id
        ORDER BY COALESCE(b.is_primary,0) DESC,d.device_id ASC LIMIT 20
        """
    )
    if rows:
        return [{"device_id": str(r.get("device_id")), "device_number": r.get("device_number"), "custom_device_name": r.get("custom_device_name") or r.get("device_number"), "is_primary": int(r.get("is_primary") or 0), "model_name": r.get("model_name"), "status": int(r.get("status") or 0), "last_active": json_safe(r.get("last_active") or now_str())} for r in rows]
    d = load_state()["device"]
    return [{"device_id": "1", "device_number": d["deviceSn"], "custom_device_name": d["deviceName"], "is_primary": 1, "model_name": d["modelName"], "status": 1 if d["online"] else 0, "last_active": now_str()}]


@api_bp.get("/device/list")
def device_list():
    return ok("device list success", device_list_data())


@api_bp.get("/device/detail")
def device_detail():
    d = get_device(request.args.get("deviceId"))
    return plain({"code": 200, "data": {"deviceId": d["deviceId"], "deviceName": d["deviceName"], "modelName": d["modelName"], "online": d["online"], "isConnecting": d["isConnecting"], "volume": d["volume"], "signalStrength": d["signalStrength"], "bassGain": d["bassGain"], "currentNetwork": d["currentNetwork"], "volumeLimit": d["volumeLimit"]}})


@api_bp.get("/device/battery")
def device_battery():
    d = get_device(request.args.get("deviceId"))
    return ok("battery info success", {"deviceId": d["deviceId"], "battery": d["battery"], "estimatedPlayTime": "11h20m", "lowBatteryThreshold": d["lowBatteryThreshold"], "powerSaveEnabled": d["powerSaveEnabled"], "isCharging": d["isCharging"], "fullChargeNotice": d["fullChargeNotice"]})


@api_bp.post("/device/power-save")
def power_save():
    body = body_json()
    return ok("power save set", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "powerSaveEnabled": bool(body.get("enabled", True))})


@api_bp.post("/device/battery-notice")
def battery_notice():
    body = body_json()
    return ok("battery notice set", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "lowBatteryEnabled": bool(body.get("lowBatteryEnabled", True)), "threshold": int(body.get("threshold", 20)), "fullChargeNotice": bool(body.get("fullChargeNotice", True))})


@api_bp.post("/device/rename")
def device_rename():
    body = body_json()
    name = str(body.get("name", "")).strip()
    if not name:
        return ok("device name is required", {"field": "name"}, 400)
    return ok("device renamed", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "name": name})


@api_bp.post("/device/advanced-settings")
def advanced_settings():
    body = body_json()
    return ok("advanced settings saved", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "volumeLimit": int(body.get("volumeLimit", 80)), "nightModeEnabled": bool(body.get("nightModeEnabled", True)), "nightStart": body.get("nightStart", "23:00"), "nightEnd": body.get("nightEnd", "07:00"), "autoFirmwareUpdate": bool(body.get("autoFirmwareUpdate", True))})


@api_bp.get("/device/search-nearby")
def search_nearby():
    keyword = (request.args.get("keyword") or "").lower()
    rows = [{"deviceId": "dev_001", "deviceName": "Living Room Speaker", "modelName": "SH-Mini A1", "signalStrength": -65, "online": True, "binded": False}]
    if keyword:
        rows = [row for row in rows if keyword in row["deviceName"].lower() or keyword in row["modelName"].lower()]
    return ok("nearby devices found", {"total": len(rows), "list": rows})


@api_bp.post("/device/bind")
def device_bind():
    body = body_json()
    sn = str(body.get("deviceSn") or "SHMINI-A1-0001")
    return ok("device binding started", {"taskId": "bind_001", "deviceSn": sn, "deviceName": "Smart Speaker", "status": "binding", "progress": 0})


@api_bp.get("/device/bind-progress")
def bind_progress():
    return plain({"progress": 70, "steps": [{"name": "Discover speaker", "status": "done"}, {"name": "Write Wi-Fi", "status": "doing"}, {"name": "Bind account", "status": "waiting"}]})


@api_bp.post("/device/unbind")
def device_unbind():
    return ok("device unbound", {"deviceId": body_json().get("deviceId", get_device()["deviceId"]), "unbound": True})


SERVICE_NAMES = {"qq": "QQ Music", "netease": "Netease Cloud Music"}


@api_bp.post("/music-service/bind")
def music_bind():
    service = str(body_json().get("service", "qq"))
    if service not in SERVICE_NAMES:
        return ok("unsupported music service", {"service": service}, 404)
    return ok("music service bound", {"service": service, "bound": True, "accountName": "Music User"})


@api_bp.get("/music-service/list")
def music_list():
    return ok("music service list success", {"services": list(load_state()["music_services"].values())})


@api_bp.get("/music-service/sync-progress")
def music_sync():
    service = request.args.get("service") or "qq"
    return ok("sync progress success", {"service": service, "status": "syncing", "progress": 68, "currentTask": "Syncing favorite songs", "totalSongs": 1200, "syncedSongs": 780})


@api_bp.post("/music-service/permissions")
def music_permissions():
    body = body_json()
    return ok("permissions updated", {"service": body.get("service", "qq"), "permissions": body.get("permissions") or {"readPlaylist": True, "syncHistory": True, "personalRecommend": True}})


@api_bp.post("/music-service/unbind")
def music_unbind():
    return ok("music service unbound", {"service": body_json().get("service", "qq"), "unbound": True})
