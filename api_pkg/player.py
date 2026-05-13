from datetime import datetime

from . import api_bp

def real_conn():
    import os
    import pymysql
    from pymysql.cursors import DictCursor

    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "123456")
    database = os.environ.get("MYSQL_DATABASE", "smart_speaker")
    port = 3306

    hosts = ["172.25.91.167", "172.28.0.1", "127.0.0.1", "8.137.165.220"]

    last_error = None
    for host in hosts:
        try:
            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=False,
                connect_timeout=2,
                read_timeout=3,
                write_timeout=3,
            )
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"MySQL 连接失败，已尝试 {hosts}，最后错误：{last_error}")

from .common import body_json, get_device, get_song, load_state, mongo_update, ok, save_state, mysql_one, mysql_all, mysql_exec, current_user_id




def real_device_id(device_code):
    return 2

def real_user_id():
    return 2

def ensure_mapping(user_id, song_id, song_name, artist, source, cover_url=""):
    conn = real_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT mapping_id
                FROM media_mapping
                WHERE external_id=%s AND platform=%s
                ORDER BY mapping_id DESC
                LIMIT 1
                """,
                (str(song_id), str(source)),
            )
            row = cursor.fetchone()

            if row and row.get("mapping_id") is not None:
                mapping_id = int(row["mapping_id"])
                cursor.execute(
                    """
                    UPDATE media_mapping
                    SET song_title=%s, artist=%s, cover_url=%s
                    WHERE mapping_id=%s
                    """,
                    (song_name, artist or "", cover_url or "", mapping_id),
                )
                conn.commit()
                return mapping_id

            cursor.execute(
                """
                INSERT INTO media_mapping
                (user_id, song_title, artist, platform, external_id, cover_url)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (user_id, song_name, artist or "", source or "netease", str(song_id), cover_url or ""),
            )
            mapping_id = cursor.lastrowid
            conn.commit()

            if not mapping_id:
                raise RuntimeError("media_mapping 插入后没有拿到 mapping_id")

            return int(mapping_id)

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise RuntimeError(f"media_mapping 写入失败：{exc}") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass

@api_bp.post("/player/play-song")
def play_song():
    body = body_json()

    device_code = str(body.get("deviceId") or "dev_001").strip()
    song_id = str(body.get("songId") or "").strip()
    song_name = str(body.get("songName") or body.get("keyword") or "").strip()
    artist = str(body.get("artist") or "").strip()
    source = str(body.get("source") or "netease").strip()
    cover_url = str(body.get("coverUrl") or "")

    if not song_id:
        return ok("歌曲 ID 不能为空", {"field": "songId"}, 400)
    if not song_name:
        song_name = song_id

    try:
        did = real_device_id(device_code)
        uid = real_user_id()
        mapping_id = ensure_mapping(uid, song_id, song_name, artist, source, cover_url)

        conn = real_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO play_history
                    (device_id, user_id, mapping_id, play_duration, created_at, played_at, style, source_platform)
                    VALUES (%s,%s,%s,%s,NOW(),NOW(),%s,%s)
                    """,
                    (did, uid, mapping_id, 0, "normal", source),
                )
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as exc:
        return ok("真实数据库写入失败", {"error": str(exc)}, 500)

    try:
        mongo_update(
            "player_state",
            {"device_id": device_code},
            {
                "$set": {
                    "device_id": device_code,
                    "song_id": song_id,
                    "song_name": song_name,
                    "artist": artist,
                    "source": source,
                    "cover_url": cover_url,
                    "is_playing": True,
                    "updated_at": datetime.now(),
                }
            },
        )
    except Exception:
        pass

    return ok(
        "歌曲播放成功",
        {
            "deviceId": device_code,
            "realDeviceId": did,
            "songId": song_id,
            "songName": song_name,
            "artist": artist,
            "source": source,
            "mappingId": mapping_id,
            "isPlaying": True,
            "playTime": 0,
        },
    )


@api_bp.post("/player/volume")
def player_volume():
    body = body_json()
    try:
        volume = max(0, min(100, int(body.get("volume", 60))))
    except Exception:
        return ok("音量必须是 0-100 的整数", {"field": "volume"}, 400)

    device_id = str(body.get("deviceId") or get_device()["deviceId"])

    try:
        mongo_update(
            "device_runtime",
            {"device_id": device_id},
            {"$set": {"device_id": device_id, "volume": volume, "metrics.volume": volume, "updated_at": datetime.now()}},
        )
    except Exception:
        pass

    return ok("音量设置成功", {"deviceId": device_id, "volume": volume, "isMuted": volume == 0})


@api_bp.post("/player/control")
def player_control():
    body = body_json()
    action = str(body.get("action", "")).strip().lower()

    if action not in ("play", "pause", "previous", "next"):
        return ok("无效的播放控制动作", {"action": action}, 400)

    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song = get_song()
    is_playing = action != "pause"

    try:
        mongo_update(
            "player_state",
            {"device_id": device_id},
            {"$set": {"device_id": device_id, "is_playing": is_playing, "last_action": action, "updated_at": datetime.now()}},
        )
    except Exception:
        pass

    return ok(
        "播放控制成功",
        {
            "deviceId": device_id,
            "action": action,
            "isPlaying": is_playing,
            "currentSong": {"songId": song["songId"], "songName": song["songName"], "artist": song["artist"]},
        },
    )


@api_bp.post("/player/add-next")
def add_next():
    body = body_json()
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or "").strip()

    if not song_id:
        return ok("歌曲 ID 不能为空", {"field": "songId"}, 400)

    song_name = str(body.get("songName") or song_id)
    artist = str(body.get("artist") or "")
    item = {
        "deviceId": device_id,
        "songId": song_id,
        "songName": song_name,
        "artist": artist,
        "queuePosition": 1,
    }

    state = load_state()
    queue = state.setdefault("queue", [])
    if song_id not in [str(x.get("songId")) for x in queue]:
        queue.insert(0, item)
        save_state(state)

    return ok("已加入下一首播放", item)
