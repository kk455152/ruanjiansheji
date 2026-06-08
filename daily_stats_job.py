import argparse
import hashlib
import json
import random
import time
import uuid
from datetime import date, datetime, time as datetime_time, timedelta, timezone

import pymysql

from song_info_provider import fetch_song_info
from storage_backends import (
    DAILY_STATS_TABLE_SQL,
    build_song_document,
    get_mongo_database_name,
    get_mysql_config,
    get_song_collection,
    get_play_log_collection,
    persist_play_log_to_relational,
    utcnow,
)


LOCAL_TZ = timezone(timedelta(hours=8))
DEFAULT_SONG_KEYWORDS = ["稻香", "晴天", "夜曲", "青花瓷", "七里香"]
DEFAULT_DEVICES = [f"dev_{index:02d}" for index in range(1, 6)]
DEMO_NAMES = [
    "林小满", "陈一诺", "周明轩", "苏念安", "顾北辰", "许知夏", "沈清欢", "陆星河",
    "赵云舒", "唐若溪", "宋景行", "何雨桐", "韩子墨", "梁诗语", "程予安", "孟晚晴",
    "秦思远", "夏沐橙", "叶青禾", "方以宁", "罗嘉树", "白芷晴", "魏南风", "姜予乐",
    "袁星澜", "邓若楠", "蒋依依", "钟亦辰", "薛听雨", "马知遥", "高云深", "卢清越",
]
DEMO_REGIONS = [
    ("310000", "上海市", "310100", "上海市"),
    ("110000", "北京市", "110100", "北京市"),
    ("440000", "广东省", "440100", "广州市"),
    ("330000", "浙江省", "330100", "杭州市"),
    ("320000", "江苏省", "320100", "南京市"),
    ("510000", "四川省", "510100", "成都市"),
]
DEMO_SONGS = [
    ("demo-daoxiang", "稻香", "周杰伦", "网易云音乐", "华语流行"),
    ("demo-qingtian", "晴天", "周杰伦", "QQ音乐", "华语流行"),
    ("demo-yesong", "夜曲", "周杰伦", "网易云音乐", "R&B"),
    ("demo-qinghuaci", "青花瓷", "周杰伦", "QQ音乐", "中国风"),
    ("demo-pingfan", "平凡之路", "朴树", "网易云音乐", "民谣"),
    ("demo-lantingxu", "兰亭序", "周杰伦", "QQ音乐", "中国风"),
    ("demo-hongdou", "红豆", "王菲", "网易云音乐", "经典流行"),
    ("demo-guanghui", "光辉岁月", "Beyond", "QQ音乐", "摇滚"),
]
DEMO_PLATFORMS = ("网易云音乐", "QQ音乐")
ONLINE_DEVICE_VALUE_SQL = """
CASE
    WHEN LOWER(COALESCE(online_status, '')) IN ('online', 'true', '1', 'yes')
         OR COALESCE(online_status, '') = '在线' THEN 1
    WHEN LOWER(COALESCE(online_status, '')) IN ('offline', 'false', '0', 'no')
         OR COALESCE(online_status, '') = '离线' THEN 0
    ELSE CASE WHEN COALESCE(status, 0) = 1 THEN 1 ELSE 0 END
END
"""
ONLINE_DEVICE_CONDITION = f"({ONLINE_DEVICE_VALUE_SQL}) = 1"


def mysql_connect():
    last_error = None
    for _ in range(3):
        try:
            return pymysql.connect(**get_mysql_config())
        except pymysql.MySQLError as exc:
            last_error = exc
            time.sleep(1)
    raise last_error


def local_now():
    return datetime.now(LOCAL_TZ)


def parse_stat_date(value):
    if value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return local_now().date()


def local_day_range(stat_date):
    start = datetime.combine(stat_date, datetime_time.min, tzinfo=LOCAL_TZ)
    end = start + timedelta(days=1)
    return start, end


def ensure_mongo_schema():
    get_song_collection().create_index("song_id", unique=True, sparse=True)
    get_song_collection().create_index("name")
    get_play_log_collection().create_index("played_at")
    get_play_log_collection().create_index([("song_id", 1), ("played_at", 1)])
    get_play_log_collection().create_index("device_id")
    get_play_log_collection().create_index("user_account")


def ensure_daily_stats_table():
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(DAILY_STATS_TABLE_SQL)
            cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'daily_stats'
                """
            )
            columns = {row["COLUMN_NAME"] for row in cursor.fetchall()}
            if "hottest_song_id" in columns and "hottest_song_external_id" not in columns:
                cursor.execute(
                    "ALTER TABLE daily_stats CHANGE COLUMN hottest_song_id "
                    "hottest_song_external_id VARCHAR(100) NOT NULL DEFAULT ''"
                )
                columns.remove("hottest_song_id")
                columns.add("hottest_song_external_id")
            required_columns = {
                "active_user_count": "INT NOT NULL DEFAULT 0",
                "online_device_count": "INT NOT NULL DEFAULT 0",
                "platform_wechat_count": "INT NOT NULL DEFAULT 0",
                "platform_qq_count": "INT NOT NULL DEFAULT 0",
                "hottest_song_external_id": "VARCHAR(100) NOT NULL DEFAULT ''",
                "hottest_song_name": "VARCHAR(255) NOT NULL DEFAULT ''",
                "hottest_artist": "VARCHAR(255) NOT NULL DEFAULT ''",
                "new_user_count": "INT NOT NULL DEFAULT 0",
                "new_device_count": "INT NOT NULL DEFAULT 0",
                "total_sales_amount": "DECIMAL(12,2) NOT NULL DEFAULT 0.00",
            }
            for column, definition in required_columns.items():
                if column not in columns:
                    cursor.execute(f"ALTER TABLE daily_stats ADD COLUMN {column} {definition}")
    finally:
        connection.close()


def ensure_front_daily_tables():
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS region_stats_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            stat_date DATE NOT NULL,
            region_level VARCHAR(20) NOT NULL,
            region_name VARCHAR(100) NOT NULL,
            user_count INT NOT NULL DEFAULT 0,
            active_user_count INT NOT NULL DEFAULT 0,
            device_count INT NOT NULL DEFAULT 0,
            order_count INT NOT NULL DEFAULT 0,
            sales_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            region_code VARCHAR(20) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_region_stats_daily (stat_date, region_level, region_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS hot_ranking_daily (
            ranking_id BIGINT NOT NULL AUTO_INCREMENT,
            ranking_date DATE NOT NULL,
            ranking_type VARCHAR(50) NOT NULL,
            scope_type VARCHAR(30) NOT NULL,
            scope_code VARCHAR(100) NOT NULL,
            rank_no INT NOT NULL,
            target_id VARCHAR(100),
            target_name VARCHAR(255) NOT NULL,
            target_category VARCHAR(100),
            metric_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            metric_unit VARCHAR(20),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ranking_id),
            UNIQUE KEY uk_hot_ranking_daily (ranking_date, ranking_type, scope_type, scope_code, rank_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS user_value_segment_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            stat_date DATE NOT NULL,
            segment_code VARCHAR(50) NOT NULL,
            segment_name VARCHAR(100) NOT NULL,
            user_count INT NOT NULL DEFAULT 0,
            active_user_count INT NOT NULL DEFAULT 0,
            avg_play_count DECIMAL(10,2),
            avg_pay_amount DECIMAL(12,2),
            retention_rate DECIMAL(10,4),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_user_value_segment_daily (stat_date, segment_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS user_activity_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            stat_date DATE NOT NULL,
            user_id BIGINT NOT NULL,
            play_count INT NOT NULL DEFAULT 0,
            play_duration BIGINT NOT NULL DEFAULT 0,
            active_count INT NOT NULL DEFAULT 0,
            is_active TINYINT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_active_at DATETIME,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_user_activity_daily (stat_date, user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_metric_daily (
            metric_id BIGINT NOT NULL AUTO_INCREMENT,
            metric_date DATE NOT NULL,
            scope_type VARCHAR(30) NOT NULL,
            scope_code VARCHAR(100) NOT NULL,
            metric_code VARCHAR(50) NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            metric_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            metric_unit VARCHAR(20),
            compare_value DECIMAL(18,4),
            growth_rate DECIMAL(10,4),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (metric_id),
            UNIQUE KEY uk_metric_daily_scope (metric_date, scope_type, scope_code, metric_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            for statement in ddl_statements:
                cursor.execute(statement)
    finally:
        connection.close()


def mysql_scalar(cursor, sql, params=(), default=0):
    cursor.execute(sql, params)
    row = cursor.fetchone() or {}
    value = next(iter(row.values()), default)
    return value if value is not None else default


def quote_identifier(name):
    return f"`{str(name).replace('`', '``')}`"


def mysql_table_columns(cursor, table):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table,),
    )
    return {row["COLUMN_NAME"] for row in cursor.fetchall() or []}


def filter_existing_columns(data, columns):
    return {key: value for key, value in data.items() if key in columns}


def upsert_demo_row(cursor, table, data, update_columns):
    columns = mysql_table_columns(cursor, table)
    filtered = filter_existing_columns(data, columns)
    if not filtered:
        return
    names = list(filtered.keys())
    insert_sql = ", ".join(quote_identifier(column) for column in names)
    value_sql = ", ".join(["%s"] * len(names))
    updates = [
        column for column in update_columns
        if column in filtered and column not in {"user_id", "device_id", "mapping_id", "history_id", "order_id"}
    ]
    if updates:
        update_sql = ", ".join(
            f"{quote_identifier(column)}=VALUES({quote_identifier(column)})"
            for column in updates
        )
    else:
        update_sql = f"{quote_identifier(names[0])}={quote_identifier(names[0])}"
    cursor.execute(
        f"INSERT INTO {quote_identifier(table)} ({insert_sql}) VALUES ({value_sql}) "
        f"ON DUPLICATE KEY UPDATE {update_sql}",
        [filtered[column] for column in names],
    )


def demo_password_hash(seed):
    return hashlib.sha256(f"demo:{seed}".encode("utf-8")).hexdigest()


def demo_age_range(age):
    if age < 18:
        return "18-"
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    return "46+"


def day_moment(stat_date, index, total):
    hour = 8 + (index * 11 // max(total, 1)) % 14
    minute = (index * 17) % 60
    second = (index * 23) % 60
    return datetime.combine(stat_date, datetime_time(hour, minute, second))


def select_single_id(cursor, table, id_column, where_column, value):
    cursor.execute(
        f"SELECT {quote_identifier(id_column)} FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(where_column)}=%s ORDER BY {quote_identifier(id_column)} ASC LIMIT 1",
        (value,),
    )
    row = cursor.fetchone()
    return int(row[id_column]) if row else None


def seed_chinese_demo_data(stat_date, user_count=32, device_count=18, order_count=24, play_count=120):
    rng = random.Random(f"demo-{stat_date.isoformat()}-{user_count}-{device_count}-{order_count}-{play_count}")
    user_count = max(1, min(int(user_count or 32), len(DEMO_NAMES)))
    device_count = max(1, int(device_count or 18))
    order_count = max(0, int(order_count or 24))
    play_count = max(0, int(play_count or 120))

    connection = mysql_connect()
    created = {
        "users": 0,
        "profiles": 0,
        "devices": 0,
        "orders": 0,
        "songs": 0,
        "play_history": 0,
    }
    try:
        with connection.cursor() as cursor:
            user_ids = []
            for index, name in enumerate(DEMO_NAMES[:user_count], start=1):
                username = f"{name}{index:03d}"
                phone = f"18{stat_date.strftime('%m%d')}{index:05d}"
                email = f"demo{stat_date.strftime('%m%d')}{index:03d}@smart-speaker.local"
                created_at = day_moment(stat_date, index, user_count)
                upsert_demo_row(
                    cursor,
                    "user",
                    {
                        "username": username,
                        "password_hash": demo_password_hash(username),
                        "phone": phone,
                        "created_at": created_at,
                        "nickname": name,
                        "avatar": "",
                        "email": email,
                        "status": "active",
                        "last_login_at": created_at + timedelta(hours=1),
                        "updated_at": created_at + timedelta(hours=1),
                    },
                    ["password_hash", "phone", "created_at", "nickname", "avatar", "email", "status", "last_login_at", "updated_at"],
                )
                user_id = select_single_id(cursor, "user", "user_id", "username", username)
                if user_id is None:
                    continue
                user_ids.append(user_id)
                region = DEMO_REGIONS[(index - 1) % len(DEMO_REGIONS)]
                age = 18 + (index * 3) % 38
                platform = DEMO_PLATFORMS[(index - 1) % len(DEMO_PLATFORMS)]
                active_level = ["high", "medium", "low"][index % 3]
                value_level = ["high", "normal", "low"][(index + 1) % 3]
                upsert_demo_row(
                    cursor,
                    "user_profile",
                    {
                        "user_id": user_id,
                        "nickname": name,
                        "email": email,
                        "gender": "女" if index % 2 else "男",
                        "age": age,
                        "age_range": demo_age_range(age),
                        "province_code": region[0],
                        "province_name": region[1],
                        "city_code": region[2],
                        "city_name": region[3],
                        "active_level": active_level,
                        "value_level": value_level,
                        "bound_platforms": platform,
                        "user_status": "active",
                        "created_at": created_at,
                        "updated_at": created_at + timedelta(hours=1),
                    },
                    [
                        "nickname", "email", "gender", "age", "age_range", "province_code", "province_name",
                        "city_code", "city_name", "active_level", "value_level", "bound_platforms",
                        "user_status", "created_at", "updated_at",
                    ],
                )
                for auth_platform in platform.split(","):
                    upsert_demo_row(
                        cursor,
                        "auth_token",
                        {
                            "user_id": user_id,
                            "platform_type": auth_platform,
                            "access_token": demo_password_hash(f"{username}:{auth_platform}:access"),
                            "refresh_token": demo_password_hash(f"{username}:{auth_platform}:refresh"),
                            "expires_at": created_at + timedelta(days=30),
                        },
                        ["access_token", "refresh_token", "expires_at"],
                    )
                created["users"] += 1
                created["profiles"] += 1

            device_ids = []
            for index in range(1, device_count + 1):
                device_number = f"中文演示音箱-{index:03d}"
                created_at = day_moment(stat_date, index, device_count)
                upsert_demo_row(
                    cursor,
                    "device",
                    {
                        "device_number": device_number,
                        "model_name": "小智音箱 Pro",
                        "status": 1 if index % 5 else 0,
                        "last_active": created_at + timedelta(hours=2),
                        "firmware_version": f"v2.{index % 5}.{index % 9}",
                        "created_at": created_at,
                        "device_name": f"{DEMO_REGIONS[index % len(DEMO_REGIONS)][3]}客厅音箱{index:02d}",
                        "device_type": "speaker",
                        "online_status": "online" if index % 5 else "offline",
                        "ip_address": f"192.168.10.{20 + index}",
                        "hardware_version": "HW-CN-2026",
                        "location": DEMO_REGIONS[index % len(DEMO_REGIONS)][3],
                        "updated_at": created_at + timedelta(hours=2),
                    },
                    [
                        "model_name", "status", "last_active", "firmware_version", "created_at",
                        "device_name", "device_type", "online_status", "ip_address", "hardware_version",
                        "location", "updated_at",
                    ],
                )
                device_id = select_single_id(cursor, "device", "device_id", "device_number", device_number)
                if device_id is not None:
                    device_ids.append(device_id)
                created["devices"] += 1

            for index, user_id in enumerate(user_ids):
                if not device_ids:
                    break
                device_id = device_ids[index % len(device_ids)]
                bind_time = day_moment(stat_date, index + 1, max(len(user_ids), 1))
                upsert_demo_row(
                    cursor,
                    "user_device_binding",
                    {
                        "user_id": user_id,
                        "device_id": device_id,
                        "custom_device_name": f"{DEMO_NAMES[index]}的智能音箱",
                        "is_primary": 1,
                        "default_room": ["客厅", "卧室", "书房", "厨房"][index % 4],
                        "current_network": f"家庭WiFi-{index % 6 + 1}",
                        "bind_time": bind_time,
                    },
                    ["custom_device_name", "is_primary", "default_room", "current_network", "bind_time"],
                )

            mapping_ids = []
            for index, song in enumerate(DEMO_SONGS, start=1):
                user_id = user_ids[(index - 1) % len(user_ids)] if user_ids else None
                upsert_demo_row(
                    cursor,
                    "media_mapping",
                    {
                        "user_id": user_id,
                        "song_title": song[1],
                        "artist": song[2],
                        "platform": song[3],
                        "external_id": song[0],
                        "cover_url": f"https://cdn.example.com/demo/{song[0]}.jpg",
                    },
                    ["song_title", "artist", "cover_url"],
                )
                cursor.execute(
                    """
                    SELECT mapping_id
                    FROM media_mapping
                    WHERE user_id <=> %s AND platform=%s AND external_id=%s
                    ORDER BY mapping_id ASC
                    LIMIT 1
                    """,
                    (user_id, song[3], song[0]),
                )
                row = cursor.fetchone()
                if row:
                    mapping_ids.append((int(row["mapping_id"]), song))
                created["songs"] += 1

            for index in range(1, order_count + 1):
                user_id = user_ids[(index - 1) % len(user_ids)] if user_ids else None
                device_id = device_ids[(index - 1) % len(device_ids)] if device_ids else None
                region = DEMO_REGIONS[(index - 1) % len(DEMO_REGIONS)]
                amount = 199 + (index % 6) * 80
                created_at = day_moment(stat_date, index, max(order_count, 1))
                upsert_demo_row(
                    cursor,
                    "sales_order",
                    {
                        "order_no": f"DEMO{stat_date.strftime('%Y%m%d')}{index:04d}",
                        "user_id": user_id,
                        "device_id": device_id,
                        "order_amount": amount,
                        "pay_amount": amount - (20 if index % 5 == 0 else 0),
                        "order_status": "finished",
                        "pay_status": "paid",
                        "province_code": region[0],
                        "province_name": region[1],
                        "city_code": region[2],
                        "city_name": region[3],
                        "paid_at": created_at + timedelta(minutes=8),
                        "created_at": created_at,
                        "updated_at": created_at + timedelta(minutes=8),
                    },
                    [
                        "user_id", "device_id", "order_amount", "pay_amount", "order_status", "pay_status",
                        "province_code", "province_name", "city_code", "city_name", "paid_at", "created_at", "updated_at",
                    ],
                )
                created["orders"] += 1

            play_columns = mysql_table_columns(cursor, "play_history")
            for index in range(1, play_count + 1):
                if not user_ids or not device_ids or not mapping_ids:
                    break
                mapping_id, song = rng.choice(mapping_ids)
                play_data = {
                    "device_id": rng.choice(device_ids),
                    "user_id": rng.choice(user_ids),
                    "mapping_id": mapping_id,
                    "play_duration": rng.randint(40, 260),
                    "created_at": day_moment(stat_date, index, max(play_count, 1)),
                    "style": song[4],
                    "source_platform": song[3],
                }
                filtered = filter_existing_columns(play_data, play_columns)
                names = list(filtered.keys())
                cursor.execute(
                    f"INSERT INTO play_history ({', '.join(quote_identifier(column) for column in names)}) "
                    f"VALUES ({', '.join(['%s'] * len(names))})",
                    [filtered[column] for column in names],
                )
                created["play_history"] += 1

        return created
    finally:
        connection.close()


def enrich_daily_stats_from_mysql(cursor, stat_date, stats):
    total_users = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM `user`", default=0) or 0)
    new_users = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM `user` WHERE DATE(created_at)=%s", (stat_date,), 0) or 0)
    total_devices = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device", default=0) or 0)
    new_devices = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device WHERE DATE(created_at)=%s", (stat_date,), 0) or 0)
    sales = mysql_scalar(
        cursor,
        """
        SELECT COALESCE(SUM(pay_amount), 0) AS c
        FROM sales_order
        WHERE pay_status IN ('paid', 'success', 'finished') AND DATE(created_at)=%s
        """,
        (stat_date,),
        0,
    )
    active_users = int(mysql_scalar(
        cursor,
        "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at)=%s",
        (stat_date,),
        0,
    ) or 0)
    active_devices = int(mysql_scalar(
        cursor,
        "SELECT COUNT(DISTINCT device_id) AS c FROM play_history WHERE DATE(created_at)=%s",
        (stat_date,),
        0,
    ) or 0)
    return {
        **stats,
        "unique_user_count": max(int(stats.get("unique_user_count") or 0), active_users),
        "active_user_count": max(int(stats.get("unique_user_count") or 0), active_users),
        "unique_device_count": max(int(stats.get("unique_device_count") or 0), active_devices),
        "online_device_count": max(active_devices, int(mysql_scalar(cursor, f"SELECT COUNT(*) AS c FROM device WHERE {ONLINE_DEVICE_CONDITION}", default=0) or 0)),
        "platform_wechat_count": int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE bound_platforms LIKE %s OR LOWER(bound_platforms) LIKE %s", ("%网易云%", "%netease%"), 0) or 0),
        "platform_qq_count": int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE bound_platforms LIKE %s OR bound_platforms LIKE %s", ("%qq%", "%QQ音乐%"), 0) or 0),
        "new_user_count": new_users,
        "new_device_count": new_devices,
        "total_sales_amount": sales,
        "_total_users": total_users,
        "_total_devices": total_devices,
    }


def seed_song_catalog(keywords):
    collection = get_song_collection()
    saved = []
    for keyword in keywords:
        payload = fetch_song_info(keyword)
        document = build_song_document(payload)
        if not document["song_id"]:
            raise ValueError(f"Song provider returned empty song_id for keyword: {keyword}")

        collection.update_one(
            {"song_id": document["song_id"]},
            {
                "$set": document,
                "$setOnInsert": {"created_at": utcnow()},
            },
            upsert=True,
        )
        saved.append(document)
    return saved


def load_song_catalog():
    return list(
        get_song_collection()
        .find({"doc_type": "song", "song_id": {"$ne": ""}}, {"_id": 0})
        .sort("updated_at", -1)
    )


def build_play_log(song, stat_date, index):
    start, _ = local_day_range(stat_date)
    played_at = start + timedelta(
        seconds=random.randint(0, 24 * 60 * 60 - 1),
        milliseconds=random.randint(0, 999),
    )
    duration_seconds = song.get("duration_seconds") or random.randint(160, 260)
    device_id = random.choice(DEFAULT_DEVICES)
    user_number = random.randint(1, 8)

    return {
        "event_id": str(uuid.uuid4()),
        "source": "daily_stats_job",
        "song_id": song["song_id"],
        "song_name": song["name"],
        "artists": song.get("artists") or [],
        "artist_text": song.get("artist_text") or " / ".join(song.get("artists") or []),
        "album": song.get("album") or "",
        "cover_url": song.get("cover_url") or "",
        "duration_seconds": duration_seconds,
        "play_duration_seconds": random.randint(30, max(31, int(duration_seconds))),
        "device_id": device_id,
        "user_account": f"user_{user_number:02d}@smart-speaker.local",
        "played_at": played_at,
        "stat_date": stat_date.isoformat(),
        "created_at": utcnow(),
        "sequence": index,
    }


def generate_play_logs(stat_date, count):
    songs = load_song_catalog()
    if not songs:
        raise RuntimeError("No song_info documents available. Seed the song catalog first.")

    logs = [build_play_log(random.choice(songs), stat_date, index) for index in range(count)]
    if logs:
        get_play_log_collection().insert_many(logs)
        for log in logs:
            persist_play_log_to_relational(log)
    return logs


def aggregate_from_play_logs(stat_date):
    start, end = local_day_range(stat_date)
    pipeline = [
        {"$match": {"played_at": {"$gte": start, "$lt": end}}},
        {
            "$group": {
                "_id": "$song_id",
                "song_name": {"$first": "$song_name"},
                "artist_text": {"$first": "$artist_text"},
                "play_count": {"$sum": 1},
                "duration_sum": {"$sum": "$play_duration_seconds"},
                "users": {"$addToSet": "$user_account"},
                "devices": {"$addToSet": "$device_id"},
            }
        },
        {"$sort": {"play_count": -1, "duration_sum": -1, "song_name": 1}},
    ]
    rows = list(get_play_log_collection().aggregate(pipeline))

    total_play_count = sum(row["play_count"] for row in rows)
    total_duration = sum(row.get("duration_sum", 0) for row in rows)
    unique_users = set()
    unique_devices = set()
    for row in rows:
        unique_users.update(row.get("users") or [])
        unique_devices.update(row.get("devices") or [])

    hottest = rows[0] if rows else {}
    return {
        "stat_date": stat_date,
        "total_play_count": total_play_count,
        "unique_song_count": len(rows),
        "unique_user_count": len(unique_users),
        "unique_device_count": len(unique_devices),
        "total_play_duration_seconds": total_duration,
        "avg_play_duration_seconds": round(total_duration / total_play_count, 2)
        if total_play_count
        else 0,
        "hottest_song_id": hottest.get("_id"),
        "hottest_song_name": hottest.get("song_name"),
        "hottest_artist": hottest.get("artist_text"),
        "hottest_play_count": hottest.get("play_count", 0),
    }


def upsert_daily_stats(stats):
    sql = """
    INSERT INTO daily_stats (
        stat_date,
        total_play_count,
        unique_song_count,
        unique_user_count,
        active_user_count,
        online_device_count,
        platform_wechat_count,
        platform_qq_count,
        unique_device_count,
        total_play_duration_seconds,
        avg_play_duration_seconds,
        hottest_song_external_id,
        hottest_song_name,
        hottest_artist,
        hottest_play_count,
        new_user_count,
        new_device_count,
        total_sales_amount,
        generated_at,
        updated_at
    ) VALUES (
        %(stat_date)s,
        %(total_play_count)s,
        %(unique_song_count)s,
        %(unique_user_count)s,
        %(active_user_count)s,
        %(online_device_count)s,
        %(platform_wechat_count)s,
        %(platform_qq_count)s,
        %(unique_device_count)s,
        %(total_play_duration_seconds)s,
        %(avg_play_duration_seconds)s,
        %(hottest_song_external_id)s,
        %(hottest_song_name)s,
        %(hottest_artist)s,
        %(hottest_play_count)s,
        %(new_user_count)s,
        %(new_device_count)s,
        %(total_sales_amount)s,
        NOW(),
        NOW()
    )
    ON DUPLICATE KEY UPDATE
        total_play_count = VALUES(total_play_count),
        unique_song_count = VALUES(unique_song_count),
        unique_user_count = VALUES(unique_user_count),
        active_user_count = VALUES(active_user_count),
        online_device_count = VALUES(online_device_count),
        platform_wechat_count = VALUES(platform_wechat_count),
        platform_qq_count = VALUES(platform_qq_count),
        unique_device_count = VALUES(unique_device_count),
        total_play_duration_seconds = VALUES(total_play_duration_seconds),
        avg_play_duration_seconds = VALUES(avg_play_duration_seconds),
        hottest_song_external_id = VALUES(hottest_song_external_id),
        hottest_song_name = VALUES(hottest_song_name),
        hottest_artist = VALUES(hottest_artist),
        hottest_play_count = VALUES(hottest_play_count),
        new_user_count = VALUES(new_user_count),
        new_device_count = VALUES(new_device_count),
        total_sales_amount = VALUES(total_sales_amount),
        updated_at = NOW()
    """
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            stats = enrich_daily_stats_from_mysql(cursor, stats["stat_date"], stats)
            stats = {
                **stats,
                "hottest_song_external_id": stats.get("hottest_song_id") or "",
                "hottest_song_name": stats.get("hottest_song_name") or "",
                "hottest_artist": stats.get("hottest_artist") or "",
            }
            cursor.execute(sql, stats)
    finally:
        connection.close()


def refresh_region_stats(cursor, stat_date):
    regions = {}

    def bucket(row):
        region_code = row.get("region_code") or "unknown"
        if region_code not in regions:
            regions[region_code] = {
                "region_code": region_code,
                "region_name": row.get("region_name") or "unknown",
                "user_count": 0,
                "active_user_count": 0,
                "device_count": 0,
                "order_count": 0,
                "sales_amount": 0,
            }
        return regions[region_code]

    cursor.execute(
        """
        SELECT
            COALESCE(p.province_code, 'unknown') AS region_code,
            COALESCE(p.province_name, p.city_name, 'unknown') AS region_name,
            COUNT(DISTINCT p.user_id) AS user_count,
            COUNT(DISTINCT CASE WHEN p.active_level='high' THEN p.user_id END) AS active_user_count,
            COUNT(DISTINCT b.device_id) AS device_count
        FROM user_profile p
        LEFT JOIN user_device_binding b ON b.user_id = p.user_id
        GROUP BY COALESCE(p.province_code, 'unknown'),
                 COALESCE(p.province_name, p.city_name, 'unknown')
        """
    )
    for row in cursor.fetchall() or []:
        item = bucket(row)
        item["user_count"] = int(row.get("user_count") or 0)
        item["active_user_count"] = int(row.get("active_user_count") or 0)
        item["device_count"] = int(row.get("device_count") or 0)

    cursor.execute(
        """
        SELECT
            COALESCE(province_code, 'unknown') AS region_code,
            COALESCE(province_name, city_name, 'unknown') AS region_name,
            COUNT(*) AS order_count,
            COALESCE(SUM(pay_amount), 0) AS sales_amount
        FROM sales_order
        WHERE pay_status IN ('paid', 'success', 'finished')
          AND DATE(created_at) = %s
        GROUP BY COALESCE(province_code, 'unknown'),
                 COALESCE(province_name, city_name, 'unknown')
        """,
        (stat_date,),
    )
    for row in cursor.fetchall() or []:
        item = bucket(row)
        item["order_count"] = int(row.get("order_count") or 0)
        item["sales_amount"] = row.get("sales_amount") or 0

    rows = list(regions.values())
    if not rows:
        rows = [{
            "region_code": "global",
            "region_name": "全国",
            "user_count": mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM `user`", default=0),
            "active_user_count": mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE active_level='high'", default=0),
            "device_count": mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device", default=0),
            "order_count": mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM sales_order", default=0),
            "sales_amount": mysql_scalar(cursor, "SELECT COALESCE(SUM(pay_amount),0) AS c FROM sales_order WHERE pay_status IN ('paid','success','finished')", default=0),
        }]
    for row in rows:
        cursor.execute(
            """
            INSERT INTO region_stats_daily
                (stat_date, region_level, region_code, region_name, user_count, active_user_count, device_count, order_count, sales_amount, created_at, updated_at)
            VALUES (%s, 'province', %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                region_name=VALUES(region_name),
                user_count=VALUES(user_count),
                active_user_count=VALUES(active_user_count),
                device_count=VALUES(device_count),
                order_count=VALUES(order_count),
                sales_amount=VALUES(sales_amount),
                updated_at=NOW()
            """,
            (
                stat_date,
                row.get("region_code") or "unknown",
                row.get("region_name") or "unknown",
                int(row.get("user_count") or 0),
                int(row.get("active_user_count") or 0),
                int(row.get("device_count") or 0),
                int(row.get("order_count") or 0),
                row.get("sales_amount") or 0,
            ),
        )


def refresh_hot_ranking(cursor, stat_date):
    cursor.execute(
        """
        SELECT
            COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)) AS target_id,
            COALESCE(mm.song_title, '未知歌曲') AS target_name,
            COALESCE(mm.artist, '未知歌手') AS target_category,
            COALESCE(ph.source_platform, mm.platform, '未知平台') AS source_platform,
            COUNT(*) AS play_count
        FROM play_history ph
        LEFT JOIN media_mapping mm ON mm.mapping_id = ph.mapping_id
        WHERE DATE(ph.created_at) = %s
        GROUP BY COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)),
                 COALESCE(mm.song_title, '未知歌曲'),
                 COALESCE(mm.artist, '未知歌手'),
                 COALESCE(ph.source_platform, mm.platform, '未知平台')
        ORDER BY play_count DESC, target_name ASC
        LIMIT 10
        """,
        (stat_date,),
    )
    rows = cursor.fetchall() or []
    if not rows:
        return
    cursor.execute(
        "DELETE FROM hot_ranking_daily WHERE ranking_date=%s AND ranking_type='song'",
        (stat_date,),
    )
    for index, row in enumerate(rows, start=1):
        cursor.execute(
            """
            INSERT INTO hot_ranking_daily
                (ranking_date, ranking_type, scope_type, scope_code, rank_no, target_id, target_name, target_category, metric_value, metric_unit, created_at)
            VALUES (%s, 'song', 'platform', %s, %s, %s, %s, %s, %s, 'plays', NOW())
            ON DUPLICATE KEY UPDATE
                target_id=VALUES(target_id),
                target_name=VALUES(target_name),
                target_category=VALUES(target_category),
                metric_value=VALUES(metric_value),
                metric_unit=VALUES(metric_unit)
            """,
            (
                stat_date,
                row.get("source_platform") or "未知平台",
                index,
                row.get("target_id") or f"song-{index}",
                row.get("target_name") or "未知歌曲",
                row.get("target_category") or "未知歌手",
                row.get("play_count") or 0,
            ),
        )


def refresh_user_activity(cursor, stat_date):
    cursor.execute(
        """
        INSERT INTO user_activity_daily
            (stat_date, user_id, play_count, play_duration, active_count, is_active, created_at, last_active_at, updated_at)
        SELECT
            %s,
            user_id,
            COUNT(*) AS play_count,
            COALESCE(SUM(play_duration), 0) AS play_duration,
            COUNT(*) AS active_count,
            1 AS is_active,
            NOW(),
            MAX(created_at),
            NOW()
        FROM play_history
        WHERE DATE(created_at) = %s AND user_id IS NOT NULL
        GROUP BY user_id
        ON DUPLICATE KEY UPDATE
            play_count=VALUES(play_count),
            play_duration=VALUES(play_duration),
            active_count=VALUES(active_count),
            is_active=VALUES(is_active),
            last_active_at=VALUES(last_active_at),
            updated_at=NOW()
        """,
        (stat_date, stat_date),
    )


def refresh_user_value_segments(cursor, stat_date):
    cursor.execute(
        """
        SELECT
            COALESCE(value_level, 'normal') AS segment_code,
            COUNT(*) AS user_count,
            COUNT(CASE WHEN active_level='high' THEN 1 END) AS active_user_count
        FROM user_profile
        GROUP BY COALESCE(value_level, 'normal')
        """
    )
    rows = cursor.fetchall() or []
    for row in rows:
        segment_code = row.get("segment_code") or "normal"
        cursor.execute(
            """
            SELECT
                COALESCE(AVG(play_count), 0) AS avg_play_count,
                COALESCE(AVG(pay_amount), 0) AS avg_pay_amount
            FROM (
                SELECT p.user_id, COUNT(ph.history_id) AS play_count, COALESCE(SUM(so.pay_amount), 0) AS pay_amount
                FROM user_profile p
                LEFT JOIN play_history ph ON ph.user_id=p.user_id AND DATE(ph.created_at)=%s
                LEFT JOIN sales_order so ON so.user_id=p.user_id
                    AND so.pay_status IN ('paid', 'success', 'finished')
                    AND DATE(so.created_at)=%s
                WHERE COALESCE(p.value_level, 'normal')=%s
                GROUP BY p.user_id
            ) x
            """,
            (stat_date, stat_date, segment_code),
        )
        avg_row = cursor.fetchone() or {}
        user_count = int(row.get("user_count") or 0)
        active_count = int(row.get("active_user_count") or 0)
        cursor.execute(
            """
            INSERT INTO user_value_segment_daily
                (stat_date, segment_code, segment_name, user_count, active_user_count, avg_play_count, avg_pay_amount, retention_rate, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                segment_name=VALUES(segment_name),
                user_count=VALUES(user_count),
                active_user_count=VALUES(active_user_count),
                avg_play_count=VALUES(avg_play_count),
                avg_pay_amount=VALUES(avg_pay_amount),
                retention_rate=VALUES(retention_rate),
                updated_at=NOW()
            """,
            (
                stat_date,
                segment_code,
                {"high": "高价值用户", "low": "低价值用户", "normal": "普通用户"}.get(segment_code, segment_code),
                user_count,
                active_count,
                avg_row.get("avg_play_count") or 0,
                avg_row.get("avg_pay_amount") or 0,
                round(active_count / max(user_count, 1), 4),
            ),
        )


def refresh_analytics_metrics(cursor, stat_date):
    metrics = [
        ("user_count", "用户总数", mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM `user`", default=0), "count"),
        ("device_count", "设备总数", mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device", default=0), "count"),
        ("sales_amount", "销售额", mysql_scalar(cursor, "SELECT COALESCE(SUM(pay_amount),0) AS c FROM sales_order WHERE pay_status IN ('paid','success','finished') AND DATE(created_at)=%s", (stat_date,), 0), "yuan"),
        ("active_user_count", "活跃用户数", mysql_scalar(cursor, "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at)=%s", (stat_date,), 0), "count"),
    ]
    for code, name, value, unit in metrics:
        cursor.execute(
            """
            INSERT INTO analytics_metric_daily
                (metric_date, scope_type, scope_code, metric_code, metric_name, metric_value, metric_unit, created_at, updated_at)
            VALUES (%s, 'global', 'global', %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                metric_name=VALUES(metric_name),
                metric_value=VALUES(metric_value),
                metric_unit=VALUES(metric_unit),
                updated_at=NOW()
            """,
            (stat_date, code, name, value or 0, unit),
        )


def refresh_front_daily_tables(stat_date):
    ensure_front_daily_tables()
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            refresh_region_stats(cursor, stat_date)
            refresh_hot_ranking(cursor, stat_date)
            refresh_user_activity(cursor, stat_date)
            refresh_user_value_segments(cursor, stat_date)
            refresh_analytics_metrics(cursor, stat_date)
    finally:
        connection.close()


def coerce_date_value(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    return None


def date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def missing_daily_stat_dates(target_date):
    end_date = target_date - timedelta(days=1)
    if end_date < date.min:
        return []
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT MAX(stat_date) AS latest_date FROM daily_stats WHERE stat_date < %s",
                (target_date,),
            )
            latest_date = coerce_date_value((cursor.fetchone() or {}).get("latest_date"))
            if not latest_date:
                return []
            start_date = latest_date + timedelta(days=1)
            if start_date > end_date:
                return []
            cursor.execute(
                "SELECT stat_date FROM daily_stats WHERE stat_date BETWEEN %s AND %s",
                (start_date, end_date),
            )
            existing_dates = {
                item
                for item in (coerce_date_value(row.get("stat_date")) for row in cursor.fetchall() or [])
                if item
            }
    finally:
        connection.close()
    return [item for item in date_range(start_date, end_date) if item not in existing_dates]


def refresh_daily_stats_from_mysql(stat_date):
    stats = aggregate_from_mysql_play_history(stat_date)
    upsert_daily_stats(stats)
    refresh_front_daily_tables(stat_date)
    return stats


def backfill_missing_daily_stats(target_date):
    backfilled = []
    for missing_date in missing_daily_stat_dates(target_date):
        stats = refresh_daily_stats_from_mysql(missing_date)
        backfilled.append({
            "stat_date": missing_date.isoformat(),
            "total_play_count": int(stats.get("total_play_count") or 0),
            "unique_user_count": int(stats.get("unique_user_count") or 0),
            "unique_device_count": int(stats.get("unique_device_count") or 0),
        })
    return backfilled


def run_once(args):
    stat_date = parse_stat_date(args.date)
    keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]

    needs_mongo = not args.skip_seed or not args.skip_generate
    if needs_mongo:
        ensure_mongo_schema()
    ensure_daily_stats_table()
    ensure_front_daily_tables()
    backfilled_dates = backfill_missing_daily_stats(stat_date)

    demo_data = {}
    if getattr(args, "generate_demo_data", False):
        demo_play_count = getattr(args, "demo_play_count", None)
        if demo_play_count is None:
            demo_play_count = args.generate_count
        demo_data = seed_chinese_demo_data(
            stat_date,
            user_count=getattr(args, "demo_user_count", 32),
            device_count=getattr(args, "demo_device_count", 18),
            order_count=getattr(args, "demo_order_count", 24),
            play_count=demo_play_count,
        )

    seeded = [] if args.skip_seed else seed_song_catalog(keywords)
    generated_logs = [] if args.skip_generate else generate_play_logs(stat_date, args.generate_count)
    stats = aggregate_from_play_logs(stat_date) if needs_mongo else aggregate_from_mysql_play_history(stat_date)
    upsert_daily_stats(stats)
    refresh_front_daily_tables(stat_date)

    return {
        "ok": True,
        "mongo_database": get_mongo_database_name(),
        "song_collection": "song_info",
        "play_log_collection": "play_logs",
        "daily_stats_table": "daily_stats",
        "stat_date": stat_date.isoformat(),
        "seeded_song_count": len(seeded),
        "generated_play_log_count": len(generated_logs),
        "demo_data": demo_data,
        "backfilled_dates": backfilled_dates,
        "processed_dates": [item["stat_date"] for item in backfilled_dates] + [stat_date.isoformat()],
        "refreshed_daily_tables": [
            "daily_stats",
            "region_stats_daily",
            "hot_ranking_daily",
            "user_activity_daily",
            "user_value_segment_daily",
            "analytics_metric_daily",
        ],
        "stats": {
            **stats,
            "stat_date": stats["stat_date"].isoformat(),
        },
    }


def aggregate_from_mysql_play_history(stat_date):
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), '') AS song_id,
                    COALESCE(mm.song_title, '') AS song_name,
                    COALESCE(mm.artist, '') AS artist_text,
                    COUNT(*) AS play_count,
                    COALESCE(SUM(ph.play_duration), 0) AS duration_sum,
                    COUNT(DISTINCT ph.user_id) AS user_count,
                    COUNT(DISTINCT ph.device_id) AS device_count
                FROM play_history ph
                LEFT JOIN media_mapping mm ON mm.mapping_id = ph.mapping_id
                WHERE DATE(ph.created_at) = %s
                GROUP BY COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), ''),
                         COALESCE(mm.song_title, ''),
                         COALESCE(mm.artist, '')
                ORDER BY play_count DESC, duration_sum DESC, song_name ASC
                """,
                (stat_date,),
            )
            rows = cursor.fetchall() or []
            total_play_count = sum(int(row.get("play_count") or 0) for row in rows)
            total_duration = sum(int(row.get("duration_sum") or 0) for row in rows)
            hottest = rows[0] if rows else {}
            return {
                "stat_date": stat_date,
                "total_play_count": total_play_count,
                "unique_song_count": len(rows),
                "unique_user_count": int(mysql_scalar(
                    cursor,
                    "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at)=%s",
                    (stat_date,),
                    0,
                ) or 0),
                "unique_device_count": int(mysql_scalar(
                    cursor,
                    "SELECT COUNT(DISTINCT device_id) AS c FROM play_history WHERE DATE(created_at)=%s",
                    (stat_date,),
                    0,
                ) or 0),
                "total_play_duration_seconds": total_duration,
                "avg_play_duration_seconds": round(total_duration / total_play_count, 2) if total_play_count else 0,
                "hottest_song_id": hottest.get("song_id"),
                "hottest_song_name": hottest.get("song_name"),
                "hottest_artist": hottest.get("artist_text"),
                "hottest_play_count": int(hottest.get("play_count") or 0),
            }
    finally:
        connection.close()


def run_daily_stats_once(
    date_value=None,
    generate_count=50,
    skip_seed=False,
    skip_generate=False,
    keywords=None,
    generate_demo_data=False,
    demo_user_count=32,
    demo_device_count=18,
    demo_order_count=24,
    demo_play_count=None,
):
    class Args:
        pass

    args = Args()
    args.date = date_value
    args.generate_count = generate_count
    args.skip_seed = skip_seed
    args.skip_generate = skip_generate
    args.keywords = keywords or ",".join(DEFAULT_SONG_KEYWORDS)
    args.generate_demo_data = generate_demo_data
    args.demo_user_count = demo_user_count
    args.demo_device_count = demo_device_count
    args.demo_order_count = demo_order_count
    args.demo_play_count = demo_play_count if demo_play_count is not None else generate_count
    return run_once(args)


def build_parser():
    parser = argparse.ArgumentParser(description="Seed song JSON and build MySQL daily_stats.")
    parser.add_argument("--date", help="Target stat date in YYYY-MM-DD. Defaults to today in UTC+8.")
    parser.add_argument(
        "--keywords",
        default=",".join(DEFAULT_SONG_KEYWORDS),
        help="Comma-separated song keywords used to seed MongoDB song_info.",
    )
    parser.add_argument("--generate-count", type=int, default=50, help="Number of play logs to generate.")
    parser.add_argument("--generate-demo-data", action="store_true", help="Generate Chinese demo MySQL business data before refreshing daily stats.")
    parser.add_argument("--demo-user-count", type=int, default=32, help="Number of Chinese demo users to upsert.")
    parser.add_argument("--demo-device-count", type=int, default=18, help="Number of demo devices to upsert.")
    parser.add_argument("--demo-order-count", type=int, default=24, help="Number of demo paid orders to upsert.")
    parser.add_argument("--demo-play-count", type=int, default=None, help="Number of demo play_history rows to insert.")
    parser.add_argument("--skip-seed", action="store_true", help="Do not fetch and upsert song_info documents.")
    parser.add_argument("--skip-generate", action="store_true", help="Do not generate simulated play logs.")
    parser.add_argument("--once", action="store_true", help="Run once and exit.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=24 * 60 * 60,
        help="Loop interval when --once is not set.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    while True:
        result = run_once(args)
        print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
