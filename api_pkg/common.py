import json
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from flask import jsonify, request

try:
    from bson import ObjectId
except Exception:
    ObjectId = None

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:
    pymysql = None
    DictCursor = None

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

try:
    from db import get_mysql_conn as project_mysql_conn
except Exception:
    project_mysql_conn = None

try:
    from db import mongo_db as project_mongo_db
except Exception:
    project_mongo_db = None


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATE_FILE = os.path.join(BASE_DIR, "runtime", "api_fallback_state.json")
_mongo_client = None


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_safe(value):
    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    return value


def ok(message, data=None, code=200):
    return jsonify({"code": code, "message": message, "data": json_safe(data)}), code


def plain(data, code=200):
    return jsonify(json_safe(data)), code


def body_json():
    return request.get_json(silent=True) or {}


def fallback_state():
    return {
        "tokens": {},
        "device": {
            "deviceId": "dev_001",
            "deviceSn": "SHMINI-A1-0001",
            "deviceName": "【兜底数据】客厅音箱",
            "modelName": "【兜底数据】SH-Mini A1",
            "firmware": "2.4.8",
            "online": True,
            "isConnecting": False,
            "battery": 82,
            "volume": 60,
            "signalStrength": -73.59,
            "bassGain": 8,
            "currentNetwork": "Home-5G",
            "defaultRoom": "客厅",
            "volumeLimit": 80,
            "lowBatteryThreshold": 20,
            "powerSaveEnabled": False,
            "isCharging": False,
            "fullChargeNotice": True,
            "lowBatteryEnabled": True,
            "nightModeEnabled": True,
            "nightStart": "23:00",
            "nightEnd": "07:00",
            "autoFirmwareUpdate": True,
        },
        "playing": {
            "songId": "song_001",
            "songName": "【兜底数据】城市夜航",
            "name": "【兜底数据】城市夜航",
            "artist": "【兜底数据】Luna Echo",
            "artistText": "【兜底数据】Luna Echo",
            "artists": ["【兜底数据】Luna Echo"],
            "album": "【兜底数据】雨后电台",
            "source": "netease",
            "isPlaying": True,
            "coverUrl": "https://cdn.musicplayer.cn/song_001.jpg",
            "durationMs": 262060,
            "durationSeconds": 262,
            "playTime": 0,
        },
        "history": [
            {
                "historyId": 1,
                "songId": "song_001",
                "songName": "【兜底数据】城市夜航",
                "artist": "【兜底数据】Luna Echo",
                "source": "netease",
                "playedAt": "2026-05-08 22:14",
                "coverUrl": "https://xxx.jpg",
            },
            {
                "historyId": 2,
                "songId": "song_002",
                "songName": "【兜底数据】雨后电台",
                "artist": "【兜底数据】阿青",
                "source": "qq",
                "playedAt": "2026-05-08 21:37",
                "coverUrl": "https://xxx.jpg",
            },
        ],
        "queue": [],
        "music_services": {
            "qq": {
                "service": "qq",
                "serviceName": "QQ 音乐",
                "bound": True,
                "accountName": "【兜底数据】用户昵称",
                "syncStatus": "synced",
            },
            "netease": {
                "service": "netease",
                "serviceName": "网易云音乐",
                "bound": True,
                "accountName": "【兜底数据】网易云用户",
                "syncStatus": "syncing",
            },
        },
        "permissions": {
            "qq": {"readPlaylist": True, "syncHistory": True, "personalRecommend": True},
            "netease": {"readPlaylist": True, "syncHistory": True, "personalRecommend": True},
        },
    }


def load_state():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    default = fallback_state()

    if not os.path.exists(STATE_FILE):
        save_state(default)
        return default

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        save_state(default)
        return default

    for key, value in default.items():
        data.setdefault(key, value)
    return data


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(json_safe(state), f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def mysql_conn():
    if project_mysql_conn is not None:
        try:
            return project_mysql_conn()
        except Exception:
            pass

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
            autocommit=False,
            connect_timeout=2,
            read_timeout=3,
            write_timeout=3,
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
        try:
            conn.close()
        except Exception:
            pass


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
        try:
            conn.close()
        except Exception:
            pass


def mysql_exec(sql, params=(), fetch_last_id=False):
    conn = mysql_conn()
    if conn is None:
        return None if fetch_last_id else 0
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.lastrowid if fetch_last_id else cursor.rowcount
        conn.commit()
        return result
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None if fetch_last_id else 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


def mysql_transaction(callback):
    conn = mysql_conn()
    if conn is None:
        return None
    try:
        result = callback(conn)
        conn.commit()
        return result
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def next_id(table, pk):
    row = mysql_one(f"SELECT COALESCE(MAX(`{pk}`), 0) + 1 AS next_id FROM `{table}`")
    try:
        return int(row["next_id"])
    except Exception:
        # 退路：bigint，不依赖自增；避免重复概率很低
        return int(datetime.now().strftime("%m%d%H%M%S%f"))


def mongo_db():
    global _mongo_client

    if project_mongo_db is not None:
        try:
            return project_mongo_db
        except Exception:
            pass

    if MongoClient is None:
        return None

    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(
                os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017"),
                serverSelectionTimeoutMS=1200,
                connectTimeoutMS=1200,
                socketTimeoutMS=1200,
            )
        _mongo_client.admin.command("ping")
        return _mongo_client[os.environ.get("MONGO_DATABASE", os.environ.get("MONGO_DB", "musicplayer"))]
    except Exception:
        return None


def mongo_one(collections, query=None, sort=None):
    db = mongo_db()
    if db is None:
        return None

    if isinstance(collections, str):
        collections = [collections]

    for collection in collections:
        try:
            doc = db[collection].find_one(query or {}, sort=sort)
            if doc:
                return doc
        except Exception:
            continue
    return None


def mongo_many(collections, query=None, sort=None, limit=20):
    db = mongo_db()
    if db is None:
        return []

    if isinstance(collections, str):
        collections = [collections]

    for collection in collections:
        try:
            docs = list(db[collection].find(query or {}, sort=sort, limit=limit))
            if docs:
                return docs
        except Exception:
            continue
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

    if auth:
        row = mysql_one(
            """
            SELECT user_id
            FROM auth_token
            WHERE access_token=%s AND expires_at > NOW()
            ORDER BY expires_at DESC
            LIMIT 1
            """,
            (auth,),
        )
        if row and row.get("user_id"):
            return int(row["user_id"])

    return int(load_state().get("tokens", {}).get(auth, 10001))


def current_user_profile(user_id=None):
    user_id = int(user_id or current_user_id())
    row = mysql_one("SELECT user_id, username, phone, created_at FROM `user` WHERE user_id=%s LIMIT 1", (user_id,))
    if row:
        return {
            "userId": int(row["user_id"]),
            "nickname": row.get("username") or f"用户{user_id}",
            "avatar": "",
            "phone": row.get("phone"),
        }
    return {"userId": user_id, "nickname": "【兜底数据】我", "avatar": "", "phone": None}


def create_or_get_wechat_user(code, nickname=None):
    username = "wx_" + str(code).strip()[:40]
    row = mysql_one("SELECT user_id, username FROM `user` WHERE username=%s LIMIT 1", (username,))
    if row:
        return int(row["user_id"]), row.get("username") or nickname or "【兜底数据】微信用户"

    password_hash = secrets.token_hex(16)

    def callback(conn):
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO `user` (username, password_hash, phone) VALUES (%s, %s, %s)",
                (username, password_hash, None),
            )
            return cursor.lastrowid

    user_id = mysql_transaction(callback)
    if user_id:
        return int(user_id), nickname or username

    # 数据库不可写时仍保证接口通
    return 10001, nickname or "【兜底数据】微信用户"


def create_token(user_id, platform_type="wechat_mini"):
    access_token = "mini_" + secrets.token_hex(24)
    refresh_token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=7)
    auth_id = next_id("auth_token", "auth_id")

    mysql_exec(
        """
        INSERT INTO auth_token
        (auth_id, user_id, platform_type, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (auth_id, user_id, platform_type, access_token, refresh_token, expires_at),
    )

    state = load_state()
    state.setdefault("tokens", {})[access_token] = user_id
    save_state(state)
    return access_token


def song_from_mysql(external_id=None, mapping_id=None):
    if mapping_id:
        row = mysql_one("SELECT * FROM media_mapping WHERE mapping_id=%s LIMIT 1", (mapping_id,))
    else:
        row = mysql_one("SELECT * FROM media_mapping WHERE external_id=%s LIMIT 1", (str(external_id),))

    if not row:
        return None

    return {
        "songId": str(row.get("external_id") or row.get("mapping_id")),
        "name": row.get("song_title") or "未知歌曲",
        "songName": row.get("song_title") or "未知歌曲",
        "album": row.get("album") or "",
        "artist": row.get("artist") or "",
        "artistText": row.get("artist") or "",
        "artists": [row.get("artist") or ""],
        "coverUrl": row.get("cover_url") or "",
        "durationMs": int(row.get("duration_ms") or 0),
        "durationSeconds": int((row.get("duration_ms") or 0) / 1000),
        "source": row.get("platform") or "netease",
    }


def song_from_mongo(song_id=None):
    query_options = []
    if song_id:
        query_options.extend([
            {"song_id": str(song_id)},
            {"songId": str(song_id)},
            {"external_id": str(song_id)},
            {"id": str(song_id)},
        ])
    query_options.append({})

    for query in query_options:
        doc = mongo_one(
            ["media_metadata", "song_info", "songs", "music_metadata", "player_state"],
            query,
            sort=[("updated_at", -1), ("_id", -1)] if not query else None,
        )
        if not doc:
            continue

        artists = doc.get("artists") or doc.get("artist") or doc.get("artistText") or doc.get("artist_text") or ""
        if isinstance(artists, list):
            artist_list = [str(item.get("name") if isinstance(item, dict) else item) for item in artists]
            artist_text = " / ".join([x for x in artist_list if x])
        else:
            artist_text = str(artists)
            artist_list = [artist_text] if artist_text else []

        duration_ms = int(doc.get("duration_ms") or doc.get("durationMs") or 0)

        return {
            "songId": str(doc.get("song_id") or doc.get("songId") or doc.get("external_id") or song_id or ""),
            "name": doc.get("name") or doc.get("song_name") or doc.get("songName") or "未知歌曲",
            "songName": doc.get("song_name") or doc.get("songName") or doc.get("name") or "未知歌曲",
            "album": doc.get("album") or doc.get("album_name") or "",
            "artist": doc.get("artist_text") or artist_text,
            "artistText": doc.get("artist_text") or artist_text,
            "artists": artist_list,
            "coverUrl": doc.get("cover_url") or doc.get("coverUrl") or "",
            "durationMs": duration_ms,
            "durationSeconds": int(duration_ms / 1000) if duration_ms else 0,
            "source": doc.get("platform") or doc.get("source") or "netease",
            "isPlaying": bool(doc.get("is_playing", doc.get("isPlaying", True))),
        }

    return None


def get_song(song_id=None, mapping_id=None):
    song = None
    if song_id:
        song = song_from_mysql(external_id=song_id) or song_from_mongo(song_id)
    elif mapping_id:
        song = song_from_mysql(mapping_id=mapping_id)

    if not song:
        latest = mysql_one(
            """
            SELECT ph.*, mm.song_title, mm.artist, mm.platform, mm.external_id, mm.cover_url
            FROM play_history ph
            LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
            ORDER BY COALESCE(ph.played_at, ph.created_at) DESC
            LIMIT 1
            """
        )
        if latest:
            song = {
                "songId": str(latest.get("external_id") or latest.get("mapping_id") or "song_001"),
                "name": latest.get("song_title") or "【兜底数据】城市夜航",
                "songName": latest.get("song_title") or "【兜底数据】城市夜航",
                "album": "",
                "artist": latest.get("artist") or "",
                "artistText": latest.get("artist") or "",
                "artists": [latest.get("artist") or ""],
                "coverUrl": latest.get("cover_url") or "",
                "durationMs": int(latest.get("play_duration") or 0) * 1000,
                "durationSeconds": int(latest.get("play_duration") or 0),
                "source": latest.get("source_platform") or latest.get("platform") or "netease",
                "isPlaying": True,
            }

    if not song:
        song = fallback_state()["playing"].copy()
        song.setdefault("artistText", song.get("artist", ""))
        song.setdefault("artists", [song.get("artist", "")])
        song.setdefault("durationSeconds", int(song.get("durationMs", 0) / 1000))

    return song


def device_runtime(device_id):
    doc = mongo_one(
        ["device_runtime", "runtime_state", "device_status", "device_metrics"],
        {"device_id": str(device_id)},
        sort=[("updated_at", -1), ("_id", -1)],
    ) or {}

    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else doc
    return metrics or {}


def get_device(device_id=None, user_id=None):
    user_id = int(user_id or current_user_id())
    fallback = fallback_state()["device"]

    if device_id:
        row = mysql_one(
            """
            SELECT
                d.device_id, d.device_number, d.model_name, d.status, d.last_active,
                d.firmware_version, b.custom_device_name, b.is_primary, b.default_room,
                b.current_network, s.volume_limit, s.night_mode_enabled, s.night_start,
                s.night_end, s.auto_firmware_update, s.power_save_enabled,
                n.low_battery_enabled, n.threshold, n.full_charge_notice
            FROM device d
            LEFT JOIN user_device_binding b ON b.device_id=d.device_id
            LEFT JOIN device_settings s ON s.device_id=d.device_id
            LEFT JOIN battery_notice_setting n ON n.device_id=d.device_id
            WHERE CAST(d.device_id AS CHAR)=%s OR d.device_number=%s
            LIMIT 1
            """,
            (str(device_id), str(device_id)),
        )
    else:
        row = mysql_one(
            """
            SELECT
                d.device_id, d.device_number, d.model_name, d.status, d.last_active,
                d.firmware_version, b.custom_device_name, b.is_primary, b.default_room,
                b.current_network, s.volume_limit, s.night_mode_enabled, s.night_start,
                s.night_end, s.auto_firmware_update, s.power_save_enabled,
                n.low_battery_enabled, n.threshold, n.full_charge_notice
            FROM user_device_binding b
            JOIN device d ON d.device_id=b.device_id
            LEFT JOIN device_settings s ON s.device_id=d.device_id
            LEFT JOIN battery_notice_setting n ON n.device_id=d.device_id
            WHERE b.user_id=%s
            ORDER BY b.is_primary DESC, b.bind_time DESC
            LIMIT 1
            """,
            (user_id,),
        )

    if not row:
        return fallback

    runtime = device_runtime(row.get("device_id"))

    def runtime_int(*names, default=0):
        for name in names:
            if runtime.get(name) is not None:
                try:
                    return int(runtime.get(name))
                except Exception:
                    return default
        return default

    return {
        "deviceId": str(row.get("device_id") or fallback["deviceId"]),
        "deviceSn": row.get("device_number") or fallback["deviceSn"],
        "deviceName": row.get("custom_device_name") or fallback["deviceName"],
        "modelName": row.get("model_name") or fallback["modelName"],
        "firmware": row.get("firmware_version") or fallback["firmware"],
        "online": bool(row.get("status")),
        "lastActive": row.get("last_active"),
        "battery": runtime_int("battery", "battery_level", default=fallback["battery"]),
        "volume": runtime_int("volume", default=fallback["volume"]),
        "signalStrength": runtime.get("signal_strength", runtime.get("signalStrength", fallback["signalStrength"])),
        "bassGain": runtime_int("bass_gain", "bassGain", default=fallback["bassGain"]),
        "currentNetwork": row.get("current_network") or runtime.get("current_network") or fallback["currentNetwork"],
        "defaultRoom": row.get("default_room") or fallback["defaultRoom"],
        "volumeLimit": int(row.get("volume_limit") or fallback["volumeLimit"]),
        "nightModeEnabled": bool(row.get("night_mode_enabled", fallback["nightModeEnabled"])),
        "nightStart": str(row.get("night_start") or fallback["nightStart"]),
        "nightEnd": str(row.get("night_end") or fallback["nightEnd"]),
        "autoFirmwareUpdate": bool(row.get("auto_firmware_update", fallback["autoFirmwareUpdate"])),
        "powerSaveEnabled": bool(row.get("power_save_enabled", fallback["powerSaveEnabled"])),
        "lowBatteryEnabled": bool(row.get("low_battery_enabled", fallback["lowBatteryEnabled"])),
        "lowBatteryThreshold": int(row.get("threshold") or fallback["lowBatteryThreshold"]),
        "isCharging": bool(runtime.get("is_charging", runtime.get("isCharging", fallback["isCharging"]))),
        "fullChargeNotice": bool(row.get("full_charge_notice", fallback["fullChargeNotice"])),
        "isConnecting": bool(runtime.get("is_connecting", runtime.get("isConnecting", fallback["isConnecting"]))),
    }


def device_list(user_id=None):
    user_id = int(user_id or current_user_id())
    rows = mysql_all(
        """
        SELECT
            d.device_id,
            d.device_number,
            b.custom_device_name,
            b.is_primary,
            d.model_name,
            d.status,
            d.last_active
        FROM user_device_binding b
        JOIN device d ON d.device_id=b.device_id
        WHERE b.user_id=%s
        ORDER BY b.is_primary DESC, b.bind_time DESC
        """,
        (user_id,),
    )

    if not rows:
        rows = mysql_all(
            """
            SELECT
                d.device_id,
                d.device_number,
                NULL AS custom_device_name,
                1 AS is_primary,
                d.model_name,
                d.status,
                d.last_active
            FROM device d
            ORDER BY d.last_active DESC
            LIMIT 20
            """
        )

    if not rows:
        d = fallback_state()["device"]
        return [
            {
                "device_id": "1",
                "device_number": d["deviceSn"],
                "custom_device_name": d["deviceName"],
                "is_primary": 1,
                "model_name": d["modelName"],
                "status": 1 if d["online"] else 0,
                "last_active": now_str(),
            }
        ]

    return [
        {
            "device_id": str(row.get("device_id")),
            "device_number": row.get("device_number"),
            "custom_device_name": row.get("custom_device_name") or row.get("device_number"),
            "is_primary": int(row.get("is_primary") or 0),
            "model_name": row.get("model_name"),
            "status": int(row.get("status") or 0),
            "last_active": json_safe(row.get("last_active") or now_str()),
        }
        for row in rows
    ]


def history_rows(user_id=None, source=None, keyword=None, limit=50):
    user_id = int(user_id or current_user_id())
    params = [user_id]
    where = ["ph.user_id=%s"]

    if source:
        where.append("COALESCE(ph.source_platform, mm.platform)=%s")
        params.append(source)

    if keyword:
        where.append("(mm.song_title LIKE %s OR mm.artist LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    rows = mysql_all(
        f"""
        SELECT
            ph.history_id,
            ph.played_at,
            ph.created_at,
            COALESCE(ph.source_platform, mm.platform) AS source_platform,
            mm.external_id,
            mm.song_title,
            mm.artist,
            mm.cover_url
        FROM play_history ph
        LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(ph.played_at, ph.created_at) DESC
        LIMIT {int(limit)}
        """,
        tuple(params),
    )

    if not rows:
        docs = mongo_many(
            ["play_logs", "play_history", "history"],
            {},
            sort=[("played_at", -1), ("created_at", -1), ("_id", -1)],
            limit=limit,
        )
        rows = [
            {
                "history_id": doc.get("history_id") or doc.get("event_id") or doc.get("_id"),
                "played_at": doc.get("played_at") or doc.get("created_at"),
                "source_platform": doc.get("platform") or doc.get("source"),
                "external_id": doc.get("song_id") or doc.get("songId") or doc.get("external_id"),
                "song_title": doc.get("song_name") or doc.get("songName") or doc.get("name"),
                "artist": doc.get("artist_text") or doc.get("artist"),
                "cover_url": doc.get("cover_url") or doc.get("coverUrl"),
            }
            for doc in docs
        ]

    if not rows:
        rows = fallback_state()["history"]

    result = []
    for row in rows:
        result.append(
            {
                "historyId": json_safe(row.get("history_id") or row.get("historyId")),
                "songId": str(row.get("external_id") or row.get("songId") or ""),
                "songName": row.get("song_title") or row.get("songName") or "未知歌曲",
                "artist": row.get("artist") or "",
                "source": row.get("source_platform") or row.get("source") or "netease",
                "playedAt": json_safe(row.get("played_at") or row.get("created_at") or row.get("playedAt") or ""),
                "coverUrl": row.get("cover_url") or row.get("coverUrl") or "",
            }
        )

    return result
