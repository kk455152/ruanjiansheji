
import json
from datetime import datetime

from .common import mysql_conn, json_safe, current_user_id


_tables_ready = False


def _conn():
    conn = mysql_conn()
    if conn is None:
        raise RuntimeError("MySQL 连接失败")
    return conn


def _exec(sql, params=()):
    conn = _conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise RuntimeError(f"MySQL 写入失败：{exc}") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return

    _exec("""
    CREATE TABLE IF NOT EXISTS api_player_state (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      device_id VARCHAR(64) NOT NULL,
      song_id VARCHAR(128) DEFAULT NULL,
      song_name VARCHAR(255) DEFAULT NULL,
      artist VARCHAR(255) DEFAULT NULL,
      source VARCHAR(64) DEFAULT NULL,
      is_playing TINYINT(1) NOT NULL DEFAULT 0,
      volume INT DEFAULT NULL,
      last_action VARCHAR(64) DEFAULT NULL,
      updated_at DATETIME NOT NULL,
      UNIQUE KEY uk_api_player_state_device (device_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    _exec("""
    CREATE TABLE IF NOT EXISTS api_device_runtime (
      device_id VARCHAR(64) PRIMARY KEY,
      volume INT DEFAULT NULL,
      updated_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    _exec("""
    CREATE TABLE IF NOT EXISTS api_play_queue (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      device_id VARCHAR(64) NOT NULL,
      song_id VARCHAR(128) NOT NULL,
      song_name VARCHAR(255) DEFAULT NULL,
      artist VARCHAR(255) DEFAULT NULL,
      source VARCHAR(64) DEFAULT NULL,
      queue_position INT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL,
      UNIQUE KEY uk_api_play_queue_device_song (device_id, song_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    _exec("""
    CREATE TABLE IF NOT EXISTS api_play_history (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      user_id BIGINT DEFAULT NULL,
      device_id VARCHAR(64) DEFAULT NULL,
      song_id VARCHAR(128) DEFAULT NULL,
      song_name VARCHAR(255) DEFAULT NULL,
      artist VARCHAR(255) DEFAULT NULL,
      source VARCHAR(64) DEFAULT NULL,
      action VARCHAR(64) DEFAULT NULL,
      payload_json LONGTEXT DEFAULT NULL,
      played_at DATETIME NOT NULL,
      KEY idx_api_play_history_user_time (user_id, played_at),
      KEY idx_api_play_history_device_time (device_id, played_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    _tables_ready = True


def _user_id():
    try:
        return int(current_user_id())
    except Exception:
        return None


def _payload(body):
    try:
        return json.dumps(json_safe(body or {}), ensure_ascii=False)
    except Exception:
        return "{}"


def _s(song, key, default=""):
    value = song.get(key)
    if value is None:
        return default
    return str(value)


def save_player_volume(device_id, volume, body=None):
    _ensure_tables()
    now = datetime.now()

    _exec("""
    INSERT INTO api_device_runtime (device_id, volume, updated_at)
    VALUES (%s,%s,%s)
    ON DUPLICATE KEY UPDATE volume=VALUES(volume), updated_at=VALUES(updated_at)
    """, (str(device_id), int(volume), now))

    _exec("""
    INSERT INTO api_player_state
    (device_id, volume, is_playing, last_action, updated_at)
    VALUES (%s,%s,0,%s,%s)
    ON DUPLICATE KEY UPDATE
      volume=VALUES(volume),
      last_action=VALUES(last_action),
      updated_at=VALUES(updated_at)
    """, (str(device_id), int(volume), "volume", now))


def save_play_song(device_id, song, body=None):
    _ensure_tables()
    now = datetime.now()

    _exec("""
    INSERT INTO api_player_state
    (device_id, song_id, song_name, artist, source, is_playing, last_action, updated_at)
    VALUES (%s,%s,%s,%s,%s,1,%s,%s)
    ON DUPLICATE KEY UPDATE
      song_id=VALUES(song_id),
      song_name=VALUES(song_name),
      artist=VALUES(artist),
      source=VALUES(source),
      is_playing=1,
      last_action=VALUES(last_action),
      updated_at=VALUES(updated_at)
    """, (
        str(device_id),
        _s(song, "songId"),
        _s(song, "songName"),
        _s(song, "artist"),
        _s(song, "source", "netease"),
        "play-song",
        now,
    ))

    _exec("""
    INSERT INTO api_play_history
    (user_id, device_id, song_id, song_name, artist, source, action, payload_json, played_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        _user_id(),
        str(device_id),
        _s(song, "songId"),
        _s(song, "songName"),
        _s(song, "artist"),
        _s(song, "source", "netease"),
        "play-song",
        _payload(body),
        now,
    ))


def save_player_control(device_id, action, song, is_playing, body=None):
    _ensure_tables()
    now = datetime.now()

    _exec("""
    INSERT INTO api_player_state
    (device_id, song_id, song_name, artist, source, is_playing, last_action, updated_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      song_id=VALUES(song_id),
      song_name=VALUES(song_name),
      artist=VALUES(artist),
      source=VALUES(source),
      is_playing=VALUES(is_playing),
      last_action=VALUES(last_action),
      updated_at=VALUES(updated_at)
    """, (
        str(device_id),
        _s(song, "songId"),
        _s(song, "songName"),
        _s(song, "artist"),
        _s(song, "source", "netease"),
        1 if is_playing else 0,
        str(action),
        now,
    ))

    _exec("""
    INSERT INTO api_play_history
    (user_id, device_id, song_id, song_name, artist, source, action, payload_json, played_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        _user_id(),
        str(device_id),
        _s(song, "songId"),
        _s(song, "songName"),
        _s(song, "artist"),
        _s(song, "source", "netease"),
        str(action),
        _payload(body),
        now,
    ))


def save_add_next(device_id, song, song_id, body=None):
    _ensure_tables()
    now = datetime.now()

    _exec("""
    INSERT INTO api_play_queue
    (device_id, song_id, song_name, artist, source, queue_position, created_at)
    VALUES (%s,%s,%s,%s,%s,1,%s)
    ON DUPLICATE KEY UPDATE
      song_name=VALUES(song_name),
      artist=VALUES(artist),
      source=VALUES(source),
      queue_position=VALUES(queue_position),
      created_at=VALUES(created_at)
    """, (
        str(device_id),
        str(song_id),
        _s(song, "songName"),
        _s(song, "artist"),
        _s(song, "source", "netease"),
        now,
    ))
