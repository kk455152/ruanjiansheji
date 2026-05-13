from datetime import datetime, timedelta
import random
import time


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_bigint_id():
    return int(datetime.now().strftime("%y%m%d%H%M%S")) * 1000 + random.randint(100, 999)


def get_mysql_conn_safe():
    from db import get_mysql_conn
    return get_mysql_conn()


def get_mongo_db_safe():
    from db import mongo_db
    return mongo_db


def ensure_demo_user():
    conn = get_mysql_conn_safe()
    try:
        with conn.cursor() as c:
            c.execute("SELECT user_id FROM `user` ORDER BY user_id ASC LIMIT 1")
            row = c.fetchone()
            if row:
                return int(row["user_id"])

            username = "wechat_test_code_all_api"
            c.execute(
                """
                INSERT INTO `user` (username, password_hash, phone, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (username, "demo_hash", None, now_str())
            )
            conn.commit()
            return int(c.lastrowid)
    finally:
        conn.close()


def ensure_demo_device(device_number="dev_001"):
    conn = get_mysql_conn_safe()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT device_id FROM device WHERE device_number=%s ORDER BY device_id ASC LIMIT 1",
                (device_number,)
            )
            row = c.fetchone()
            if row:
                return int(row["device_id"])

            c.execute(
                """
                INSERT INTO device
                (device_number, model_name, status, last_active, firmware_version, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    device_number,
                    "SH-Mini A1",
                    1,
                    now_str(),
                    "v1.0.0",
                    now_str()
                )
            )
            conn.commit()
            return int(c.lastrowid)
    finally:
        conn.close()


def ensure_user_device_binding(user_id, device_id, device_number="dev_001"):
    conn = get_mysql_conn_safe()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT user_id, device_id
                FROM user_device_binding
                WHERE user_id=%s AND device_id=%s
                LIMIT 1
                """,
                (user_id, device_id)
            )
            if c.fetchone():
                return

            c.execute(
                """
                INSERT INTO user_device_binding
                (user_id, device_id, custom_device_name, is_primary, default_room, current_network, bind_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    device_id,
                    device_number,
                    1,
                    None,
                    "Home-5G",
                    now_str()
                )
            )
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def normalize_device_id(device_id):
    if not device_id:
        return "dev_001"
    return str(device_id)


def normalize_source(source):
    return str(source or "netease")


def get_song_brief(song_id):
    song_id = str(song_id or "song_demo_001")
    mongo_db = get_mongo_db_safe()

    for col in ["media_metadata", "song_info", "songs", "music_metadata"]:
        try:
            if col not in mongo_db.list_collection_names():
                continue

            doc = (
                mongo_db[col].find_one({"song_id": song_id})
                or mongo_db[col].find_one({"songId": song_id})
                or mongo_db[col].find_one({"id": song_id})
            )

            if doc:
                return {
                    "songId": song_id,
                    "songName": doc.get("song_name") or doc.get("songName") or doc.get("name") or "测试歌曲",
                    "artist": doc.get("artist") or doc.get("artistText") or "测试歌手",
                    "source": doc.get("source") or doc.get("platform") or "netease",
                    "coverUrl": doc.get("cover_url") or doc.get("coverUrl") or "",
                    "album": doc.get("album") or ""
                }
        except Exception:
            pass

    return {
        "songId": song_id,
        "songName": "测试歌曲",
        "artist": "茶北Ciper",
        "source": "netease",
        "coverUrl": "",
        "album": ""
    }


def write_device_runtime(device_id, volume=None, source="netease", extra=None):
    device_id = normalize_device_id(device_id)
    mongo_db = get_mongo_db_safe()

    doc = {
        "device_id": device_id,
        "source": normalize_source(source),
        "updated_at": datetime.now(),
        "from_api": "/api/player/volume"
    }

    if volume is not None:
        doc["volume"] = int(volume)

    if extra:
        doc.update(extra)

    mongo_db["device_runtime"].update_one(
        {"device_id": device_id},
        {"$set": doc},
        upsert=True
    )

    mongo_db["operation_logs"].insert_one({
        "device_id": device_id,
        "action": "VOLUME_CHANGE",
        "value": doc.get("volume"),
        "source": doc["source"],
        "time": datetime.now(),
        "from_api": "/api/player/volume"
    })

    return doc


def write_player_control(device_id, action, source="netease"):
    device_id = normalize_device_id(device_id)
    action = str(action or "pause")
    source = normalize_source(source)

    is_playing = action in ["play", "next", "previous"]
    mongo_db = get_mongo_db_safe()

    current = mongo_db["player_state"].find_one({"device_id": device_id}) or {}
    current_song = {
        "songId": current.get("song_id") or "song_demo_001",
        "songName": current.get("song_name") or "测试歌曲",
        "artist": current.get("artist") or "测试歌手"
    }

    mongo_db["player_state"].update_one(
        {"device_id": device_id},
        {
            "$set": {
                "device_id": device_id,
                "source": source,
                "is_playing": is_playing,
                "last_action": action,
                "updated_at": datetime.now(),
                "from_api": "/api/player/control"
            }
        },
        upsert=True
    )

    mongo_db["operation_logs"].insert_one({
        "device_id": device_id,
        "action": action.upper(),
        "source": source,
        "time": datetime.now(),
        "from_api": "/api/player/control"
    })

    return current_song, is_playing


def write_play_song(device_id, song_id, source="netease", user_id=None):
    user_id = int(user_id or ensure_demo_user())
    device_id = normalize_device_id(device_id)
    source = normalize_source(source)

    mysql_device_id = ensure_demo_device(device_id)
    ensure_user_device_binding(user_id, mysql_device_id, device_id)

    song = get_song_brief(song_id)
    song_id = song["songId"]

    mongo_db = get_mongo_db_safe()

    player_doc = {
        "device_id": device_id,
        "song_id": song_id,
        "song_name": song["songName"],
        "artist": song["artist"],
        "source": source,
        "is_playing": True,
        "play_time": 0,
        "updated_at": datetime.now(),
        "from_api": "/api/player/play-song"
    }

    mongo_db["player_state"].update_one(
        {"device_id": device_id},
        {"$set": player_doc},
        upsert=True
    )

    mongo_db["play_logs"].insert_one({
        "user_id": user_id,
        "device_id": device_id,
        "song_id": song_id,
        "song_name": song["songName"],
        "artist": song["artist"],
        "platform": source,
        "played_at": datetime.now(),
        "duration": 0,
        "from_api": "/api/player/play-song"
    })

    try:
        conn = get_mysql_conn_safe()
        try:
            with conn.cursor() as c:
                c.execute(
                    """
                    INSERT INTO play_history
                    (history_id, device_id, user_id, mapping_id, play_duration, created_at, played_at, style, source_platform)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        make_bigint_id(),
                        mysql_device_id,
                        user_id,
                        None,
                        0,
                        now_str(),
                        now_str(),
                        "默认",
                        source
                    )
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return {
        "deviceId": device_id,
        "songId": song_id,
        "songName": song["songName"],
        "artist": song["artist"],
        "source": source,
        "isPlaying": True,
        "playTime": 0
    }


def write_add_next(device_id, song_id, source="netease"):
    device_id = normalize_device_id(device_id)
    source = normalize_source(source)
    song = get_song_brief(song_id)

    mongo_db = get_mongo_db_safe()
    queue_doc = mongo_db["play_queue"].find_one({"device_id": device_id}) or {}
    queue = queue_doc.get("queue") or []

    item = {
        "song_id": song["songId"],
        "song_name": song["songName"],
        "artist": song["artist"],
        "source": source,
        "added_at": datetime.now()
    }

    queue.append(item)

    mongo_db["play_queue"].update_one(
        {"device_id": device_id},
        {
            "$set": {
                "device_id": device_id,
                "queue": queue,
                "updated_at": datetime.now(),
                "from_api": "/api/player/add-next"
            }
        },
        upsert=True
    )

    return {
        "deviceId": device_id,
        "songId": song["songId"],
        "songName": song["songName"],
        "artist": song["artist"],
        "queuePosition": len(queue)
    }


def write_share_record(song_id, room_id=None, share_type="link", image_url=None, user_id=None):
    user_id = int(user_id or ensure_demo_user())
    song_id = str(song_id or "song_demo_001")
    share_id = make_bigint_id()
    expire_at = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    share_url = f"https://api.musicplayer.cn/share/{share_id}"

    conn = get_mysql_conn_safe()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO share_record
                (share_id, user_id, song_id, room_id, share_type, share_url, image_url, expire_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    share_id,
                    user_id,
                    song_id,
                    None,
                    share_type,
                    share_url,
                    image_url,
                    expire_at,
                    now_str()
                )
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "shareId": str(share_id),
        "songId": song_id,
        "roomId": room_id,
        "shareUrl": share_url,
        "imageUrl": image_url,
        "expireAt": expire_at
    }
