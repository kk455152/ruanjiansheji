import os
import hashlib
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.parse import urlparse

import pymysql
from pymongo import MongoClient
from song_info_provider import fetch_song_info

METRIC_TYPES = {
    "signal_strength",
    "volume",
    "bass_gain",
    "is_connected",
    "is_connecting",
}
PREFERENCE_TYPES = {"like_status"}
SONG_INFO_TYPES = {"song_info", "歌曲信息"}

DEFAULT_MONGO_URI = "mongodb://y:123@8.137.165.220:27017/musicplayer?authSource=musicplayer"
DEFAULT_MYSQL_HOST = "8.137.165.220"
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MYSQL_DATABASE = "smart_speaker"
DEFAULT_MYSQL_USER = "team"
DEFAULT_MYSQL_PASSWORD = "123456"

_mongo_client = None
_mongo_client_lock = Lock()
_mysql_connection = None
_mysql_connection_lock = Lock()
_mysql_schema_ready = False


def utcnow():
    return datetime.now(timezone.utc)


def get_mongo_uri():
    return os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)


def get_mongo_database_name():
    database_name = os.environ.get("MONGO_DATABASE")
    if database_name:
        return database_name

    parsed = urlparse(get_mongo_uri())
    if parsed.path and parsed.path != "/":
        return parsed.path.lstrip("/")
    return "musicplayer"


def get_mongo_collection_name():
    return os.environ.get("MONGO_COLLECTION", "device_metrics")


def get_song_collection_name():
    return os.environ.get("MONGO_SONG_COLLECTION", "song_info")


def get_mysql_config():
    return {
        "host": os.environ.get("MYSQL_HOST", DEFAULT_MYSQL_HOST),
        "port": int(os.environ.get("MYSQL_PORT", str(DEFAULT_MYSQL_PORT))),
        "user": os.environ.get("MYSQL_USER", DEFAULT_MYSQL_USER),
        "password": os.environ.get("MYSQL_PASSWORD", DEFAULT_MYSQL_PASSWORD),
        "database": os.environ.get("MYSQL_DATABASE", DEFAULT_MYSQL_DATABASE),
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor,
    }


def get_mongo_collection():
    global _mongo_client
    if _mongo_client is None:
        with _mongo_client_lock:
            if _mongo_client is None:
                _mongo_client = MongoClient(
                    get_mongo_uri(),
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                )
                _mongo_client.admin.command("ping")
    database = _mongo_client[get_mongo_database_name()]
    return database[get_mongo_collection_name()]


def get_song_collection():
    database = get_mongo_collection().database
    return database[get_song_collection_name()]


def get_play_log_collection():
    database = get_mongo_collection().database
    return database[os.environ.get("MONGO_PLAY_LOG_COLLECTION", "play_logs")]


def get_mysql_connection():
    global _mysql_connection
    if _mysql_connection is None or not _mysql_connection.open:
        with _mysql_connection_lock:
            if _mysql_connection is None or not _mysql_connection.open:
                _mysql_connection = pymysql.connect(**get_mysql_config())
    ensure_mysql_schema()
    return _mysql_connection


def ensure_mysql_schema():
    global _mysql_schema_ready
    if _mysql_schema_ready:
        return

    connection = _mysql_connection
    if connection is None or not connection.open:
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                device_id VARCHAR(50) NOT NULL,
                like_status TINYINT NOT NULL DEFAULT '0',
                KEY idx_preferences_user_id (user_id),
                CONSTRAINT fk_user_preferences_user
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                    ON DELETE RESTRICT ON UPDATE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(DAILY_STATS_TABLE_SQL)
        ensure_member_b_relational_schema(cursor)
    _mysql_schema_ready = True


def infer_user_credentials(payload):
    device_id = payload.get("device_id", "unknown_device")
    account = payload.get("user_account") or f"{device_id}_account"
    password = payload.get("user_password") or f"{device_id}_password"
    return account, password


def build_password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def normalize_reported_timestamp(payload):
    raw_value = payload.get("timestamp")
    if raw_value is None:
        return int(datetime.now().timestamp())
    return int(raw_value)


def normalize_metric_type(metric_type):
    if metric_type in SONG_INFO_TYPES:
        return "song_info"
    return metric_type


DAILY_STATS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS Daily_Stats (
    stat_date DATE NOT NULL COMMENT '统计日期',
    total_play_count INT NOT NULL DEFAULT 0 COMMENT '当日总播放次数',
    unique_song_count INT NOT NULL DEFAULT 0 COMMENT '当日播放过的去重歌曲数',
    unique_user_count INT NOT NULL DEFAULT 0 COMMENT '当日活跃用户数',
    unique_device_count INT NOT NULL DEFAULT 0 COMMENT '当日活跃设备数',
    total_play_duration_seconds BIGINT NOT NULL DEFAULT 0 COMMENT '当日累计播放时长，单位秒',
    avg_play_duration_seconds DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '单次平均播放时长，单位秒',
    hottest_song_id VARCHAR(100) DEFAULT NULL COMMENT '当日最热歌曲 ID',
    hottest_song_name VARCHAR(255) DEFAULT NULL COMMENT '当日最热歌曲名',
    hottest_artist VARCHAR(255) DEFAULT NULL COMMENT '当日最热歌曲歌手',
    hottest_play_count INT NOT NULL DEFAULT 0 COMMENT '当日最热歌曲播放次数',
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计生成时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP COMMENT '统计更新时间',
    PRIMARY KEY (stat_date),
    KEY idx_daily_stats_hottest_song_id (hottest_song_id),
    KEY idx_daily_stats_generated_at (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


MEMBER_B_RELATIONAL_SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS action_dict (
        action_id INT NOT NULL,
        action_code VARCHAR(50) NOT NULL,
        action_name VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL,
        PRIMARY KEY (action_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS `user` (
        user_id BIGINT NOT NULL AUTO_INCREMENT,
        username VARCHAR(50) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        phone VARCHAR(20),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS device (
        device_id BIGINT NOT NULL AUTO_INCREMENT,
        device_number VARCHAR(64) NOT NULL,
        model_name VARCHAR(50) NOT NULL,
        status TINYINT NOT NULL,
        last_active DATETIME NOT NULL,
        PRIMARY KEY (device_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_token (
        auth_id BIGINT NOT NULL AUTO_INCREMENT,
        user_id BIGINT,
        platform_type VARCHAR(20) NOT NULL,
        access_token TEXT NOT NULL,
        refresh_token VARCHAR(512) NOT NULL,
        expires_at DATETIME NOT NULL,
        PRIMARY KEY (auth_id),
        CONSTRAINT FK_Reference_13 FOREIGN KEY (user_id)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS media_mapping (
        mapping_id BIGINT NOT NULL AUTO_INCREMENT,
        user_id BIGINT,
        song_title VARCHAR(255) NOT NULL,
        artist VARCHAR(100) NOT NULL,
        platform VARCHAR(20) NOT NULL,
        external_id VARCHAR(100) NOT NULL,
        cover_url VARCHAR(512) NOT NULL,
        PRIMARY KEY (mapping_id),
        CONSTRAINT FK_Reference_14 FOREIGN KEY (user_id)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS play_history (
        history_id BIGINT NOT NULL AUTO_INCREMENT,
        device_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        mapping_id BIGINT,
        play_duration BIGINT,
        created_at DATETIME,
        style VARCHAR(50),
        PRIMARY KEY (history_id),
        CONSTRAINT FK_Reference_16 FOREIGN KEY (user_id)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
        CONSTRAINT FK_Reference_18 FOREIGN KEY (device_id)
            REFERENCES device (device_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
        CONSTRAINT FK_Reference_Music FOREIGN KEY (mapping_id)
            REFERENCES media_mapping (mapping_id) ON DELETE SET NULL ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_device_binding (
        user_id BIGINT NOT NULL,
        device_id BIGINT NOT NULL,
        custom_device_name VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
        is_primary TINYINT NOT NULL,
        PRIMARY KEY (user_id, device_id),
        CONSTRAINT FK_Reference_8 FOREIGN KEY (device_id)
            REFERENCES device (device_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
        CONSTRAINT FK_Reference_9 FOREIGN KEY (user_id)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_feedback (
        content TEXT NOT NULL,
        feedback_id BIGINT NOT NULL AUTO_INCREMENT,
        user_id BIGINT,
        PRIMARY KEY (feedback_id),
        CONSTRAINT FK_Reference_11 FOREIGN KEY (user_id)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS friendship (
        user_id_2 BIGINT NOT NULL,
        user_id_1 BIGINT NOT NULL,
        PRIMARY KEY (user_id_2, user_id_1),
        CONSTRAINT FK_Reference_12 FOREIGN KEY (user_id_1)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
        CONSTRAINT FK_Reference_19 FOREIGN KEY (user_id_2)
            REFERENCES `user` (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

ACTION_DICT_ROWS = [
    (1, "PLAY", "Play song", "music"),
    (2, "LIKE", "Like song", "preference"),
    (3, "DISLIKE", "Dislike song", "preference"),
    (4, "VOLUME_CHANGE", "Volume report", "device"),
    (5, "SIGNAL_REPORT", "Signal report", "device"),
]


def ensure_member_b_relational_schema(cursor):
    for statement in MEMBER_B_RELATIONAL_SCHEMA_SQL:
        cursor.execute(statement)
    cursor.executemany(
        """
        INSERT IGNORE INTO action_dict (action_id, action_code, action_name, category)
        VALUES (%s, %s, %s, %s)
        """,
        ACTION_DICT_ROWS,
    )


def clean_artist_names(artists):
    if not artists:
        return []
    cleaned = []
    for artist in artists:
        if isinstance(artist, str):
            name = artist.strip()
        elif isinstance(artist, dict):
            name = str(artist.get("name") or "").strip()
        else:
            name = str(artist).strip()
        if name:
            cleaned.append(name)
    return cleaned


def normalize_duration_seconds(duration_ms):
    if duration_ms is None:
        return None
    try:
        return max(0, int(round(float(duration_ms) / 1000)))
    except (TypeError, ValueError):
        return None


def build_song_document(song_payload, account=None, password=None, device_id=None, reported_at=None):
    song = song_payload.get("song") or {}
    song_id = str(song.get("song_id") or "").strip()
    name = str(song.get("name") or song_payload.get("keyword") or "").strip()
    artists = clean_artist_names(song.get("artists"))
    now = utcnow()

    document = {
        "doc_type": "song",
        "song_id": song_id,
        "name": name,
        "artists": artists,
        "artist_text": " / ".join(artists),
        "album": str(song.get("album") or "").strip(),
        "duration_ms": song.get("duration_ms"),
        "duration_seconds": normalize_duration_seconds(song.get("duration_ms")),
        "cover_url": str(song.get("cover_url") or "").strip(),
        "source": {
            "platform": "netease",
            "provider": song_payload.get("provider") or "",
            "provider_url": song_payload.get("provider_url") or "",
            "keyword": song_payload.get("keyword") or "",
            "fetched_at": song_payload.get("fetched_at") or now.isoformat(),
        },
        "updated_at": now,
    }

    if reported_at is not None:
        document["reported_timestamp"] = int(reported_at)
    if device_id:
        document["last_device_id"] = device_id
    if account:
        document["user"] = {
            "account": account,
            "password_hash": build_password_hash(password or ""),
        }

    return document


def mysql_now():
    return datetime.now()


def truncate_text(value, limit):
    return str(value or "")[:limit]


def datetime_from_payload_timestamp(payload):
    try:
        return datetime.fromtimestamp(int(payload.get("timestamp")))
    except (TypeError, ValueError, OSError):
        return mysql_now()


def ensure_course_auth_token(cursor, user_id, account):
    token_seed = build_password_hash(f"{account}:netease")
    refresh_seed = build_password_hash(f"{account}:netease:refresh")
    expires_at = mysql_now() + timedelta(days=30)
    cursor.execute(
        """
        SELECT auth_id
        FROM auth_token
        WHERE user_id = %s AND platform_type = %s
        ORDER BY auth_id ASC
        LIMIT 1
        """,
        (user_id, "netease"),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """
            UPDATE auth_token
            SET access_token = %s, refresh_token = %s, expires_at = %s
            WHERE auth_id = %s
            """,
            (token_seed, refresh_seed, expires_at, row["auth_id"]),
        )
        return

    cursor.execute(
        """
        INSERT INTO auth_token (user_id, platform_type, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, "netease", token_seed, refresh_seed, expires_at),
    )


def upsert_course_user(cursor, account, password):
    password_hash = build_password_hash(password)
    cursor.execute(
        """
        SELECT user_id, password_hash
        FROM `user`
        WHERE username = %s
        ORDER BY user_id ASC
        LIMIT 1
        """,
        (account,),
    )
    row = cursor.fetchone()
    if row:
        if row["password_hash"] != password_hash:
            cursor.execute(
                "UPDATE `user` SET password_hash = %s WHERE user_id = %s",
                (password_hash, row["user_id"]),
            )
        user_id = int(row["user_id"])
    else:
        cursor.execute(
            """
            INSERT INTO `user` (username, password_hash)
            VALUES (%s, %s)
            """,
            (account, password_hash),
        )
        user_id = int(cursor.lastrowid)

    ensure_course_auth_token(cursor, user_id, account)
    return user_id


def upsert_course_device(cursor, device_number):
    now = mysql_now()
    cursor.execute(
        """
        SELECT device_id
        FROM device
        WHERE device_number = %s
        ORDER BY device_id ASC
        LIMIT 1
        """,
        (device_number,),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """
            UPDATE device
            SET status = %s, last_active = %s
            WHERE device_id = %s
            """,
            (1, now, row["device_id"]),
        )
        return int(row["device_id"])

    cursor.execute(
        """
        INSERT INTO device (device_number, model_name, status, last_active)
        VALUES (%s, %s, %s, %s)
        """,
        (device_number, "smart-speaker-simulator", 1, now),
    )
    return int(cursor.lastrowid)


def upsert_course_binding(cursor, user_id, device_id, device_number):
    cursor.execute(
        """
        INSERT INTO user_device_binding (user_id, device_id, custom_device_name, is_primary)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            custom_device_name = VALUES(custom_device_name),
            is_primary = VALUES(is_primary)
        """,
        (user_id, device_id, truncate_text(device_number, 50), 1),
    )


def ensure_course_context(payload, account, password):
    connection = get_mysql_connection()
    device_number = str(payload.get("device_id") or "unknown_device")
    with connection.cursor() as cursor:
        user_id = upsert_course_user(cursor, account, password)
        device_id = upsert_course_device(cursor, device_number)
        upsert_course_binding(cursor, user_id, device_id, device_number)
        return user_id, device_id


def upsert_course_media_mapping(cursor, user_id, song_document):
    external_id = truncate_text(song_document.get("song_id"), 100)
    song_title = truncate_text(song_document.get("name"), 255) or "unknown song"
    artist = truncate_text(song_document.get("artist_text"), 100) or "unknown artist"
    cover_url = truncate_text(song_document.get("cover_url"), 512)

    cursor.execute(
        """
        SELECT mapping_id
        FROM media_mapping
        WHERE user_id = %s AND platform = %s AND external_id = %s
        ORDER BY mapping_id ASC
        LIMIT 1
        """,
        (user_id, "netease", external_id),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """
            UPDATE media_mapping
            SET song_title = %s, artist = %s, cover_url = %s
            WHERE mapping_id = %s
            """,
            (song_title, artist, cover_url, row["mapping_id"]),
        )
        return int(row["mapping_id"])

    cursor.execute(
        """
        INSERT INTO media_mapping (user_id, song_title, artist, platform, external_id, cover_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, song_title, artist, "netease", external_id, cover_url),
    )
    return int(cursor.lastrowid)


def insert_course_play_history(cursor, user_id, device_id, mapping_id, play_duration, created_at, style):
    cursor.execute(
        """
        INSERT INTO play_history (device_id, user_id, mapping_id, play_duration, created_at, style)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            device_id,
            user_id,
            mapping_id,
            int(play_duration or 0),
            created_at,
            truncate_text(style, 50),
        ),
    )


def persist_song_document_to_relational(payload, account, password, song_document, style="song_info"):
    connection = get_mysql_connection()
    device_number = str(payload.get("device_id") or "unknown_device")
    with connection.cursor() as cursor:
        user_id = upsert_course_user(cursor, account, password)
        device_id = upsert_course_device(cursor, device_number)
        upsert_course_binding(cursor, user_id, device_id, device_number)
        mapping_id = upsert_course_media_mapping(cursor, user_id, song_document)
        insert_course_play_history(
            cursor,
            user_id,
            device_id,
            mapping_id,
            song_document.get("duration_seconds") or 0,
            datetime_from_payload_timestamp(payload),
            style,
        )
        return {
            "user_id": user_id,
            "device_id": device_id,
            "mapping_id": mapping_id,
        }


def persist_like_feedback_to_relational(payload, account, password):
    connection = get_mysql_connection()
    device_number = str(payload.get("device_id") or "unknown_device")
    like_status = bool(payload.get("value"))
    with connection.cursor() as cursor:
        user_id = upsert_course_user(cursor, account, password)
        device_id = upsert_course_device(cursor, device_number)
        upsert_course_binding(cursor, user_id, device_id, device_number)
        cursor.execute(
            """
            INSERT INTO user_feedback (content, user_id)
            VALUES (%s, %s)
            """,
            (f"like_status={like_status}; device_number={device_number}", user_id),
        )
        return {"user_id": user_id, "device_id": device_id}


def persist_play_log_to_relational(play_log):
    account = play_log.get("user_account") or "daily_stats_user@smart-speaker.local"
    password = play_log.get("user_password") or f"{account}_pwd_2026"
    device_number = str(play_log.get("device_id") or "unknown_device")
    payload = {"device_id": device_number}
    song_document = {
        "song_id": str(play_log.get("song_id") or ""),
        "name": play_log.get("song_name") or "unknown song",
        "artist_text": play_log.get("artist_text") or " / ".join(play_log.get("artists") or []),
        "cover_url": play_log.get("cover_url") or "",
        "duration_seconds": play_log.get("duration_seconds") or play_log.get("play_duration_seconds") or 0,
    }
    played_at = play_log.get("played_at")
    if not isinstance(played_at, datetime):
        played_at = mysql_now()

    connection = get_mysql_connection()
    with connection.cursor() as cursor:
        user_id = upsert_course_user(cursor, account, password)
        device_id = upsert_course_device(cursor, device_number)
        upsert_course_binding(cursor, user_id, device_id, device_number)
        mapping_id = upsert_course_media_mapping(cursor, user_id, song_document)
        insert_course_play_history(
            cursor,
            user_id,
            device_id,
            mapping_id,
            play_log.get("play_duration_seconds") or song_document.get("duration_seconds") or 0,
            played_at.replace(tzinfo=None) if played_at.tzinfo else played_at,
            "daily_stats_job",
        )
    return payload


def get_next_preference_id(cursor):
    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM user_preferences")
    row = cursor.fetchone()
    return int(row["next_id"])


def upsert_user(account, password, device_id):
    connection = get_mysql_connection()
    password_hash = build_password_hash(password)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, password_hash
            FROM users
            WHERE username = %s
            ORDER BY user_id ASC
            LIMIT 1
            """,
            (account,),
        )
        row = cursor.fetchone()
        if row:
            if row["password_hash"] != password_hash:
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (password_hash, row["user_id"]),
                )
            return row["user_id"]

        cursor.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            """,
            (account, password_hash),
        )
        return cursor.lastrowid


def upsert_user_preference(payload, user_id):
    connection = get_mysql_connection()
    with connection.cursor() as cursor:
        device_id = payload.get("device_id", "unknown_device")
        cursor.execute(
            """
            SELECT id
            FROM user_preferences
            WHERE user_id = %s AND device_id = %s
            LIMIT 1
            """,
            (user_id, device_id),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE user_preferences
                SET like_status = %s
                WHERE id = %s
                """,
                (1 if bool(payload.get("value")) else 0, row["id"]),
            )
            return

        next_id = get_next_preference_id(cursor)
        cursor.execute(
            """
            INSERT INTO user_preferences (id, user_id, device_id, like_status)
            VALUES (%s, %s, %s, %s)
            """,
            (
                next_id,
                user_id,
                device_id,
                1 if bool(payload.get("value")) else 0,
            ),
        )


def upsert_device_metric(payload, account, password):
    collection = get_mongo_collection()
    metric_type = normalize_metric_type(payload.get("type"))
    device_id = payload.get("device_id", "unknown_device")
    reported_at = normalize_reported_timestamp(payload)
    now = utcnow()

    update_fields = {
        "device_id": device_id,
        "timestamp": reported_at,
        "updated_at": now,
        f"metrics.{metric_type}": payload.get("value"),
        "user.account": account,
        "user.password_hash": build_password_hash(password),
    }
    if payload.get("api_path"):
        update_fields["last_api_path"] = payload.get("api_path")

    collection.update_one(
        {"device_id": device_id},
        {
            "$set": update_fields,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def upsert_song_info(payload, account, password):
    collection = get_song_collection()
    device_id = payload.get("device_id", "unknown_device")
    reported_at = normalize_reported_timestamp(payload)
    song_payload = payload.get("song_payload") or fetch_song_info(payload.get("value"))
    update_fields = build_song_document(
        song_payload,
        account=account,
        password=password,
        device_id=device_id,
        reported_at=reported_at,
    )
    update_fields["type"] = "song_info"
    update_fields["device_id"] = device_id
    update_fields["timestamp"] = reported_at
    if payload.get("api_path"):
        update_fields["last_api_path"] = payload.get("api_path")

    query = {"song_id": update_fields["song_id"]} if update_fields["song_id"] else {"device_id": device_id}
    collection.update_one(
        query,
        {
            "$set": update_fields,
            "$setOnInsert": {"created_at": utcnow()},
        },
        upsert=True,
    )
    return update_fields


def persist_payload(payload):
    metric_type = normalize_metric_type(payload.get("type"))
    device_id = payload.get("device_id", "unknown_device")
    account, password = infer_user_credentials(payload)
    user_id = upsert_user(account, password, device_id)
    ensure_course_context(payload, account, password)

    if metric_type in PREFERENCE_TYPES:
        upsert_user_preference(payload, user_id)
        persist_like_feedback_to_relational(payload, account, password)
        return "mysql.user_preferences+mysql.user_feedback"

    if metric_type == "song_info":
        song_document = upsert_song_info(payload, account, password)
        persist_song_document_to_relational(payload, account, password, song_document)
        return "mongodb.song_info+mysql.media_mapping+mysql.play_history"

    if metric_type in METRIC_TYPES:
        upsert_device_metric(payload, account, password)
        return "mongodb.device_metrics+mysql.user_device_binding"

    return "mysql.users"


def get_metric_document(device_id):
    return get_mongo_collection().find_one({"device_id": device_id}, {"_id": 0})


def get_song_document(device_id):
    return get_song_collection().find_one({"device_id": device_id}, {"_id": 0})


def get_user_record(account):
    connection = get_mysql_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, username, password_hash FROM users WHERE username = %s ORDER BY user_id ASC LIMIT 1",
            (account,),
        )
        return cursor.fetchone()


def get_user_preference(device_id, account):
    connection = get_mysql_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM users WHERE username = %s ORDER BY user_id ASC LIMIT 1",
            (account,),
        )
        user_row = cursor.fetchone()
        if not user_row:
            return None
        cursor.execute(
            """
            SELECT id, user_id, device_id, like_status
            FROM user_preferences
            WHERE device_id = %s AND user_id = %s
            """,
            (device_id, user_row["user_id"]),
        )
        return cursor.fetchone()
