import argparse
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
        "online_device_count": max(active_devices, int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0)=1", default=0) or 0)),
        "platform_wechat_count": int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE bound_platforms LIKE %s", ("%wechat%",), 0) or 0),
        "platform_qq_count": int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE bound_platforms LIKE %s", ("%qq%",), 0) or 0),
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
    cursor.execute(
        """
        SELECT
            COALESCE(p.province_code, so.province_code, 'unknown') AS region_code,
            COALESCE(p.province_name, so.province_name, 'unknown') AS region_name,
            COUNT(DISTINCT p.user_id) AS user_count,
            COUNT(DISTINCT CASE WHEN p.active_level='high' THEN p.user_id END) AS active_user_count,
            COUNT(DISTINCT b.device_id) AS device_count,
            COUNT(DISTINCT so.order_id) AS order_count,
            COALESCE(SUM(CASE WHEN so.pay_status IN ('paid', 'success', 'finished') THEN so.pay_amount ELSE 0 END), 0) AS sales_amount
        FROM user_profile p
        LEFT JOIN user_device_binding b ON b.user_id = p.user_id
        LEFT JOIN sales_order so ON so.user_id = p.user_id
        GROUP BY COALESCE(p.province_code, so.province_code, 'unknown'),
                 COALESCE(p.province_name, so.province_name, 'unknown')
        """
    )
    rows = cursor.fetchall() or []
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
            COUNT(*) AS play_count
        FROM play_history ph
        LEFT JOIN media_mapping mm ON mm.mapping_id = ph.mapping_id
        WHERE DATE(ph.created_at) = %s
        GROUP BY COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)),
                 COALESCE(mm.song_title, '未知歌曲'),
                 COALESCE(mm.artist, '未知歌手')
        ORDER BY play_count DESC, target_name ASC
        LIMIT 10
        """,
        (stat_date,),
    )
    rows = cursor.fetchall() or []
    if not rows:
        cursor.execute(
            """
            SELECT external_id AS target_id, song_title AS target_name, artist AS target_category, 0 AS play_count
            FROM media_mapping
            ORDER BY mapping_id ASC
            LIMIT 10
            """
        )
        rows = cursor.fetchall() or []
    for index, row in enumerate(rows, start=1):
        cursor.execute(
            """
            INSERT INTO hot_ranking_daily
                (ranking_date, ranking_type, scope_type, scope_code, rank_no, target_id, target_name, target_category, metric_value, metric_unit, created_at)
            VALUES (%s, 'song', 'global', 'global', %s, %s, %s, %s, %s, 'plays', NOW())
            ON DUPLICATE KEY UPDATE
                target_id=VALUES(target_id),
                target_name=VALUES(target_name),
                target_category=VALUES(target_category),
                metric_value=VALUES(metric_value),
                metric_unit=VALUES(metric_unit)
            """,
            (
                stat_date,
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
            CASE COALESCE(value_level, 'normal')
                WHEN 'high' THEN '高价值用户'
                WHEN 'low' THEN '低价值用户'
                ELSE '普通用户'
            END AS segment_name,
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
                LEFT JOIN play_history ph ON ph.user_id=p.user_id
                LEFT JOIN sales_order so ON so.user_id=p.user_id AND so.pay_status IN ('paid', 'success', 'finished')
                WHERE COALESCE(p.value_level, 'normal')=%s
                GROUP BY p.user_id
            ) x
            """,
            (segment_code,),
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
                row.get("segment_name") or segment_code,
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
        ("sales_amount", "销售额", mysql_scalar(cursor, "SELECT COALESCE(SUM(pay_amount),0) AS c FROM sales_order WHERE pay_status IN ('paid','success','finished')", default=0), "yuan"),
        ("active_user_count", "高活用户数", mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE active_level='high'", default=0), "count"),
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


def run_once(args):
    stat_date = parse_stat_date(args.date)
    keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]

    needs_mongo = not args.skip_seed or not args.skip_generate
    if needs_mongo:
        ensure_mongo_schema()
    ensure_daily_stats_table()
    ensure_front_daily_tables()

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


def run_daily_stats_once(date_value=None, generate_count=50, skip_seed=False, skip_generate=False, keywords=None):
    class Args:
        pass

    args = Args()
    args.date = date_value
    args.generate_count = generate_count
    args.skip_seed = skip_seed
    args.skip_generate = skip_generate
    args.keywords = keywords or ",".join(DEFAULT_SONG_KEYWORDS)
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
