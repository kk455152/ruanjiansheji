import json
import os
from datetime import datetime
from decimal import Decimal

from flask import jsonify, request

try:
    from bson import ObjectId
except Exception:
    ObjectId = None

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:
    pymysql = None
    DictCursor = None

try:
    from db import get_mysql_conn as project_mysql_conn
except Exception:
    project_mysql_conn = None

try:
    from db import mongo_db as project_mongo_db
except Exception:
    project_mongo_db = None


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
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


def ok(message, data=None, code=200):
    return jsonify({"code": code, "message": message, "data": json_safe(data)}), code


def plain(data, code=200):
    return jsonify(json_safe(data)), code


def default_state():
    return {
        "tokens": {},
        "device": {
            "deviceId": "dev_001",
            "deviceSn": "SHMINI-A1-0001",
            "deviceName": "客厅音箱",
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
            "songName": "城市夜航",
            "artist": "Luna Echo",
            "source": "netease",
            "isPlaying": True,
            "coverUrl": "https://cdn.musicplayer.cn/song_001.jpg",
            "album": "雨后电台",
            "durationMs": 262060,
        },
        "history": [
            {
                "historyId": 1,
                "songId": "song_001",
                "songName": "城市夜航",
                "artist": "Luna Echo",
                "source": "netease",
                "playedAt": "2026-05-08 22:14",
                "coverUrl": "https://xxx.jpg",
            }
        ],
        "queue": [],
        "music_services": {
            "qq": {
                "service": "qq",
                "serviceName": "QQ 音乐",
                "bound": True,
                "accountName": "用户昵称",
                "syncStatus": "synced",
            },
            "netease": {
                "service": "netease",
                "serviceName": "网易云音乐",
                "bound": True,
                "accountName": "网易云用户",
                "syncStatus": "syncing",
            },
        },
    }


def load_state():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state = default_state()

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
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as file:
        json.dump(json_safe(state), file, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def body_json():
    return request.get_json(silent=True) or {}


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


def get_device(device_id=None):
    fallback = load_state()["device"]

    if device_id:
        row = mysql_one(
            """
            SELECT
                d.device_id, d.device_number, d.model_name,
                COALESCE(d.status, 0) AS status,
                d.last_active,
                b.custom_device_name
            FROM device d
            LEFT JOIN user_device_binding b ON b.device_id=d.device_id
            WHERE CAST(d.device_id AS CHAR)=%s OR d.device_number=%s
            LIMIT 1
            """,
            (str(device_id), str(device_id)),
        )
    else:
        row = mysql_one(
            """
            SELECT
                d.device_id, d.device_number, d.model_name,
                COALESCE(d.status, 0) AS status,
                d.last_active,
                b.custom_device_name
            FROM user_device_binding b
            JOIN device d ON d.device_id=b.device_id
            WHERE b.user_id=%s
            ORDER BY COALESCE(b.is_primary, 1) DESC, d.device_id ASC
            LIMIT 1
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
        doc = (
            mongo_one("media_metadata", {"song_id": str(song_id)})
            or mongo_one("song_info", {"song_id": str(song_id)})
        )

    doc = doc or mongo_one("player_state", {}, sort=[("updated_at", -1), ("_id", -1)]) or {}

    artists = doc.get("artists") or doc.get("artist") or fallback["artist"]
    if isinstance(artists, list):
        artist_list = [str(item.get("name") if isinstance(item, dict) else item) for item in artists]
        artist_text = " / ".join(artist_list)
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
        query["$or"] = [
            {"song_name": {"$regex": keyword, "$options": "i"}},
            {"artist_text": {"$regex": keyword, "$options": "i"}},
        ]

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


def device_list_data():
    rows = mysql_all(
        """
        SELECT
            d.device_id,
            d.device_number,
            b.custom_device_name,
            COALESCE(b.is_primary, 1) AS is_primary,
            d.model_name,
            COALESCE(d.status, 0) AS status,
            d.last_active
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id=d.device_id
        ORDER BY COALESCE(b.is_primary, 0) DESC, d.device_id ASC
        LIMIT 20
        """
    )

    if rows:
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

    d = load_state()["device"]
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
