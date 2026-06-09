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
DEFAULT_DEMO_USER_COUNT = 12
DEFAULT_DEMO_DEVICE_COUNT = 16
DEFAULT_DEMO_ORDER_COUNT = 15
DEFAULT_DEMO_PLAY_COUNT = 900
DEMO_NAMES = [
    "林小满", "陈一诺", "周明轩", "苏念安", "顾北辰", "许知夏", "沈清欢", "陆星河",
    "赵云舒", "唐若溪", "宋景行", "何雨桐", "韩子墨", "梁诗语", "程予安", "孟晚晴",
    "秦思远", "夏沐橙", "叶青禾", "方以宁", "罗嘉树", "白芷晴", "魏南风", "姜予乐",
    "袁星澜", "邓若楠", "蒋依依", "钟亦辰", "薛听雨", "马知遥", "高云深", "卢清越",
]
DEMO_SURNAMES = [
    "林", "陈", "周", "苏", "顾", "许", "沈", "陆", "赵", "唐", "宋", "何",
    "韩", "梁", "程", "孟", "秦", "夏", "叶", "方", "罗", "白", "魏", "姜",
    "袁", "邓", "蒋", "钟", "薛", "马", "高", "卢", "郑", "冯", "曹", "谢",
]
DEMO_GIVEN_NAMES = [
    "清和", "知远", "安宁", "沐阳", "思语", "景行", "若溪", "星河", "云舒", "予安",
    "听澜", "书白", "南风", "嘉树", "初夏", "青禾", "明川", "以宁", "念真", "晚晴",
]
DEMO_NICK_PREFIXES = [
    "晨光", "晚风", "星河", "南山", "海盐", "青柠", "云朵", "月白", "竹影", "晴川",
    "半夏", "橙子", "松间", "微光", "听雨", "蓝调", "清欢", "北岸", "花火", "远山",
]
DEMO_NICK_SUFFIXES = [
    "电台", "小屋", "听歌人", "播放器", "歌单", "音符", "频道", "唱片架", "随身听", "音乐盒",
]
DEMO_NICK_ACTIVITIES = [
    "夜曲收藏家", "晴天歌单", "通勤电台", "睡前频道", "周末播放器", "民谣小屋",
    "摇滚现场", "老歌唱片架", "厨房随身听", "客厅点歌台", "雨天音乐盒", "早安歌单",
]
DEMO_NICK_PERSONAS = [
    "慢歌", "老歌", "民谣", "独立音乐", "粤语歌", "华语歌", "睡前", "通勤",
    "周末", "深夜", "清晨", "厨房", "客厅", "书房", "蓝调", "轻摇滚",
]
DEMO_NICK_NAME_TAILS = [
    "在听歌", "的电台", "的歌单", "点歌台", "随身听", "小唱片", "音乐盒", "耳机里",
    "听歌中", "的晚风", "的清晨", "在路上",
]
DEMO_ROOM_DEVICE_NAMES = {
    "客厅": ("客厅音箱", "客厅播放器", "客厅 Mini", "电视柜音箱", "沙发旁音箱"),
    "卧室": ("卧室音箱", "床头音箱", "主卧播放器", "睡前音箱", "床边 Mini"),
    "书房": ("书房音箱", "桌面播放器", "书桌音箱", "工作台音箱", "阅读角音箱"),
    "厨房": ("厨房音箱", "厨房小音箱", "餐厨播放器", "备餐台音箱", "餐厅音箱"),
    "阳台": ("阳台音箱", "休闲区音箱", "阳台播放器", "花架旁音箱", "露台 Mini"),
    "儿童房": ("儿童房音箱", "故事音箱", "儿童房播放器", "晚安故事机", "玩具柜音箱"),
}
DEMO_REGIONS = [
    ("310000", "上海市", "310100", "上海市"),
    ("110000", "北京市", "110100", "北京市"),
    ("440000", "广东省", "440100", "广州市"),
    ("330000", "浙江省", "330100", "杭州市"),
    ("320000", "江苏省", "320100", "南京市"),
    ("510000", "四川省", "510100", "成都市"),
]
DEMO_REGION_WEIGHTS = (34, 24, 46, 31, 27, 18)
DEMO_DAILY_WEIGHTS = (18, 13, 16, 10, 21, 15, 24, 12, 19, 14, 22, 11, 17, 9)
DEMO_SONG_WEIGHTS = (64, 58, 51, 47, 43, 39, 34, 30, 26, 23, 20, 18, 16, 14, 12, 10)
DEMO_SONGS = [
    ("demo-daoxiang", "稻香", "周杰伦", "网易云音乐", "华语流行"),
    ("demo-qingtian", "晴天", "周杰伦", "QQ音乐", "华语流行"),
    ("demo-yesong", "夜曲", "周杰伦", "网易云音乐", "R&B"),
    ("demo-qinghuaci", "青花瓷", "周杰伦", "QQ音乐", "中国风"),
    ("demo-pingfan", "平凡之路", "朴树", "网易云音乐", "民谣"),
    ("demo-lantingxu", "兰亭序", "周杰伦", "QQ音乐", "中国风"),
    ("demo-hongdou", "红豆", "王菲", "网易云音乐", "经典流行"),
    ("demo-guanghui", "光辉岁月", "Beyond", "QQ音乐", "摇滚"),
    ("demo-haikuotiankong", "海阔天空", "Beyond", "网易云音乐", "摇滚"),
    ("demo-shinian", "十年", "陈奕迅", "QQ音乐", "经典流行"),
    ("demo-fuchoushanxia", "富士山下", "陈奕迅", "网易云音乐", "粤语流行"),
    ("demo-yinyuandecibei", "阴天快乐", "陈奕迅", "QQ音乐", "抒情"),
    ("demo-chengdu", "成都", "赵雷", "网易云音乐", "民谣"),
    ("demo-nanshan-nan", "南山南", "马頔", "QQ音乐", "民谣"),
    ("demo-xiaoqingge", "小情歌", "苏打绿", "网易云音乐", "独立流行"),
    ("demo-wuyuetian", "突然好想你", "五月天", "QQ音乐", "摇滚"),
    ("demo-zhuimeng", "追梦赤子心", "GALA", "网易云音乐", "摇滚"),
    ("demo-zui-chu", "最初的梦想", "范玮琪", "QQ音乐", "励志"),
    ("demo-yueliang", "月亮代表我的心", "邓丽君", "网易云音乐", "经典老歌"),
    ("demo-tianmi", "甜蜜蜜", "邓丽君", "QQ音乐", "经典老歌"),
    ("demo-jiangnan", "江南", "林俊杰", "网易云音乐", "华语流行"),
    ("demo-cao-cao", "曹操", "林俊杰", "QQ音乐", "华语流行"),
    ("demo-qilixiang", "七里香", "周杰伦", "网易云音乐", "华语流行"),
    ("demo-anheqiao", "安和桥", "宋冬野", "QQ音乐", "民谣"),
    ("demo-mojito", "Mojito", "周杰伦", "网易云音乐", "华语流行"),
    ("demo-yanhuayileng", "烟花易冷", "周杰伦", "QQ音乐", "中国风"),
    ("demo-bunengshuodemimi", "不能说的秘密", "周杰伦", "网易云音乐", "影视原声"),
    ("demo-jingru", "听见下雨的声音", "魏如萱", "QQ音乐", "抒情"),
    ("demo-kexi-meiruguo", "可惜没如果", "林俊杰", "网易云音乐", "华语流行"),
    ("demo-beidou", "修炼爱情", "林俊杰", "QQ音乐", "抒情"),
    ("demo-qifengle", "起风了", "买辣椒也用券", "网易云音乐", "流行"),
    ("demo-daoyu", "岛屿心情", "告五人", "QQ音乐", "独立流行"),
    ("demo-aiqingfei", "爱人错过", "告五人", "网易云音乐", "独立流行"),
    ("demo-yuyan", "唯一", "告五人", "QQ音乐", "独立流行"),
    ("demo-shiguang", "时光机", "五月天", "网易云音乐", "摇滚"),
    ("demo-wenrou", "温柔", "五月天", "QQ音乐", "摇滚"),
    ("demo-houtian", "后来的我们", "五月天", "网易云音乐", "摇滚"),
    ("demo-xiaoban", "小半", "陈粒", "QQ音乐", "民谣"),
    ("demo-qimiao", "奇妙能力歌", "陈粒", "网易云音乐", "民谣"),
    ("demo-lvguang", "绿光", "孙燕姿", "QQ音乐", "华语流行"),
    ("demo-yujian", "遇见", "孙燕姿", "网易云音乐", "华语流行"),
    ("demo-tonghua", "童话", "光良", "QQ音乐", "经典流行"),
    ("demo-nazhaxiehua", "那些花儿", "朴树", "网易云音乐", "民谣"),
    ("demo-shengxia", "生如夏花", "朴树", "QQ音乐", "民谣"),
    ("demo-qingge", "旅行的意义", "陈绮贞", "网易云音乐", "民谣"),
    ("demo-haishang", "贝加尔湖畔", "李健", "QQ音乐", "民谣"),
    ("demo-fengchuimai", "风吹麦浪", "李健", "网易云音乐", "民谣"),
    ("demo-chuanqi", "传奇", "王菲", "QQ音乐", "经典流行"),
]
DEMO_PLATFORMS = ("网易云音乐", "QQ音乐")
DEMO_DEVICE_MODELS = ("A1", "A2", "B1")
DEMO_FIRMWARE_VERSIONS = ("v1.0.0", "v1.0.1", "v1.1.0")
DEMO_ROOMS = ("客厅", "卧室", "书房", "厨房", "阳台", "儿童房")
DEMO_NETWORK_PREFIXES = (
    "ChinaNet-5G",
    "CMCC-Home",
    "TP-LINK",
    "MiWiFi-2G",
    "HUAWEI-Home",
    "CU-Home",
    "FAST-Home",
    "MERCURY",
)
DEMO_CLEAR_ROOT_TABLES = (
    "user",
    "device",
    "media_mapping",
    "sales_order",
    "listen_room",
    "user_feedback",
)
DEMO_CLEAR_EXTRA_TABLES = (
    "admin_auth_token",
    "admin_data_scope",
    "admin_login_log",
    "admin_permission",
    "admin_role",
    "admin_role_permission",
    "admin_user_role",
    "daily_stats",
    "data_job_task",
    "region_stats_daily",
    "hot_ranking_daily",
    "user_value_segment_daily",
    "user_activity_daily",
    "analytics_metric_daily",
    "device_firmware",
    "device_firmware_release",
    "device_firmware_release_device",
    "device_firmware_update_task",
    "high_risk_operation",
    "security_event_log",
    "system_backup_task",
    "system_upgrade_package",
    "admin_operation_log",
)
DEMO_MONGO_COLLECTIONS = (
    "device_metrics",
    "device_runtime",
    "player_state",
    "play_queue",
    "operation_logs",
    "media_metadata",
    "song_info",
    "play_logs",
    "user_profiles",
    "music_service_auth",
    "device_bindings",
    "friendships",
    "listen_rooms",
    "listening_summaries",
    "user_feedback",
    "bind_progress",
    "music_sync_progress",
    "device_event_log",
    "play_event_log",
    "voice_command_log",
    "device_status_snapshot",
    "user_behavior_event",
    "listen_room_message",
    "feedback_attachment",
    "third_party_music_raw",
    "device_config_snapshot",
)
DEMO_CLAMP_TIME_COLUMNS = {
    "created_at",
    "updated_at",
    "generated_at",
    "last_login_at",
    "last_active",
    "bind_time",
    "paid_at",
    "handled_at",
    "closed_at",
    "scheduled_at",
    "started_at",
    "finished_at",
    "logged_at",
    "granted_at",
    "assigned_at",
    "applied_at",
}
ONLINE_DEVICE_VALUE_SQL = """
CASE
    WHEN LOWER(TRIM(COALESCE(online_status, ''))) IN ('online', 'true', '1', 'yes')
         OR TRIM(COALESCE(online_status, '')) = '在线' THEN 1
    WHEN LOWER(TRIM(COALESCE(online_status, ''))) IN ('offline', 'false', '0', 'no')
         OR TRIM(COALESCE(online_status, '')) = '离线' THEN 0
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


def clamp_demo_time(value):
    if not isinstance(value, datetime):
        return value
    limit = local_now().replace(tzinfo=None) - timedelta(minutes=2)
    candidate = value.replace(tzinfo=None)
    if candidate > limit:
        return limit
    return value


def filter_existing_columns(data, columns):
    return {
        key: clamp_demo_time(value) if key in DEMO_CLAMP_TIME_COLUMNS else value
        for key, value in data.items()
        if key in columns
    }


def mysql_existing_tables(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        """
    )
    return {row["TABLE_NAME"] for row in cursor.fetchall() or []}


def mysql_auto_increment_tables(cursor, tables):
    if not tables:
        return set()
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN %s
          AND EXTRA LIKE '%%auto_increment%%'
        """,
        (tuple(tables),),
    )
    return {row["TABLE_NAME"] for row in cursor.fetchall() or []}


def mysql_dependent_table_map(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME, REFERENCED_TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_NAME IS NOT NULL
        """
    )
    children_by_parent = {}
    for row in cursor.fetchall() or []:
        children_by_parent.setdefault(row["REFERENCED_TABLE_NAME"], set()).add(row["TABLE_NAME"])
    return children_by_parent


def tables_for_demo_clear(cursor):
    existing = mysql_existing_tables(cursor)
    children_by_parent = mysql_dependent_table_map(cursor)
    roots = {table for table in DEMO_CLEAR_ROOT_TABLES if table in existing}
    clear_tables = set(roots)
    pending = list(roots)
    while pending:
        parent = pending.pop()
        for child in children_by_parent.get(parent, set()):
            if child in existing and child not in clear_tables:
                clear_tables.add(child)
                pending.append(child)
    clear_tables.update(table for table in DEMO_CLEAR_EXTRA_TABLES if table in existing)
    return sorted(clear_tables)


def clear_chinese_demo_data(cursor):
    tables = tables_for_demo_clear(cursor)
    auto_increment_tables = mysql_auto_increment_tables(cursor, tables)
    if not tables:
        return []
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    try:
        for table in tables:
            cursor.execute(f"DELETE FROM {quote_identifier(table)}")
        for table in sorted(auto_increment_tables):
            cursor.execute(f"ALTER TABLE {quote_identifier(table)} AUTO_INCREMENT = 1")
    finally:
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    return tables


def clear_demo_mysql_data():
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            return clear_chinese_demo_data(cursor)
    finally:
        connection.close()


def clear_demo_mongo_data():
    database = get_play_log_collection().database
    counts = {}
    for collection_name in DEMO_MONGO_COLLECTIONS:
        collection = database[collection_name]
        try:
            counts[collection_name] = int(collection.estimated_document_count() or 0)
        except Exception:
            counts[collection_name] = 0
        database.drop_collection(collection_name)
    ensure_mongo_schema()
    return counts


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


def insert_demo_row(cursor, table, data):
    columns = mysql_table_columns(cursor, table)
    filtered = filter_existing_columns(data, columns)
    if not filtered:
        return None
    names = list(filtered.keys())
    cursor.execute(
        f"INSERT INTO {quote_identifier(table)} ({', '.join(quote_identifier(column) for column in names)}) "
        f"VALUES ({', '.join(['%s'] * len(names))})",
        [filtered[column] for column in names],
    )
    return cursor.lastrowid


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


def demo_day_index(stat_date):
    return max((stat_date - date(2026, 1, 1)).days, 0)


def demo_daily_count(base_count, stat_date, minimum=0, salt=0):
    base_count = max(int(base_count or 0), int(minimum or 0))
    if base_count <= 0:
        return 0
    day_index = demo_day_index(stat_date)
    rng = random.Random(f"daily-count:{stat_date.isoformat()}:{salt}:{base_count}")
    weight = DEMO_DAILY_WEIGHTS[(day_index * 3 + int(salt or 0)) % len(DEMO_DAILY_WEIGHTS)]
    average_weight = sum(DEMO_DAILY_WEIGHTS) / len(DEMO_DAILY_WEIGHTS)
    weekday = stat_date.weekday()
    weekday_factor = {
        0: 0.88,
        1: 0.96,
        2: 1.03,
        3: 1.0,
        4: 1.12,
        5: 1.2,
        6: 0.93,
    }.get(weekday, 1.0)
    campaign_factor = 1 + (((day_index + int(salt or 0) * 7) % 9) - 4) * 0.035
    jitter = rng.triangular(0.72, 1.34, 1.0)
    value = base_count * (weight / average_weight) * weekday_factor * campaign_factor * jitter
    value += rng.choice([-2, -1, 0, 1, 2])
    return max(int(minimum or 0), int(round(value)))


def demo_target_count(total, preferred_count, low_ratio, high_ratio, rng):
    if total <= 0:
        return 0
    ratio = rng.uniform(low_ratio, high_ratio)
    jitter = rng.randint(-3, 3)
    return min(total, max(1, int(preferred_count or 0), int(round(total * ratio)) + jitter))


def demo_choice_subset(values, target_count, rng, preferred_values=None):
    values = list(dict.fromkeys(values or []))
    if not values:
        return []
    preferred_values = list(dict.fromkeys(preferred_values or []))
    target_count = min(max(int(target_count or 1), 1), len(values))
    selected = []
    for value in preferred_values:
        if value in values and value not in selected and len(selected) < target_count:
            selected.append(value)
    pool = [value for value in values if value not in selected]
    rng.shuffle(pool)
    selected.extend(pool[:max(target_count - len(selected), 0)])
    rng.shuffle(selected)
    return selected or values[:target_count]


def demo_unique_song_choices(mapping_choices):
    unique = []
    seen = set()
    for mapping_id, song in mapping_choices or []:
        key = song[0] if song else mapping_id
        if key in seen:
            continue
        seen.add(key)
        unique.append((mapping_id, song))
    return unique


def demo_full_name(index, used_names, seed_offset=0):
    position = max(index + seed_offset, 1)
    if position <= len(DEMO_NAMES) and DEMO_NAMES[position - 1] not in used_names:
        return DEMO_NAMES[position - 1]
    surname_count = len(DEMO_SURNAMES)
    given_count = len(DEMO_GIVEN_NAMES)
    base_position = max(position - len(DEMO_NAMES) - 1, 0)
    offset = 0
    while True:
        current = base_position + offset
        surname = DEMO_SURNAMES[(current * 7 + current // 3) % surname_count]
        given = DEMO_GIVEN_NAMES[(current * 11 + current // surname_count) % given_count]
        candidate = f"{surname}{given}"
        if candidate not in used_names:
            return candidate
        offset += 1


def demo_nickname(username, index, rng=None, used_nicknames=None):
    rng = rng or random.Random(f"nickname:{username}:{index}")
    used_nicknames = used_nicknames if used_nicknames is not None else set()
    if username and len(username) >= 2:
        given_name = username[1:]
        surname = username[0]
    else:
        given_name = "听友"
        surname = "音"
    start = rng.randint(0, 997)
    candidates = []
    for offset in range(120):
        cursor = index + start + offset
        prefix = DEMO_NICK_PREFIXES[cursor % len(DEMO_NICK_PREFIXES)]
        suffix = DEMO_NICK_SUFFIXES[(cursor // 2) % len(DEMO_NICK_SUFFIXES)]
        persona = DEMO_NICK_PERSONAS[(cursor // 3) % len(DEMO_NICK_PERSONAS)]
        tail = DEMO_NICK_NAME_TAILS[(cursor // 5) % len(DEMO_NICK_NAME_TAILS)]
        activity = DEMO_NICK_ACTIVITIES[cursor % len(DEMO_NICK_ACTIVITIES)]
        given_tail = given_name[-1:] or "音"
        candidates.extend([
            f"{given_name}{tail}",
            f"{prefix}{suffix}",
            f"{persona}{suffix}",
            f"{given_name}的{suffix}",
            f"{prefix}{given_tail}{suffix}",
            f"{given_name}{persona}{suffix}",
            f"{surname}{prefix}{suffix}",
            activity,
        ])
    for nickname in candidates:
        if nickname and nickname != username and nickname not in used_nicknames:
            used_nicknames.add(nickname)
            return nickname
    for offset in range(500):
        fallback = (
            f"{given_name}"
            f"{DEMO_NICK_PERSONAS[(index + offset) % len(DEMO_NICK_PERSONAS)]}"
            f"{DEMO_NICK_SUFFIXES[(index * 7 + offset) % len(DEMO_NICK_SUFFIXES)]}"
        )
        if fallback != username and fallback not in used_nicknames:
            used_nicknames.add(fallback)
            return fallback
    digest = hashlib.sha1(f"{username}:{index}".encode("utf-8")).hexdigest()[:4]
    fallback = f"{given_name}听歌人{digest}"
    used_nicknames.add(fallback)
    return fallback


def demo_device_model(index):
    return DEMO_DEVICE_MODELS[(index - 1) % len(DEMO_DEVICE_MODELS)]


def demo_firmware_version(index):
    return DEMO_FIRMWARE_VERSIONS[(index - 1) % len(DEMO_FIRMWARE_VERSIONS)]


def demo_device_number(model_name, index):
    compact_model = "".join(char for char in model_name if char.isalnum()).upper()
    return f"SPK-{compact_model}-{index:04d}"


def demo_room_device_name(room, index):
    names = DEMO_ROOM_DEVICE_NAMES.get(room) or (f"{room}音箱",)
    return names[(index - 1) % len(names)]


def demo_network_name(index):
    prefix = DEMO_NETWORK_PREFIXES[(index - 1) % len(DEMO_NETWORK_PREFIXES)]
    digest = hashlib.sha1(f"{prefix}:{index}".encode("utf-8")).hexdigest()[:4].upper()
    return f"{prefix}-{digest}"


def demo_song_choice(rng, mapping_ids):
    if not mapping_ids:
        return None
    weights = [
        DEMO_SONG_WEIGHTS[index] if index < len(DEMO_SONG_WEIGHTS) else max(3, 12 - index // 4)
        for index in range(len(mapping_ids))
    ]
    return rng.choices(mapping_ids, weights=weights, k=1)[0]


def weighted_position(index, total, weights):
    if not weights:
        return 0
    position = ((max(index, 1) - 1) * sum(weights)) // max(int(total or 1), 1)
    running = 0
    for offset, weight in enumerate(weights):
        running += weight
        if position < running:
            return offset
    return len(weights) - 1


def demo_region(index, total):
    return DEMO_REGIONS[weighted_position(index, total, DEMO_REGION_WEIGHTS)]


def demo_span_moment(stat_date, index, total, span_days=1):
    if int(span_days or 1) <= 1:
        return day_moment(stat_date, index, total)
    weights = DEMO_DAILY_WEIGHTS[:span_days]
    day_offset = weighted_position(index, total, weights)
    return day_moment(stat_date - timedelta(days=day_offset), index, total)


def select_firmware_id(cursor, model_name, hardware_version, version_code):
    cursor.execute(
        """
        SELECT firmware_id
        FROM device_firmware
        WHERE model_name=%s AND device_type='speaker' AND hardware_version=%s AND version_code=%s
        ORDER BY firmware_id ASC
        LIMIT 1
        """,
        (model_name, hardware_version, version_code),
    )
    row = cursor.fetchone()
    return int(row["firmware_id"]) if row else None


def select_release_id(cursor, release_no):
    cursor.execute(
        """
        SELECT release_id
        FROM device_firmware_release
        WHERE release_no=%s
        ORDER BY release_id ASC
        LIMIT 1
        """,
        (release_no,),
    )
    row = cursor.fetchone()
    return int(row["release_id"]) if row else None


def count_insert(cursor, table, data):
    return 1 if insert_demo_row(cursor, table, data) is not None else 0


def table_exists(cursor, table):
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table,),
    )
    return int((cursor.fetchone() or {}).get("c") or 0) > 0


def select_id_by_column(cursor, table, id_column, where_column, value):
    if not table_exists(cursor, table):
        return None
    cursor.execute(
        f"SELECT {quote_identifier(id_column)} FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(where_column)}=%s "
        f"ORDER BY {quote_identifier(id_column)} ASC LIMIT 1",
        (value,),
    )
    row = cursor.fetchone() or {}
    return row.get(id_column)


def insert_demo_row_if_missing(cursor, table, where_sql, params, data):
    if not table_exists(cursor, table):
        return 0
    cursor.execute(f"SELECT 1 FROM {quote_identifier(table)} WHERE {where_sql} LIMIT 1", params)
    if cursor.fetchone():
        return 0
    return count_insert(cursor, table, data)


def seed_demo_admin_rows(cursor, stat_date, rng, span_days=1):
    required = {
        "admin_user", "admin_role", "admin_permission", "admin_role_permission",
        "admin_user_role", "admin_data_scope", "admin_auth_token", "admin_login_log",
        "data_job_task", "high_risk_operation", "security_event_log",
        "system_backup_task", "system_upgrade_package",
    }
    if not any(table_exists(cursor, table) for table in required):
        return 0

    moment = lambda index, total: spread_day_moment(stat_date, index, total, span_days)
    rows = 0
    cursor.execute(
        """
        SELECT admin_id, username, role, real_name
        FROM admin_user
        ORDER BY admin_id ASC
        """
    )
    admins = cursor.fetchall() or []
    if not admins:
        return 0

    role_defs = [
        ("super_admin", "超级管理员", "system", "拥有后台全部模块和数据库维护权限"),
        ("market_admin", "市场分析管理员", "business", "负责趋势、地区、画像、热歌和营销洞察"),
        ("operator_admin", "普通管理员", "business", "负责设备、固件、日志和用户反馈处理"),
        ("boss", "老板", "readonly", "只读查看经营看板、日报和核心指标"),
    ]
    for index, (code, name, role_type, description) in enumerate(role_defs, start=1):
        upsert_demo_row(
            cursor,
            "admin_role",
            {
                "role_code": code,
                "role_name": name,
                "role_type": role_type,
                "description": description,
                "status": "active",
                "created_by": None,
                "updated_by": None,
                "created_at": moment(index, len(role_defs)),
                "updated_at": moment(index, len(role_defs)) + timedelta(minutes=8),
            },
            ["role_name", "role_type", "description", "status", "updated_by", "updated_at"],
        )
        rows += 1

    permission_defs = [
        ("overview:view", "查看数据总览", "overview", "数据总览", "menu", "/overview", "/api/admin/super/overview/*"),
        ("trend:view", "查看趋势分析", "trend", "趋势分析", "menu", "/trend", "/api/admin/super/trend/*"),
        ("region:view", "查看区域热力", "region", "区域热力", "menu", "/region", "/api/admin/super/region/*"),
        ("profile:view", "查看用户画像", "profile", "用户画像", "menu", "/profile", "/api/admin/super/user-profile/*"),
        ("segments:view", "查看用户分群", "segments", "用户分群", "menu", "/segments", "/api/admin/market/segments"),
        ("insights:view", "查看营销洞察", "insights", "营销洞察", "menu", "/insights", "/api/admin/market/insights"),
        ("songs:view", "查看热歌排行", "songs", "热歌排行", "menu", "/songs", "/api/admin/market/top-songs"),
        ("feedback:handle", "处理用户反馈", "feedback", "用户反馈", "action", "/feedback", "/api/admin/operator/feedback/handle"),
        ("devices:operate", "维护设备", "devices", "设备管理", "action", "/devices", "/api/admin/operator/device/*"),
        ("firmware:upload", "上传固件包", "firmware", "设备固件", "action", "/firmware", "/api/admin/operator/device/firmware-upload"),
        ("logs:view", "查看设备日志", "logs", "设备日志", "menu", "/logs", "/api/admin/operator/device/logs"),
        ("notices:create", "发布系统公告", "notices", "系统公告", "action", "/notices", "/api/admin/super/notices"),
        ("audit:view", "查看审计日志", "audit", "审计日志", "menu", "/audit", "/api/admin/super/security/logs"),
        ("system:config", "维护系统配置", "system", "系统配置", "action", "/system", "/api/admin/super/system/config"),
        ("db:maintain", "数据库维护", "database", "数据库维护", "action", "/db-admin", "/api/db/*"),
    ]
    for index, item in enumerate(permission_defs, start=1):
        code, name, module_code, module_name, permission_type, route_path, api_path = item
        upsert_demo_row(
            cursor,
            "admin_permission",
            {
                "permission_code": code,
                "permission_name": name,
                "module_code": module_code,
                "module_name": module_name,
                "permission_type": permission_type,
                "parent_id": None,
                "route_path": route_path,
                "api_path": api_path,
                "sort_no": index * 10,
                "status": "active",
                "created_at": moment(index, len(permission_defs)),
                "updated_at": moment(index, len(permission_defs)) + timedelta(minutes=5),
            },
            ["permission_name", "module_code", "module_name", "permission_type", "route_path", "api_path", "sort_no", "status", "updated_at"],
        )
        rows += 1

    role_ids = {
        code: select_id_by_column(cursor, "admin_role", "role_id", "role_code", code)
        for code, *_ in role_defs
    }
    permission_ids = {
        code: select_id_by_column(cursor, "admin_permission", "permission_id", "permission_code", code)
        for code, *_ in permission_defs
    }
    role_permissions = {
        "super_admin": list(permission_ids.keys()),
        "market_admin": ["overview:view", "trend:view", "region:view", "profile:view", "segments:view", "insights:view", "songs:view"],
        "operator_admin": ["overview:view", "feedback:handle", "devices:operate", "firmware:upload", "logs:view"],
        "boss": ["overview:view", "trend:view", "region:view", "profile:view", "segments:view", "insights:view", "songs:view", "audit:view"],
    }
    for role_code, permission_codes in role_permissions.items():
        role_id = role_ids.get(role_code)
        if not role_id:
            continue
        for permission_code in permission_codes:
            permission_id = permission_ids.get(permission_code)
            if not permission_id:
                continue
            rows += insert_demo_row_if_missing(
                cursor,
                "admin_role_permission",
                "role_id=%s AND permission_id=%s",
                (role_id, permission_id),
                {
                    "role_id": role_id,
                    "permission_id": permission_id,
                    "granted_by": None,
                    "granted_at": moment(len(permission_code), 64),
                },
            )

    for index, admin in enumerate(admins, start=1):
        role_code = admin.get("role") or "operator_admin"
        role_id = role_ids.get(role_code)
        if role_id:
            rows += insert_demo_row_if_missing(
                cursor,
                "admin_user_role",
                "admin_id=%s AND role_id=%s",
                (admin["admin_id"], role_id),
                {
                    "admin_id": admin["admin_id"],
                    "role_id": role_id,
                    "assigned_by": None,
                    "assigned_at": moment(index, len(admins)),
                },
            )
            rows += insert_demo_row_if_missing(
                cursor,
                "admin_data_scope",
                "role_id=%s AND scope_type=%s AND scope_code=%s",
                (role_id, "global", "all"),
                {
                    "admin_id": None,
                    "role_id": role_id,
                    "scope_type": "global",
                    "scope_code": "all",
                    "scope_name": "全部数据" if role_code == "super_admin" else "角色授权数据",
                    "can_view": 1,
                    "can_edit": 1 if role_code in {"super_admin", "operator_admin"} else 0,
                    "can_export": 1,
                    "created_at": moment(index, len(admins)),
                    "updated_at": moment(index, len(admins)) + timedelta(minutes=3),
                },
            )
        rows += insert_demo_row_if_missing(
            cursor,
            "admin_auth_token",
            "admin_id=%s AND token_type=%s AND DATE(created_at)=%s",
            (admin["admin_id"], "access", stat_date),
            {
                "admin_id": admin["admin_id"],
                "token": demo_password_hash(f"admin-token:{stat_date}:{admin['admin_id']}"),
                "token_type": "access",
                "login_type": "password",
                "ip_address": f"10.0.2.{20 + index}",
                "user_agent": "Mozilla/5.0 AdminConsole",
                "status": "active",
                "expires_at": moment(index, len(admins)) + timedelta(hours=12),
                "revoked_at": None,
                "created_at": moment(index, len(admins)),
                "updated_at": moment(index, len(admins)) + timedelta(minutes=2),
            },
        )

    login_statuses = ("success", "success", "success", "failed")
    for index in range(1, 25):
        admin = admins[(index - 1) % len(admins)]
        status = login_statuses[(index - 1) % len(login_statuses)]
        rows += insert_demo_row_if_missing(
            cursor,
            "admin_login_log",
            "username=%s AND logged_at=%s",
            (admin["username"], moment(index, 24)),
            {
                "admin_id": admin["admin_id"],
                "username": admin["username"],
                "login_type": "password",
                "ip_address": f"10.0.3.{30 + index}",
                "user_agent": "Mozilla/5.0 AdminConsole",
                "login_status": status,
                "fail_reason": None if status == "success" else "验证码输入错误",
                "logged_at": moment(index, 24),
            },
        )

    job_defs = [
        ("daily_stats", "运营日报汇总", 14, 14, 0, "success", None),
        ("import", "用户画像导入", 240, 236, 4, "finished", "4 行缺少手机号已跳过"),
        ("export", "热歌排行导出", 10, 10, 0, "success", None),
        ("sync", "Mongo 运行态同步", 291, 291, 0, "success", None),
    ]
    for index, (job_type, business_type, total, success, fail, status, reason) in enumerate(job_defs, start=1):
        rows += insert_demo_row_if_missing(
            cursor,
            "data_job_task",
            "job_no=%s",
            (f"JOB{stat_date.strftime('%Y%m%d')}{index:03d}",),
            {
                "job_no": f"JOB{stat_date.strftime('%Y%m%d')}{index:03d}",
                "job_type": job_type,
                "business_type": business_type,
                "file_url": f"https://cdn.example.com/jobs/{stat_date:%Y%m%d}-{index}.csv",
                "total_count": total,
                "success_count": success,
                "fail_count": fail,
                "status": status,
                "fail_reason": reason,
                "admin_id": admins[index % len(admins)]["admin_id"],
                "started_at": moment(index, len(job_defs)),
                "finished_at": moment(index, len(job_defs)) + timedelta(minutes=12),
                "created_at": moment(index, len(job_defs)),
                "updated_at": moment(index, len(job_defs)) + timedelta(minutes=12),
            },
        )

    risk_defs = [
        ("delete", "device", "批量删除离线设备", "high", "approved", "success"),
        ("export", "user_profile", "导出用户画像明细", "medium", "approved", "success"),
        ("firmware", "device_firmware", "全量固件灰度扩大", "high", "pending", "waiting"),
    ]
    for index, (op_type, target_type, message, level, approval, result) in enumerate(risk_defs, start=1):
        rows += insert_demo_row_if_missing(
            cursor,
            "high_risk_operation",
            "operation_no=%s",
            (f"RISK{stat_date.strftime('%Y%m%d')}{index:03d}",),
            {
                "operation_no": f"RISK{stat_date.strftime('%Y%m%d')}{index:03d}",
                "operation_type": op_type,
                "target_type": target_type,
                "target_id": f"{target_type}-{index}",
                "request_params": json.dumps({"message": message}, ensure_ascii=False),
                "risk_level": level,
                "approval_status": approval,
                "requested_by": admins[(index - 1) % len(admins)]["admin_id"],
                "approved_by": admins[0]["admin_id"] if approval == "approved" else None,
                "approved_at": moment(index, len(risk_defs)) + timedelta(minutes=20) if approval == "approved" else None,
                "executed_at": moment(index, len(risk_defs)) + timedelta(minutes=28) if result == "success" else None,
                "result_status": result,
                "result_message": message,
                "created_at": moment(index, len(risk_defs)),
                "updated_at": moment(index, len(risk_defs)) + timedelta(minutes=30),
            },
        )

    security_defs = [
        ("login_failed", "warning", "后台登录失败", "同一 IP 连续输错密码，已触发提醒", "handled"),
        ("api_rate", "info", "接口访问峰值", "数据维护页短时间内连续刷新，系统已记录审计", "handled"),
        ("firmware_task", "warning", "固件任务失败", "部分设备升级任务失败，已进入告警列表", "open"),
        ("db_write", "info", "数据库维护写入", "管理员通过维护页新增数据并刷新日报", "handled"),
    ]
    for index, (event_type, level, title, content, handled) in enumerate(security_defs, start=1):
        rows += insert_demo_row_if_missing(
            cursor,
            "security_event_log",
            "event_type=%s AND title=%s AND DATE(created_at)=%s",
            (event_type, title, stat_date),
            {
                "admin_id": admins[(index - 1) % len(admins)]["admin_id"],
                "event_type": event_type,
                "event_level": level,
                "title": title,
                "content": content,
                "ip_address": f"10.0.4.{40 + index}",
                "user_agent": "Mozilla/5.0 AdminConsole",
                "handled_status": handled,
                "handled_by": admins[0]["admin_id"] if handled == "handled" else None,
                "handled_at": moment(index, len(security_defs)) + timedelta(minutes=18) if handled == "handled" else None,
                "created_at": moment(index, len(security_defs)),
            },
        )

    backup_defs = [
        ("mysql", "smart_speaker", 128_000_000, "success", None),
        ("mongo", "musicplayer", 72_000_000, "success", None),
        ("code", "project", 24_000_000, "success", None),
    ]
    for index, (task_type, scope, size, status, reason) in enumerate(backup_defs, start=1):
        rows += insert_demo_row_if_missing(
            cursor,
            "system_backup_task",
            "task_no=%s",
            (f"BAK{stat_date.strftime('%Y%m%d')}{index:03d}",),
            {
                "task_no": f"BAK{stat_date.strftime('%Y%m%d')}{index:03d}",
                "task_type": task_type,
                "backup_scope": scope,
                "file_url": f"https://backup.example.com/{scope}/{stat_date:%Y%m%d}-{index}.zip",
                "file_size": size,
                "status": status,
                "fail_reason": reason,
                "admin_id": admins[(index - 1) % len(admins)]["admin_id"],
                "started_at": moment(index, len(backup_defs)),
                "finished_at": moment(index, len(backup_defs)) + timedelta(minutes=9),
                "created_at": moment(index, len(backup_defs)),
                "updated_at": moment(index, len(backup_defs)) + timedelta(minutes=9),
            },
        )

    package_defs = [
        ("SYS-PKG-ADMIN-202606", "后台管理前端包", "2026.06.1", "frontend", "active"),
        ("SYS-PKG-API-202606", "后台接口服务包", "2026.06.1", "backend", "active"),
        ("SYS-PKG-JOB-202606", "每日汇总任务包", "2026.06.1", "job", "active"),
    ]
    for index, (package_no, package_name, version, upgrade_type, status) in enumerate(package_defs, start=1):
        upsert_demo_row(
            cursor,
            "system_upgrade_package",
            {
                "package_no": package_no,
                "package_name": package_name,
                "version": version,
                "file_url": f"https://cdn.example.com/system/{package_no}.zip",
                "file_md5": demo_password_hash(package_no)[:32],
                "file_size": 12_000_000 + index * 3_000_000,
                "upgrade_type": upgrade_type,
                "description": f"{package_name}，用于演示系统升级包管理。",
                "status": status,
                "uploaded_by": admins[(index - 1) % len(admins)]["admin_id"],
                "applied_by": admins[0]["admin_id"] if index < 3 else None,
                "applied_at": moment(index, len(package_defs)) + timedelta(minutes=30) if index < 3 else None,
                "created_at": moment(index, len(package_defs)),
                "updated_at": moment(index, len(package_defs)) + timedelta(minutes=30),
            },
            ["package_name", "version", "file_url", "file_md5", "file_size", "upgrade_type", "description", "status", "uploaded_by", "applied_by", "applied_at", "updated_at"],
        )
        rows += 1

    return rows


def seed_demo_support_rows(cursor, stat_date, rng, user_profiles, device_records, mapping_ids, order_records, span_days=1):
    if not user_profiles or not device_records:
        return 0

    moment = lambda index, total: spread_day_moment(stat_date, index, total, span_days)
    rows = seed_demo_admin_rows(cursor, stat_date, rng, span_days)
    firmware_ids = []
    for index, model_name in enumerate(DEMO_DEVICE_MODELS, start=1):
        hardware_version = f"HW-{model_name}"
        version = demo_firmware_version(index)
        version_code = 100 + index
        upsert_demo_row(
            cursor,
            "device_firmware",
            {
                "model_name": model_name,
                "device_type": "speaker",
                "hardware_version": hardware_version,
                "version": version,
                "version_code": version_code,
                "file_url": f"https://cdn.example.com/firmware/{model_name.lower()}-{version}.bin",
                "file_md5": demo_password_hash(f"{model_name}:{version_code}")[:32],
                "file_size": 18_000_000 + index * 350_000,
                "description": f"{model_name} 稳定版固件",
                "force_update": 0,
                "status": "active",
                "created_at": moment(index, len(DEMO_DEVICE_MODELS)),
                "updated_at": moment(index, len(DEMO_DEVICE_MODELS)) + timedelta(hours=1),
            },
            [
                "version", "file_url", "file_md5", "file_size", "description",
                "force_update", "status", "created_at", "updated_at",
            ],
        )
        firmware_id = select_firmware_id(cursor, model_name, hardware_version, version_code)
        if firmware_id is not None:
            firmware_ids.append((firmware_id, model_name, hardware_version, version_code))
            rows += 1

    release_ids = []
    for index, (firmware_id, model_name, hardware_version, _) in enumerate(firmware_ids, start=1):
        release_no = f"REL{stat_date.strftime('%Y%m%d')}{index:02d}"
        upsert_demo_row(
            cursor,
            "device_firmware_release",
            {
                "release_no": release_no,
                "firmware_id": firmware_id,
                "target_model_name": model_name,
                "target_device_type": "speaker",
                "target_hardware_version": hardware_version,
                "release_scope": "gray",
                "total_device_count": 24 + index * 3,
                "success_device_count": 20 + index * 3,
                "fail_device_count": index % 3,
                "status": "running" if index % 3 == 0 else "finished",
                "admin_id": None,
                "operator_name": "系统运营",
                "scheduled_at": moment(index, len(firmware_ids)),
                "started_at": moment(index, len(firmware_ids)) + timedelta(minutes=5),
                "finished_at": moment(index, len(firmware_ids)) + timedelta(hours=2),
                "created_at": moment(index, len(firmware_ids)),
                "updated_at": moment(index, len(firmware_ids)) + timedelta(hours=2),
            },
            [
                "firmware_id", "target_model_name", "target_device_type", "target_hardware_version",
                "release_scope", "total_device_count", "success_device_count", "fail_device_count",
                "status", "admin_id", "operator_name", "scheduled_at", "started_at", "finished_at",
                "created_at", "updated_at",
            ],
        )
        release_id = select_release_id(cursor, release_no)
        if release_id is not None:
            release_ids.append((release_id, firmware_id, model_name))
            rows += 1

    for index, device in enumerate(device_records, start=1):
        rows += count_insert(
            cursor,
            "device_settings",
            {
                "device_id": device["device_id"],
                "volume_limit": 70 + index % 20,
                "night_mode_enabled": 1 if index % 4 == 0 else 0,
                "night_start": "22:30:00",
                "night_end": "07:30:00",
                "auto_firmware_update": 1 if index % 3 else 0,
                "power_save_enabled": 1,
                "updated_at": moment(index, len(device_records)),
            },
        )
        rows += count_insert(
            cursor,
            "battery_notice_setting",
            {
                "device_id": device["device_id"],
                "low_battery_enabled": 1,
                "threshold": 15 + index % 10,
                "full_charge_notice": 1 if index % 2 else 0,
                "updated_at": moment(index, len(device_records)),
            },
        )

    for index, device in enumerate(device_records[:80], start=1):
        user = user_profiles[(index - 1) % len(user_profiles)]
        status = "success" if index % 6 else "failed"
        rows += count_insert(
            cursor,
            "device_bind_task",
            {
                "user_id": user["user_id"],
                "device_sn": device["device_number"],
                "wifi_name": demo_network_name(index),
                "wifi_password": "12345678",
                "progress": 100 if status == "success" else 68,
                "current_step": "绑定完成" if status == "success" else "连接家庭 Wi-Fi",
                "status": status,
                "error_message": None if status == "success" else "路由器信号较弱，请靠近后重试",
                "device_id": device["device_id"],
                "created_at": moment(index, 80),
                "updated_at": moment(index, 80) + timedelta(minutes=6),
                "finished_at": moment(index, 80) + timedelta(minutes=8) if status == "success" else None,
            },
        )

    log_titles = [
        ("online", "info", "设备上线", "设备心跳恢复，已连接家庭 Wi-Fi"),
        ("network", "warning", "网络抖动", "设备检测到 Wi-Fi 信号波动"),
        ("firmware", "info", "固件检查", "设备完成固件版本检测"),
        ("firmware", "error", "固件升级失败", "下载固件包超时，等待自动重试"),
        ("play", "info", "开始播放", "用户从歌单发起播放"),
        ("system", "error", "播放失败", "音乐平台临时返回超时"),
    ]
    for index, device in enumerate(device_records[:140], start=1):
        log_type, log_level, title, content = log_titles[(index - 1) % len(log_titles)]
        rows += count_insert(
            cursor,
            "device_log",
            {
                "device_id": device["device_id"],
                "device_sn": device["device_number"],
                "device_name": device["device_name"],
                "device_type": "speaker",
                "device_model": device["model_name"],
                "log_type": log_type,
                "log_level": log_level,
                "title": title,
                "content": content,
                "event_code": f"{log_type.upper()}_{index:04d}",
                "trace_id": f"TRACE-{stat_date.strftime('%m%d')}-{index:04d}",
                "task_id": None,
                "firmware_version": demo_firmware_version(index),
                "online_status": device["online_status"],
                "ip_address": f"192.168.10.{20 + ((index - 1) % 220)}",
                "network_type": "wifi",
                "location": device["device_name"][:20],
                "request_url": "/api/device/runtime",
                "request_method": "POST",
                "request_id": f"REQ-{stat_date.strftime('%m%d')}-{index:04d}",
                "response_code": 200 if log_level != "error" else 504,
                "response_message": "success" if log_level != "error" else "timeout",
                "admin_id": None,
                "operator_name": "设备自动上报",
                "operator_type": "device",
                "created_at": moment(index, 140),
                "updated_at": moment(index, 140),
            },
        )

    release_device_ids = []
    if release_ids:
        for index, device in enumerate(device_records[:72], start=1):
            release_id, firmware_id, _ = release_ids[(index - 1) % len(release_ids)]
            status = "success" if index % 8 else "failed"
            release_device_id = insert_demo_row(
                cursor,
                "device_firmware_release_device",
                {
                    "release_id": release_id,
                    "device_id": device["device_id"],
                    "status": status,
                    "progress": 100 if status == "success" else 45,
                    "fail_reason": None if status == "success" else "下载固件包超时",
                    "created_at": moment(index, 72),
                    "updated_at": moment(index, 72) + timedelta(minutes=20),
                },
            )
            if release_device_id is not None:
                rows += 1
                release_device_ids.append((release_device_id, firmware_id, device))

        for index, (release_device_id, firmware_id, device) in enumerate(release_device_ids, start=1):
            status = "success" if index % 8 else "failed"
            rows += count_insert(
                cursor,
                "device_firmware_update_task",
                {
                    "task_no": f"FW{stat_date.strftime('%Y%m%d')}{index:04d}",
                    "device_id": device["device_id"],
                    "firmware_id": firmware_id,
                    "release_device_id": release_device_id,
                    "current_version": DEMO_FIRMWARE_VERSIONS[(index - 1) % len(DEMO_FIRMWARE_VERSIONS)],
                    "target_version": DEMO_FIRMWARE_VERSIONS[index % len(DEMO_FIRMWARE_VERSIONS)],
                    "status": status,
                    "progress": 100 if status == "success" else 45,
                    "fail_reason": None if status == "success" else "设备离线，等待重试",
                    "admin_id": None,
                    "operator_name": "系统运营",
                    "started_at": moment(index, len(release_device_ids)),
                    "finished_at": moment(index, len(release_device_ids)) + timedelta(minutes=22) if status == "success" else None,
                    "created_at": moment(index, len(release_device_ids)),
                    "updated_at": moment(index, len(release_device_ids)) + timedelta(minutes=22),
                },
            )

    for index, user in enumerate(user_profiles, start=1):
        service = DEMO_PLATFORMS[(index - 1) % len(DEMO_PLATFORMS)]
        rows += count_insert(
            cursor,
            "music_service_binding",
            {
                "user_id": user["user_id"],
                "service": service,
                "account_name": user["nickname"],
                "access_token": demo_password_hash(f"{user['username']}:{service}:binding"),
                "refresh_token": demo_password_hash(f"{user['username']}:{service}:refresh"),
                "expires_at": moment(index, len(user_profiles)) + timedelta(days=30),
                "sync_status": "synced" if index % 5 else "pending",
                "bound_at": moment(index, len(user_profiles)),
                "updated_at": moment(index, len(user_profiles)) + timedelta(hours=1),
            },
        )
        rows += count_insert(
            cursor,
            "music_service_permission",
            {
                "user_id": user["user_id"],
                "service": service,
                "read_playlist": 1,
                "sync_history": 1 if index % 4 else 0,
                "personal_recommend": 1,
                "updated_at": moment(index, len(user_profiles)) + timedelta(hours=1),
            },
        )

    for index in range(1, min(90, len(user_profiles) - 1) + 1):
        rows += count_insert(
            cursor,
            "friendship",
            {
                "user_id_1": user_profiles[index - 1]["user_id"],
                "user_id_2": user_profiles[(index + 4) % len(user_profiles)]["user_id"],
            },
        )

    room_ids = []
    room_count = min(max(6, len(user_profiles) // 4), 16)
    for index in range(1, room_count + 1):
        owner = user_profiles[(index - 1) % len(user_profiles)]
        device = device_records[(index - 1) % len(device_records)]
        mapping_id, song = mapping_ids[(index - 1) % len(mapping_ids)] if mapping_ids else (None, DEMO_SONGS[(index - 1) % len(DEMO_SONGS)])
        room_id = insert_demo_row(
            cursor,
            "listen_room",
            {
                "room_code": f"ROOM{stat_date.strftime('%Y%m%d')}{index:02d}",
                "owner_user_id": owner["user_id"],
                "device_id": device["device_id"],
                "current_song_id": song[0],
                "room_name": f"{owner['nickname']}的一起听",
                "source_platform": song[3],
                "status": "active" if index % 4 else "ended",
                "created_at": moment(index, 12),
                "ended_at": None if index % 4 else moment(index, 12) + timedelta(hours=1),
            },
        )
        if room_id is not None:
            rows += 1
            room_ids.append(room_id)
            for member_index in range(1, 5):
                member = user_profiles[(index + member_index) % len(user_profiles)]
                rows += count_insert(
                    cursor,
                    "listen_room_member",
                    {
                        "room_id": room_id,
                        "user_id": member["user_id"],
                        "role": "owner" if member_index == 1 else "member",
                        "online_status": 1 if member_index != 4 else 0,
                        "joined_at": moment(index + member_index, 16),
                        "left_at": None if member_index != 4 else moment(index + member_index, 16) + timedelta(minutes=35),
                    },
                )
            for comment_index, content in enumerate(("这首歌很适合晚上听", "音质不错", "加入下一首吧"), start=1):
                commenter = user_profiles[(index + comment_index + 6) % len(user_profiles)]
                rows += count_insert(
                    cursor,
                    "listen_room_comment",
                    {
                        "room_id": room_id,
                        "user_id": commenter["user_id"],
                        "content": content,
                        "created_at": moment(index + comment_index, 15),
                    },
                )

    share_count = min(max(18, len(user_profiles) * 2), 96)
    for index in range(1, share_count + 1):
        user = user_profiles[(index - 1) % len(user_profiles)]
        _, song = mapping_ids[(index - 1) % len(mapping_ids)] if mapping_ids else (None, DEMO_SONGS[(index - 1) % len(DEMO_SONGS)])
        rows += count_insert(
            cursor,
            "share_record",
            {
                "user_id": user["user_id"],
                "song_id": song[0],
                "room_id": room_ids[(index - 1) % len(room_ids)] if room_ids else None,
                "share_type": "song" if index % 3 else "room",
                "share_url": f"https://speaker.example.com/share/{song[0]}/{index}",
                "image_url": f"https://cdn.example.com/share/{song[0]}.jpg",
                "expire_at": moment(index, share_count) + timedelta(days=7),
                "created_at": moment(index, share_count),
            },
        )

    feedback_statuses = ("open", "pending", "processed", "closed")
    feedback_templates = (
        ("播放体验反馈", "晚上播放歌单时偶尔会卡一下，希望切换歌曲更顺滑。", "experience", "偶发卡顿"),
        ("设备连接反馈", "客厅音箱有时从 Wi-Fi 恢复比较慢，重连后就正常。", "device", "连接恢复慢"),
        ("歌单同步建议", "网易云歌单同步挺方便，希望能显示最近同步时间。", "suggestion", "歌单同步"),
        ("音量体验反馈", "夜间模式音量控制很好用，希望卧室设备默认再低一点。", "experience", "夜间模式"),
        ("固件升级反馈", "升级后响应速度比之前快，偶尔会提示正在检查版本。", "praise", "响应快"),
        ("音乐平台反馈", "QQ 音乐绑定流程清楚，但授权过期提醒可以再明显一些。", "suggestion", "授权提醒"),
    )
    feedback_count = min(max(8, len(user_profiles) // 2 + rng.randint(2, 8)), 42)
    for index in range(1, feedback_count + 1):
        user = user_profiles[(index - 1) % len(user_profiles)]
        device = device_records[(index - 1) % len(device_records)]
        status = feedback_statuses[(index - 1) % len(feedback_statuses)]
        feedback_no = f"FB{stat_date.strftime('%Y%m%d')}{index:04d}"
        title, content, feedback_type, rating_tag = feedback_templates[(index - 1) % len(feedback_templates)]
        rows += count_insert(
            cursor,
            "user_feedback",
            {
                "content": content,
                "user_id": user["user_id"],
                "feedback_no": feedback_no,
                "feedback_type": feedback_type,
                "title": title,
                "contact": user["email"],
                "device_info": f"{device['device_number']} / {device['model_name']}",
                "status": status,
                "priority": "high" if index % 7 == 0 else "normal",
                "star_rating": 3 + index % 3,
                "rating_tags": "音质好,连接稳定" if index % 4 else rating_tag,
                "admin_id": None,
                "handler_name": "客服小组" if status in {"processed", "closed"} else None,
                "reply_content": "已记录并同步给设备体验团队" if status in {"processed", "closed"} else None,
                "handled_at": moment(index, feedback_count) + timedelta(hours=2) if status in {"processed", "closed"} else None,
                "closed_at": moment(index, feedback_count) + timedelta(hours=4) if status == "closed" else None,
                "created_at": moment(index, feedback_count),
                "updated_at": moment(index, feedback_count) + timedelta(hours=2),
            },
        )
        if status in {"processed", "closed"}:
            cursor.execute(
                "SELECT feedback_id FROM user_feedback WHERE feedback_no=%s ORDER BY feedback_id ASC LIMIT 1",
                (feedback_no,),
            )
            row = cursor.fetchone()
            if row:
                rows += count_insert(
                    cursor,
                    "user_feedback_process_log",
                    {
                        "feedback_id": row["feedback_id"],
                        "action": "process",
                        "action_text": "处理反馈",
                        "admin_id": None,
                        "operator_name": "客服小组",
                        "remark": "已回复用户并标记跟进",
                        "created_at": moment(index, feedback_count) + timedelta(hours=2),
                    },
                )

    audit_actions = [
        ("login", "auth", "后台登录", "/api/admin/login", "POST", "success"),
        ("view", "device", "查看设备列表", "/api/admin/operator/device/list", "GET", "success"),
        ("update", "feedback", "处理用户反馈", "/api/admin/operator/feedback/handle", "POST", "success"),
        ("create", "firmware", "发布固件任务", "/api/admin/operator/device/firmware-task", "POST", "success"),
        ("run", "daily_stats", "运行每日汇总", "/api/db/daily-stats/run", "POST", "success"),
        ("view", "report", "查看运营报表", "/api/admin/super/reports", "GET", "success"),
    ]
    for index in range(1, 121):
        action, module, operation_name, path, method, result_status = audit_actions[(index - 1) % len(audit_actions)]
        rows += count_insert(
            cursor,
            "admin_operation_log",
            {
                "admin_id": None,
                "action": action,
                "module": module,
                "operation_name": operation_name,
                "path": path,
                "request_method": method,
                "ip_address": f"10.0.0.{20 + index % 80}",
                "user_agent": "Mozilla/5.0 AdminConsole",
                "params": json.dumps({"demo": True, "index": index}, ensure_ascii=False),
                "result_status": result_status,
                "error_message": None,
                "created_at": moment(index, 120),
            },
        )

    config_rows = [
        (f"notice.daily.{stat_date.strftime('%Y%m%d')}", "今日运营数据已更新，新增用户、设备、播放和反馈已完成汇总。", "notice", "notice", "运营日报公告", "published"),
        ("monitor.api", "running", "status", "monitor_service", "后台接口服务", "平均响应 42 ms"),
        ("monitor.mysql", "running", "status", "monitor_service", "MySQL 数据库", "连接正常"),
        ("monitor.mongo", "running", "status", "monitor_service", "MongoDB 运行态", "连接正常"),
        ("decision_risk.offline", "离线设备占比需持续关注", "warning", "decision_risk", "设备离线风险", "当前离线率低于 20%"),
        ("market_recommendation.retention", "优先触达购买后 7 日内播放少于 3 次的用户。", "text", "market_recommendation", "留存运营建议", "用于营销洞察"),
    ]
    for index, (key, value, config_type, group, name, description) in enumerate(config_rows, start=1):
        upsert_demo_row(
            cursor,
            "system_config",
            {
                "config_key": key,
                "config_value": value,
                "config_type": config_type,
                "config_group": group,
                "config_name": name,
                "description": description,
                "editable": 1,
                "updated_by": None,
                "created_at": moment(index, len(config_rows)),
                "updated_at": moment(index, len(config_rows)) + timedelta(minutes=15),
            },
            ["config_value", "config_type", "config_group", "config_name", "description", "editable", "updated_by", "updated_at"],
        )
        rows += 1

    return rows


def day_moment(stat_date, index, total):
    now = local_now()
    if stat_date >= now.date() and now.replace(tzinfo=None).time() < datetime_time(8, 5, 0):
        day_start = datetime.combine(now.date(), datetime_time(0, 5, 0))
    else:
        day_start = datetime.combine(stat_date, datetime_time(8, 0, 0))
    if stat_date >= now.date():
        day_end = now.replace(tzinfo=None) - timedelta(minutes=3)
        if day_end <= day_start:
            day_start = datetime.combine(now.date(), datetime_time(0, 0, 0))
            day_end = max(day_start + timedelta(minutes=1), now.replace(tzinfo=None) - timedelta(minutes=1))
    else:
        day_end = datetime.combine(stat_date, datetime_time(22, 45, 0))
    span_seconds = max(int((day_end - day_start).total_seconds()), 1)
    offset = ((index * 9973) // max(total, 1) + index * 131) % span_seconds
    return day_start + timedelta(seconds=offset)


def spread_day_moment(stat_date, index, total, span_days=14):
    day_offset = (index - 1) % max(1, int(span_days or 1))
    return day_moment(stat_date - timedelta(days=day_offset), index, total)


def select_single_id(cursor, table, id_column, where_column, value):
    cursor.execute(
        f"SELECT {quote_identifier(id_column)} FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(where_column)}=%s ORDER BY {quote_identifier(id_column)} ASC LIMIT 1",
        (value,),
    )
    row = cursor.fetchone()
    return int(row[id_column]) if row else None


def select_all_ids(cursor, table, id_column):
    cursor.execute(
        f"SELECT {quote_identifier(id_column)} FROM {quote_identifier(table)} "
        f"ORDER BY {quote_identifier(id_column)} ASC"
    )
    return [int(row[id_column]) for row in cursor.fetchall() or [] if row.get(id_column) is not None]


def select_existing_values(cursor, table, column):
    cursor.execute(
        f"SELECT {quote_identifier(column)} FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(column)} IS NOT NULL"
    )
    return {
        str(row.get(column))
        for row in cursor.fetchall() or []
        if str(row.get(column) or "").strip()
    }


def load_all_mapping_choices(cursor):
    cursor.execute(
        """
        SELECT mapping_id, external_id, song_title, artist, platform
        FROM media_mapping
        ORDER BY mapping_id ASC
        """
    )
    rows = cursor.fetchall() or []
    return [
        (
            int(row["mapping_id"]),
            (
                row.get("external_id") or f"song-{row['mapping_id']}",
                row.get("song_title") or "未知歌曲",
                row.get("artist") or "未知歌手",
                row.get("platform") or "网易云音乐",
                "流行",
            ),
        )
        for row in rows
        if row.get("mapping_id") is not None
    ]


def demo_counts_for_date(stat_date, user_count, device_count, order_count, play_count):
    rng = random.Random(f"demo-counts:{stat_date.isoformat()}:{user_count}:{device_count}:{order_count}:{play_count}")
    target_users = rng.randint(5, max(8, min(20, int((user_count or DEFAULT_DEMO_USER_COUNT) * 2))))
    extra_devices = rng.randint(1, 8)
    target_devices = target_users + extra_devices
    if rng.random() < 0.22:
        target_devices += rng.randint(3, 8)
    target_orders = max(3, target_devices + rng.randint(-4, 5))
    if rng.random() < 0.18:
        target_orders += rng.randint(4, 10)
    target_plays = rng.randint(420, 980) + target_users * rng.randint(18, 36) + target_devices * rng.randint(8, 20)
    return {
        "user_count": target_users,
        "device_count": target_devices,
        "order_count": target_orders,
        "play_count": max(650, min(2200, target_plays)),
    }


def seed_chinese_demo_data(
    stat_date,
    user_count=DEFAULT_DEMO_USER_COUNT,
    device_count=DEFAULT_DEMO_DEVICE_COUNT,
    order_count=DEFAULT_DEMO_ORDER_COUNT,
    play_count=DEFAULT_DEMO_PLAY_COUNT,
    reset_demo_data=False,
    span_days=1,
):
    rng = random.Random(f"demo-{stat_date.isoformat()}-{user_count}-{device_count}-{order_count}-{play_count}")
    user_count = max(1, int(user_count or DEFAULT_DEMO_USER_COUNT))
    device_count = max(1, int(device_count or DEFAULT_DEMO_DEVICE_COUNT))
    order_count = max(0, int(order_count or DEFAULT_DEMO_ORDER_COUNT))
    play_count = max(0, int(play_count or DEFAULT_DEMO_PLAY_COUNT))

    connection = mysql_connect()
    created = {
        "cleared_tables": 0,
        "users": 0,
        "profiles": 0,
        "devices": 0,
        "bindings": 0,
        "orders": 0,
        "order_items": 0,
        "songs": 0,
        "play_history": 0,
        "support_rows": 0,
    }
    lock_name = f"smart_speaker_demo_seed:{stat_date.isoformat()}:{int(span_days or 1)}:{1 if reset_demo_data else 0}"
    lock_connection = acquire_mysql_named_lock(lock_name, 0)
    if lock_connection is None:
        connection.close()
        created["skipped_by_lock"] = 1
        return created
    try:
        with connection.cursor() as cursor:
            if reset_demo_data:
                created["cleared_tables"] = len(clear_chinese_demo_data(cursor))
            demo_moment = lambda index, total: spread_day_moment(stat_date, index, total, span_days)
            user_base = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM `user`", default=0) or 0)
            device_base = int(mysql_scalar(cursor, "SELECT COUNT(*) AS c FROM device", default=0) or 0)
            user_ids = []
            user_profiles = []
            used_names = select_existing_values(cursor, "user", "username")
            used_nicknames = select_existing_values(cursor, "user", "nickname")
            for index in range(1, user_count + 1):
                serial = user_base + index
                username = demo_full_name(serial, used_names)
                used_names.add(username)
                nickname = demo_nickname(username, serial, rng, used_nicknames)
                phone = f"13{(serial * 7) % 10}{stat_date.strftime('%m%d')}{serial % 10000:04d}"
                email = f"user{serial:04d}@smart-speaker.local"
                created_at = demo_moment(index, user_count)
                upsert_demo_row(
                    cursor,
                    "user",
                    {
                        "username": username,
                        "password_hash": "123456",
                        "phone": phone,
                        "created_at": created_at,
                        "nickname": nickname,
                        "avatar": "",
                        "email": email,
                        "status": "active",
                        "last_login_at": created_at + timedelta(hours=1),
                        "updated_at": created_at + timedelta(hours=1),
                    },
                    ["password_hash", "phone", "nickname", "avatar", "email", "status", "last_login_at", "updated_at"],
                )
                user_id = select_single_id(cursor, "user", "user_id", "username", username)
                if user_id is None:
                    continue
                user_ids.append(user_id)
                user_profiles.append({
                    "user_id": user_id,
                    "username": username,
                    "nickname": nickname,
                    "email": email,
                })
                region = demo_region(serial, max(user_base + user_count, 1))
                age = 18 + (serial * 3) % 38
                platform = DEMO_PLATFORMS[(serial - 1) % len(DEMO_PLATFORMS)]
                if serial % 5 == 0:
                    platform = "网易云音乐,QQ音乐"
                active_level = ("high", "medium", "high", "low", "medium")[serial % 5]
                value_level = ("high", "normal", "normal", "low", "high")[serial % 5]
                upsert_demo_row(
                    cursor,
                    "user_profile",
                    {
                        "user_id": user_id,
                        "nickname": nickname,
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
                        "user_status", "updated_at",
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
            device_records = []
            for index in range(1, device_count + 1):
                serial = device_base + index
                model_name = demo_device_model(serial)
                device_number = demo_device_number(model_name, serial)
                region = demo_region(serial, max(device_base + device_count, 1))
                room = DEMO_ROOMS[(serial - 1) % len(DEMO_ROOMS)]
                device_name = demo_room_device_name(room, serial)
                created_at = demo_moment(index, device_count)
                upsert_demo_row(
                    cursor,
                    "device",
                    {
                        "device_number": device_number,
                        "model_name": model_name,
                        "status": 1 if index % 5 else 0,
                        "last_active": created_at + timedelta(hours=2),
                        "firmware_version": demo_firmware_version(serial),
                        "created_at": created_at,
                        "device_name": device_name,
                        "device_type": "speaker",
                        "online_status": "online" if index % 5 else "offline",
                        "ip_address": f"192.168.10.{20 + ((index - 1) % 220)}",
                        "hardware_version": f"HW-{model_name}",
                        "location": region[3],
                        "updated_at": created_at + timedelta(hours=2),
                    },
                    [
                        "model_name", "status", "last_active", "firmware_version",
                        "device_name", "device_type", "online_status", "ip_address", "hardware_version",
                        "location", "updated_at",
                    ],
                )
                device_id = select_single_id(cursor, "device", "device_id", "device_number", device_number)
                if device_id is not None:
                    device_ids.append(device_id)
                    device_records.append({
                        "device_id": device_id,
                        "device_number": device_number,
                        "device_name": device_name,
                        "model_name": model_name,
                        "room": room,
                        "online_status": "online" if index % 5 else "offline",
                        "serial": serial,
                    })
                created["devices"] += 1

            for index, device_id in enumerate(device_ids):
                if not user_profiles:
                    break
                user_info = user_profiles[index % len(user_profiles)]
                device_info = device_records[index % len(device_records)]
                room = device_info["room"]
                bind_time = demo_moment(index + 1, max(len(device_ids), 1))
                upsert_demo_row(
                    cursor,
                    "user_device_binding",
                    {
                        "user_id": user_info["user_id"],
                        "device_id": device_id,
                        "custom_device_name": device_info["device_name"],
                        "is_primary": 1 if index < len(user_profiles) else 0,
                        "default_room": room,
                        "current_network": demo_network_name(device_info["serial"]),
                        "bind_time": bind_time,
                    },
                    ["custom_device_name", "is_primary", "default_room", "current_network", "bind_time"],
                )
                created["bindings"] += 1

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
            all_user_ids = select_all_ids(cursor, "user", "user_id") or user_ids
            all_device_ids = select_all_ids(cursor, "device", "device_id") or device_ids
            all_mapping_ids = load_all_mapping_choices(cursor) or mapping_ids
            new_user_active_target = min(
                len(user_ids),
                max(1, int(round(len(user_ids) * rng.uniform(0.52, 0.86)))) if user_ids else 0,
            )
            preferred_active_users = rng.sample(user_ids, new_user_active_target) if new_user_active_target else []
            active_user_target = demo_target_count(
                len(all_user_ids),
                preferred_count=max(new_user_active_target, int(round(len(user_ids) * 0.7))),
                low_ratio=0.34,
                high_ratio=0.68,
                rng=rng,
            )
            active_user_ids = demo_choice_subset(all_user_ids, active_user_target, rng, preferred_active_users)

            new_device_active_target = min(
                len(device_ids),
                max(1, int(round(len(device_ids) * rng.uniform(0.62, 0.92)))) if device_ids else 0,
            )
            preferred_active_devices = rng.sample(device_ids, new_device_active_target) if new_device_active_target else []
            active_device_target = demo_target_count(
                len(all_device_ids),
                preferred_count=max(new_device_active_target, int(round(len(device_ids) * 0.8))),
                low_ratio=0.46,
                high_ratio=0.82,
                rng=rng,
            )
            active_device_ids = demo_choice_subset(all_device_ids, active_device_target, rng, preferred_active_devices)

            unique_song_choices = demo_unique_song_choices(all_mapping_ids)
            song_target = min(
                len(unique_song_choices),
                max(16, int(round(len(DEMO_SONGS) * rng.uniform(0.55, 0.92))) + rng.randint(-3, 4)),
            )
            active_mapping_ids = demo_choice_subset(unique_song_choices, song_target, rng)

            order_records = []
            for index in range(1, order_count + 1):
                user_id = user_ids[(index - 1) % len(user_ids)] if user_ids else None
                device_id = device_ids[(index - 1) % len(device_ids)] if device_ids else None
                region = DEMO_REGIONS[(index - 1) % len(DEMO_REGIONS)]
                amount = 199 + (index % 6) * 80
                created_at = demo_moment(index, max(order_count, 1))
                order_no = f"DEMO{created_at.strftime('%Y%m%d')}{index:04d}"
                upsert_demo_row(
                    cursor,
                    "sales_order",
                    {
                        "order_no": order_no,
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
                order_id = select_single_id(cursor, "sales_order", "order_id", "order_no", order_no)
                if order_id is not None:
                    order_records.append({
                        "order_id": order_id,
                        "user_id": user_id,
                        "device_id": device_id,
                        "model_name": demo_device_model(index),
                        "amount": amount,
                        "created_at": created_at,
                    })
                created["orders"] += 1

            for index, order in enumerate(order_records, start=1):
                insert_demo_row(
                    cursor,
                    "sales_order_item",
                    {
                        "order_id": order["order_id"],
                        "user_id": order["user_id"],
                        "device_id": order["device_id"],
                        "product_name": "智能音箱",
                        "model_name": order["model_name"],
                        "quantity": 1,
                        "unit_price": order["amount"],
                        "total_amount": order["amount"],
                        "created_at": order["created_at"],
                    },
                )
                created["order_items"] += 1

            play_columns = mysql_table_columns(cursor, "play_history")
            play_names = [
                column for column in (
                    "device_id", "user_id", "mapping_id", "play_duration",
                    "created_at", "style", "source_platform",
                )
                if column in play_columns
            ]
            play_insert_sql = (
                f"INSERT INTO play_history ({', '.join(quote_identifier(column) for column in play_names)}) "
                f"VALUES ({', '.join(['%s'] * len(play_names))})"
            ) if play_names else None
            play_batch = []
            for index in range(1, play_count + 1):
                if not active_user_ids or not active_device_ids or not active_mapping_ids:
                    break
                mapping_id, song = demo_song_choice(rng, active_mapping_ids)
                play_data = filter_existing_columns({
                    "device_id": rng.choice(active_device_ids),
                    "user_id": rng.choice(active_user_ids),
                    "mapping_id": mapping_id,
                    "play_duration": rng.randint(40, 260),
                    "created_at": demo_moment(index, max(play_count, 1)),
                    "style": song[4],
                    "source_platform": song[3],
                }, play_columns)
                if not play_insert_sql:
                    break
                play_batch.append([play_data.get(column) for column in play_names])
                if len(play_batch) >= 1000:
                    cursor.executemany(play_insert_sql, play_batch)
                    play_batch.clear()
                created["play_history"] += 1
            if play_insert_sql and play_batch:
                cursor.executemany(play_insert_sql, play_batch)

            created["support_rows"] = seed_demo_support_rows(
                cursor,
                stat_date,
                rng,
                user_profiles,
                device_records,
                mapping_ids,
                order_records,
                span_days=span_days,
            )

        return created
    finally:
        connection.close()
        release_mysql_named_lock(lock_connection, lock_name)


def load_mysql_demo_snapshot():
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    d.device_id,
                    d.device_number,
                    d.device_name,
                    d.model_name,
                    d.online_status,
                    d.firmware_version,
                    b.user_id,
                    b.custom_device_name,
                    b.default_room,
                    b.current_network
                FROM device d
                LEFT JOIN user_device_binding b ON b.device_id = d.device_id
                ORDER BY d.device_id ASC
                """
            )
            devices = cursor.fetchall() or []
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.nickname,
                    u.email,
                    p.gender,
                    p.age,
                    p.age_range,
                    p.province_name,
                    p.city_name,
                    p.active_level,
                    p.value_level,
                    p.bound_platforms
                FROM `user` u
                LEFT JOIN user_profile p ON p.user_id = u.user_id
                ORDER BY u.user_id ASC
                """
            )
            users = cursor.fetchall() or []
            cursor.execute(
                """
                SELECT mapping_id, external_id, song_title, artist, platform, cover_url
                FROM media_mapping
                ORDER BY mapping_id ASC
                """
            )
            songs = cursor.fetchall() or []
    finally:
        connection.close()
    return {"devices": devices, "users": users, "songs": songs}


def seed_demo_mongo_data(stat_date, play_count=3600):
    snapshot = load_mysql_demo_snapshot()
    devices = snapshot["devices"]
    users = snapshot["users"]
    songs = snapshot["songs"]
    if not devices or not users or not songs:
        return {
            "device_metrics": 0,
            "device_runtime": 0,
            "player_state": 0,
            "play_queue": 0,
            "operation_logs": 0,
            "media_metadata": 0,
            "song_info": 0,
            "play_logs": 0,
            "user_profiles": 0,
            "music_service_auth": 0,
            "device_bindings": 0,
            "friendships": 0,
            "listen_rooms": 0,
            "listening_summaries": 0,
            "user_feedback": 0,
            "device_event_log": 0,
            "play_event_log": 0,
            "voice_command_log": 0,
            "device_status_snapshot": 0,
            "user_behavior_event": 0,
            "listen_room_message": 0,
            "feedback_attachment": 0,
            "third_party_music_raw": 0,
            "device_config_snapshot": 0,
        }

    database = get_play_log_collection().database
    collections = {
        "device_metrics": database["device_metrics"],
        "device_runtime": database["device_runtime"],
        "player_state": database["player_state"],
        "play_queue": database["play_queue"],
        "operation_logs": database["operation_logs"],
        "media_metadata": database["media_metadata"],
        "song_info": get_song_collection(),
        "play_logs": get_play_log_collection(),
        "user_profiles": database["user_profiles"],
        "music_service_auth": database["music_service_auth"],
        "device_bindings": database["device_bindings"],
        "friendships": database["friendships"],
        "listen_rooms": database["listen_rooms"],
        "listening_summaries": database["listening_summaries"],
        "user_feedback": database["user_feedback"],
        "bind_progress": database["bind_progress"],
        "music_sync_progress": database["music_sync_progress"],
        "device_event_log": database["device_event_log"],
        "play_event_log": database["play_event_log"],
        "voice_command_log": database["voice_command_log"],
        "device_status_snapshot": database["device_status_snapshot"],
        "user_behavior_event": database["user_behavior_event"],
        "listen_room_message": database["listen_room_message"],
        "feedback_attachment": database["feedback_attachment"],
        "third_party_music_raw": database["third_party_music_raw"],
        "device_config_snapshot": database["device_config_snapshot"],
    }
    for collection in collections.values():
        collection.delete_many({})

    now = utcnow()
    mongo_moment = lambda index, total: spread_day_moment(stat_date, index, total).replace(tzinfo=LOCAL_TZ)
    runtime_docs = []
    player_docs = []
    queue_docs = []
    device_metric_docs = []
    device_binding_docs = []
    bind_progress_docs = []
    status_snapshot_docs = []
    config_snapshot_docs = []
    device_event_docs = []
    for index, device in enumerate(devices, start=1):
        song = songs[(index - 1) % len(songs)]
        next_songs = [songs[(index + offset) % len(songs)] for offset in range(1, 4)]
        device_time = mongo_moment(index, max(len(devices), 1))
        device_id = int(device["device_id"])
        user_id = int(device.get("user_id") or users[(index - 1) % len(users)]["user_id"])
        network_name = device.get("current_network") or demo_network_name(index)
        room_name = device.get("default_room") or DEMO_ROOMS[(index - 1) % len(DEMO_ROOMS)]
        online = str(device.get("online_status") or "").lower() == "online"
        battery = 45 + index % 55
        volume = 25 + index % 65
        signal_strength = -35 - index % 45
        device_name = device.get("custom_device_name") or device.get("device_name")
        runtime_docs.append({
            "device_id": device_id,
            "deviceId": str(device["device_id"]),
            "device_number": device["device_number"],
            "deviceName": device_name,
            "modelName": device.get("model_name"),
            "online": online,
            "battery": battery,
            "volume": volume,
            "signalStrength": signal_strength,
            "networkType": "wifi",
            "currentNetwork": network_name,
            "room": room_name,
            "firmwareVersion": device.get("firmware_version"),
            "updated_at": device_time,
        })
        device_metric_docs.append({
            "device_id": str(device_id),
            "deviceId": str(device_id),
            "device_number": device["device_number"],
            "timestamp": int(device_time.timestamp()),
            "metrics": {
                "battery": battery,
                "volume": volume,
                "signal_strength": signal_strength,
                "current_network": network_name,
                "is_connected": online,
            },
            "user": {"user_id": user_id},
            "updated_at": device_time,
        })
        player_docs.append({
            "device_id": device_id,
            "deviceId": str(device["device_id"]),
            "isPlaying": index % 5 != 0,
            "songId": song["external_id"],
            "songName": song["song_title"],
            "artist": song["artist"],
            "source": song["platform"],
            "playTime": 20 + index % 180,
            "duration": 210 + index % 70,
            "updated_at": device_time,
        })
        queue_docs.append({
            "device_id": device_id,
            "deviceId": str(device["device_id"]),
            "queue": [
                {
                    "songId": item["external_id"],
                    "songName": item["song_title"],
                    "artist": item["artist"],
                    "source": item["platform"],
                }
                for item in next_songs
            ],
            "updated_at": device_time,
        })
        device_binding_docs.append({
            "account": str(user_id),
            "user_id": user_id,
            "device_id": device_id,
            "device_number": device["device_number"],
            "custom_device_name": device_name,
            "default_room": room_name,
            "current_network": network_name,
            "status": "bound",
            "created_at": device_time,
            "updated_at": device_time,
        })
        bind_progress_docs.append({
            "task_id": f"BIND{stat_date.strftime('%Y%m%d')}{index:04d}",
            "device_sn": device["device_number"],
            "device_id": device_id,
            "user_id": user_id,
            "overall_status": "bound",
            "progress": 100,
            "steps": ["扫码识别", "连接 Wi-Fi", "绑定账号", "同步歌单"],
            "created_at": device_time,
            "updated_at": device_time,
        })
        status_snapshot_docs.append({
            "device_id": device_id,
            "device_sn": device["device_number"],
            "online": online,
            "battery": battery,
            "volume": volume,
            "signal_strength": signal_strength,
            "reported_at": device_time,
            "created_at": device_time,
        })
        config_snapshot_docs.append({
            "device_id": device_id,
            "device_sn": device["device_number"],
            "room": room_name,
            "network_name": network_name,
            "firmware_version": device.get("firmware_version"),
            "volume_limit": 80,
            "auto_firmware_update": index % 3 != 0,
            "created_at": device_time,
        })
        device_event_docs.append({
            "device_id": device_id,
            "device_sn": device["device_number"],
            "device_type": "speaker",
            "model_name": device.get("model_name"),
            "log_type": "online" if online else "offline",
            "log_level": "info" if online else "warning",
            "event_code": "DEVICE_ONLINE" if online else "DEVICE_OFFLINE",
            "message": f"{device_name} {'上线并完成心跳' if online else '离线等待重连'}",
            "trace_id": f"trace-{stat_date.strftime('%Y%m%d')}-{index:04d}",
            "created_at": device_time,
        })

    user_profile_docs = []
    music_auth_docs = []
    friendship_docs = []
    listen_room_docs = []
    listen_room_message_docs = []
    listening_summary_docs = []
    user_feedback_docs = []
    user_behavior_docs = []
    music_sync_docs = []
    feedback_templates = [
        ("bug", "夜间偶尔断连", "昨晚播放到一半断开，重新配网后恢复。", "high", 3, "网络,断连"),
        ("suggestion", "希望增加儿童模式", "家里小朋友会误触音量，希望能限制最大音量。", "normal", 4, "儿童模式,音量"),
        ("praise", "歌单推荐很准", "最近推荐的民谣和老歌都很合口味。", "low", 5, "推荐,歌单"),
        ("bug", "固件升级后重启", "升级结束后自动重启了一次，之后可以正常使用。", "normal", 4, "固件,重启"),
    ]
    for index, user in enumerate(users, start=1):
        user_time = mongo_moment(index, max(len(users), 1))
        account = str(user["user_id"])
        platforms = str(user.get("bound_platforms") or "网易云音乐,QQ音乐")
        user_profile_docs.append({
            "account": account,
            "user_id": int(user["user_id"]),
            "display_name": user.get("nickname") or user.get("username"),
            "username": user.get("username"),
            "nickname": user.get("nickname"),
            "email": user.get("email"),
            "gender": user.get("gender") or ("female" if index % 2 else "male"),
            "age": int(user.get("age") or (22 + index % 28)),
            "age_range": user.get("age_range") or demo_age_range(22 + index % 28),
            "province_name": user.get("province_name"),
            "city_name": user.get("city_name"),
            "active_level": user.get("active_level") or ("high" if index % 4 == 0 else "medium"),
            "value_level": user.get("value_level") or ("high" if index % 5 == 0 else "normal"),
            "bound_platforms": platforms,
            "created_at": user_time,
            "updated_at": user_time,
        })
        for service in ("网易云音乐", "QQ音乐"):
            if service in platforms:
                music_auth_docs.append({
                    "account": account,
                    "user_id": int(user["user_id"]),
                    "platform_type": "netease" if service == "网易云音乐" else "qq_music",
                    "platform_name": service,
                    "status": "bound",
                    "permissions": ["play_history", "playlist", "recommendation"],
                    "sync_state": {
                        "status": "synced" if index % 7 else "syncing",
                        "progress": 100 if index % 7 else 82,
                        "last_synced_at": user_time,
                    },
                    "created_at": user_time,
                    "updated_at": user_time,
                })
        if index <= min(80, len(users)):
            event_name = ("open_app", "play_song", "bind_device", "view_playlist")[index % 4]
            user_behavior_docs.append({
                "user_id": int(user["user_id"]),
                "event_name": event_name,
                "page": "player" if event_name == "play_song" else "home",
                "platform": "wxapp",
                "properties": {"nickname": user.get("nickname"), "city": user.get("city_name")},
                "created_at": user_time,
            })
        if index <= min(72, len(users)):
            tpl = feedback_templates[(index - 1) % len(feedback_templates)]
            feedback_type, title, content, priority, rating, tags = tpl
            user_feedback_docs.append({
                "feedback_id": f"FB{stat_date.strftime('%Y%m%d')}{index:04d}",
                "user_id": int(user["user_id"]),
                "account": account,
                "nickname": user.get("nickname") or user.get("username"),
                "feedback_type": feedback_type,
                "title": title,
                "content": content,
                "priority": priority,
                "star_rating": rating,
                "rating_tags": tags,
                "status": "open" if index % 5 == 0 else "processed",
                "created_at": user_time,
                "updated_at": user_time,
            })
        if index <= min(48, len(users)):
            music_sync_docs.append({
                "user_id": int(user["user_id"]),
                "service": "netease" if index % 2 else "qq_music",
                "status": "finished" if index % 6 else "syncing",
                "progress": 100 if index % 6 else 76,
                "current_task": "同步最近播放",
                "total_songs": 120 + index * 3,
                "synced_songs": 120 + index * 3 if index % 6 else 90 + index,
                "created_at": user_time,
                "updated_at": user_time,
            })

    for index in range(1, min(80, len(users) - 1) + 1):
        user = users[index - 1]
        friend = users[(index * 5) % len(users)]
        friendship_docs.append({
            "account": str(user["user_id"]),
            "friend_account": str(friend["user_id"]),
            "user_id": int(user["user_id"]),
            "friend_user_id": int(friend["user_id"]),
            "friend_nickname": friend.get("nickname") or friend.get("username"),
            "status": "active",
            "created_at": mongo_moment(index, 80),
            "updated_at": mongo_moment(index, 80),
        })

    for index in range(1, min(18, len(devices), len(users)) + 1):
        user = users[(index - 1) % len(users)]
        device = devices[(index - 1) % len(devices)]
        room_time = mongo_moment(index, 18)
        room_id = f"ROOM{stat_date.strftime('%Y%m%d')}{index:03d}"
        listen_room_docs.append({
            "room_id": room_id,
            "owner_user_id": int(user["user_id"]),
            "owner_nickname": user.get("nickname") or user.get("username"),
            "device_id": int(device["device_id"]),
            "title": f"{device.get('default_room') or '客厅'}一起听",
            "status": "active" if index % 4 else "closed",
            "member_count": 2 + index % 6,
            "created_at": room_time,
            "updated_at": room_time,
        })
        listen_room_message_docs.append({
            "room_id": room_id,
            "user_id": int(user["user_id"]),
            "message_type": "text",
            "content": "这首歌很适合今天的歌单",
            "created_at": room_time + timedelta(minutes=2),
        })
        listening_summary_docs.append({
            "account": str(user["user_id"]),
            "user_id": int(user["user_id"]),
            "period_type": "daily",
            "period_key": stat_date.isoformat(),
            "play_count": 18 + index * 2,
            "duration_seconds": 3600 + index * 240,
            "favorite_style": DEMO_SONGS[index % len(DEMO_SONGS)][4],
            "updated_at": room_time,
        })

    metadata_docs = []
    song_docs = []
    unique_songs = []
    seen_song_ids = set()
    for song in songs:
        song_id = song.get("external_id")
        if not song_id or song_id in seen_song_ids:
            continue
        seen_song_ids.add(song_id)
        unique_songs.append(song)
    for index, song in enumerate(unique_songs, start=1):
        duration_seconds = 190 + index % 90
        metadata_docs.append({
            "song_id": song["external_id"],
            "external_id": song["external_id"],
            "name": song["song_title"],
            "artist": song["artist"],
            "platform": song["platform"],
            "cover_url": song["cover_url"],
            "duration": duration_seconds,
            "updated_at": now,
        })
        song_docs.append({
            "doc_type": "song",
            "song_id": song["external_id"],
            "name": song["song_title"],
            "artists": [song["artist"]],
            "artist_text": song["artist"],
            "album": "智能音箱演示歌单",
            "duration_ms": duration_seconds * 1000,
            "duration_seconds": duration_seconds,
            "cover_url": song["cover_url"],
            "source": song["platform"],
            "source_detail": {
                "platform": song["platform"],
                "provider": "demo",
                "provider_url": "",
                "keyword": song["song_title"],
                "fetched_at": now.isoformat(),
            },
            "updated_at": now,
        })

    third_party_raw_docs = []
    for index, song in enumerate(unique_songs[:96], start=1):
        raw_time = mongo_moment(index, max(min(len(unique_songs), 96), 1))
        third_party_raw_docs.append({
            "platform": song.get("platform") or "网易云音乐",
            "api_name": "song_detail",
            "request_id": f"MUSIC{stat_date.strftime('%Y%m%d')}{index:04d}",
            "success": True,
            "latency_ms": 42 + index % 90,
            "raw_payload": {
                "external_id": song.get("external_id"),
                "song_title": song.get("song_title"),
                "artist": song.get("artist"),
            },
            "created_at": raw_time,
        })

    operation_docs = []
    operation_actions = ("play", "pause", "volume_change", "next", "sync_music", "firmware_check")
    for index in range(1, 241):
        device = devices[(index - 1) % len(devices)]
        user = users[(index - 1) % len(users)]
        action = operation_actions[(index - 1) % len(operation_actions)]
        operation_docs.append({
            "requestId": f"REQ{stat_date.strftime('%Y%m%d')}{index:04d}",
            "device_id": int(device["device_id"]),
            "deviceId": str(device["device_id"]),
            "user_id": int(user["user_id"]),
            "username": user["username"],
            "action": action,
            "source": "manual" if index % 3 else "schedule",
            "result": "success" if index % 11 else "failed",
            "message": "操作成功" if index % 11 else "设备暂时离线",
            "created_at": spread_day_moment(stat_date, index, 240).replace(tzinfo=LOCAL_TZ),
        })

    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ph.history_id,
                    ph.created_at,
                    ph.play_duration,
                    ph.device_id,
                    ph.user_id,
                    COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)) AS external_id,
                    COALESCE(mm.song_title, '未知歌曲') AS song_title,
                    COALESCE(mm.artist, '未知歌手') AS artist,
                    COALESCE(ph.source_platform, mm.platform, '网易云音乐') AS platform,
                    COALESCE(mm.cover_url, '') AS cover_url,
                    u.username
                FROM play_history ph
                LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
                LEFT JOIN `user` u ON u.user_id=ph.user_id
                ORDER BY ph.created_at ASC, ph.history_id ASC
                """
            )
            play_rows = cursor.fetchall() or []
    finally:
        connection.close()

    play_docs = []
    play_event_docs = []
    voice_command_docs = []
    for index, row in enumerate(play_rows, start=1):
        played_at = row.get("created_at")
        if isinstance(played_at, datetime):
            played_at = played_at.replace(tzinfo=LOCAL_TZ)
        else:
            played_at = spread_day_moment(stat_date, index, max(len(play_rows), 1)).replace(tzinfo=LOCAL_TZ)
        duration = int(row.get("play_duration") or 0) or 40 + index % 220
        play_docs.append({
            "event_id": str(uuid.uuid4()),
            "source": "demo_mysql_sync",
            "song_id": row.get("external_id"),
            "song_name": row.get("song_title"),
            "artists": [row.get("artist") or "未知歌手"],
            "artist_text": row.get("artist") or "未知歌手",
            "album": "智能音箱演示歌单",
            "cover_url": row.get("cover_url") or "",
            "duration_seconds": max(duration + 20, 190 + index % 90),
            "play_duration_seconds": duration,
            "device_id": str(row.get("device_id") or ""),
            "user_account": row.get("username") or f"user_{row.get('user_id') or index}",
            "played_at": played_at,
            "stat_date": played_at.date().isoformat(),
            "created_at": now,
            "sequence": int(row.get("history_id") or index),
        })
        if index <= 600 and index % 2 == 0:
            play_event_docs.append({
                "user_id": int(row.get("user_id") or 0),
                "device_id": int(row.get("device_id") or 0),
                "event_type": "PLAY_START" if index % 9 else "PLAY_COMPLETE",
                "source_platform": row.get("platform") or "网易云音乐",
                "song": {
                    "external_id": row.get("external_id"),
                    "title": row.get("song_title"),
                    "artist": row.get("artist"),
                    "duration_seconds": max(duration + 20, 190 + index % 90),
                    "cover_url": row.get("cover_url") or "",
                },
                "created_at": played_at,
            })
        if index <= 120 and index % 6 == 0:
            voice_command_docs.append({
                "user_id": int(row.get("user_id") or 0),
                "device_id": int(row.get("device_id") or 0),
                "session_id": f"VOICE{stat_date.strftime('%Y%m%d')}{index:04d}",
                "request_id": f"VREQ{stat_date.strftime('%Y%m%d')}{index:04d}",
                "asr_text": f"播放{row.get('song_title') or '推荐歌曲'}",
                "nlu": {"intent": "play_song", "song": row.get("song_title"), "artist": row.get("artist")},
                "success": True,
                "created_at": played_at,
            })

    feedback_attachment_docs = [
        {
            "feedback_id": item["feedback_id"],
            "user_id": item["user_id"],
            "attachments": [],
            "note": item["content"],
            "created_at": item["created_at"],
        }
        for item in user_feedback_docs[:36]
    ]

    batches = {
        "device_metrics": device_metric_docs,
        "device_runtime": runtime_docs,
        "player_state": player_docs,
        "play_queue": queue_docs,
        "operation_logs": operation_docs,
        "media_metadata": metadata_docs,
        "song_info": song_docs,
        "play_logs": play_docs,
        "user_profiles": user_profile_docs,
        "music_service_auth": music_auth_docs,
        "device_bindings": device_binding_docs,
        "friendships": friendship_docs,
        "listen_rooms": listen_room_docs,
        "listening_summaries": listening_summary_docs,
        "user_feedback": user_feedback_docs,
        "bind_progress": bind_progress_docs,
        "music_sync_progress": music_sync_docs,
        "device_event_log": device_event_docs,
        "play_event_log": play_event_docs,
        "voice_command_log": voice_command_docs,
        "device_status_snapshot": status_snapshot_docs,
        "user_behavior_event": user_behavior_docs,
        "listen_room_message": listen_room_message_docs,
        "feedback_attachment": feedback_attachment_docs,
        "third_party_music_raw": third_party_raw_docs,
        "device_config_snapshot": config_snapshot_docs,
    }
    counts = {}
    for name, docs in batches.items():
        if docs:
            collections[name].insert_many(docs)
        counts[name] = len(docs)
    return counts


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
    online_devices_for_day = int(mysql_scalar(
        cursor,
        f"""
        SELECT COUNT(*) AS c
        FROM device
        WHERE DATE(created_at) <= %s
          AND {ONLINE_DEVICE_CONDITION}
        """,
        (stat_date,),
        0,
    ) or 0)
    netease_profiles_for_day = int(mysql_scalar(
        cursor,
        """
        SELECT COUNT(*) AS c
        FROM user_profile
        WHERE DATE(created_at) <= %s
          AND (bound_platforms LIKE %s OR LOWER(bound_platforms) LIKE %s)
        """,
        (stat_date, "%网易云%", "%netease%"),
        0,
    ) or 0)
    qq_profiles_for_day = int(mysql_scalar(
        cursor,
        """
        SELECT COUNT(*) AS c
        FROM user_profile
        WHERE DATE(created_at) <= %s
          AND (LOWER(bound_platforms) LIKE %s OR bound_platforms LIKE %s)
        """,
        (stat_date, "%qq%", "%QQ音乐%"),
        0,
    ) or 0)
    return {
        **stats,
        "unique_user_count": max(int(stats.get("unique_user_count") or 0), active_users),
        "active_user_count": max(int(stats.get("unique_user_count") or 0), active_users),
        "unique_device_count": max(int(stats.get("unique_device_count") or 0), active_devices),
        "online_device_count": max(active_devices, online_devices_for_day),
        "platform_wechat_count": netease_profiles_for_day,
        "platform_qq_count": qq_profiles_for_day,
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
            COUNT(DISTINCT CASE WHEN ph.history_id IS NOT NULL THEN p.user_id END) AS active_user_count,
            COUNT(DISTINCT b.device_id) AS device_count
        FROM user_profile p
        LEFT JOIN user_device_binding b ON b.user_id = p.user_id
        LEFT JOIN play_history ph ON ph.user_id = p.user_id AND DATE(ph.created_at) = %s
        GROUP BY COALESCE(p.province_code, 'unknown'),
                 COALESCE(p.province_name, p.city_name, 'unknown')
        """,
        (stat_date,),
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
            COUNT(DISTINCT p.user_id) AS user_count,
            COUNT(DISTINCT CASE WHEN ph.history_id IS NOT NULL THEN p.user_id END) AS active_user_count
        FROM user_profile p
        LEFT JOIN play_history ph ON ph.user_id = p.user_id AND DATE(ph.created_at) = %s
        GROUP BY COALESCE(p.value_level, 'normal')
        """,
        (stat_date,),
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


def day_has_play_history(stat_date):
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            return int(mysql_scalar(
                cursor,
                "SELECT COUNT(*) AS c FROM play_history WHERE DATE(created_at)=%s",
                (stat_date,),
                0,
            ) or 0) > 0
    finally:
        connection.close()


def acquire_mysql_named_lock(lock_name, timeout_seconds=0):
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, %s) AS locked", (lock_name, int(timeout_seconds or 0)))
            row = cursor.fetchone() or {}
            if int(row.get("locked") or 0) == 1:
                return connection
    except Exception:
        connection.close()
        raise
    connection.close()
    return None


def release_mysql_named_lock(connection, lock_name):
    if not connection:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
    finally:
        connection.close()


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
    needs_demo_mongo = bool(getattr(args, "generate_demo_data", False))
    if needs_mongo or needs_demo_mongo:
        ensure_mongo_schema()
    ensure_daily_stats_table()
    ensure_front_daily_tables()
    missing_dates = missing_daily_stat_dates(stat_date)
    backfilled_dates = []

    demo_data = {}
    demo_processed_dates = []
    if getattr(args, "generate_demo_data", False):
        reset_demo_data = bool(getattr(args, "reset_demo_data", False))
        demo_play_count = getattr(args, "demo_play_count", None)
        if demo_play_count is None:
            demo_play_count = args.generate_count
        demo_order_count = getattr(args, "demo_order_count", 28)
        demo_user_count = getattr(args, "demo_user_count", 36)
        demo_device_count = getattr(args, "demo_device_count", 19)
        demo_runs = []
        if reset_demo_data:
            demo_dates = list(date_range(stat_date - timedelta(days=13), stat_date))
            cleared_tables = clear_demo_mysql_data()
            cleared_mongo = clear_demo_mongo_data()
            for demo_date in demo_dates:
                counts = demo_counts_for_date(
                    demo_date,
                    demo_user_count,
                    demo_device_count,
                    demo_order_count,
                    demo_play_count,
                )
                demo_runs.append({
                    "date": demo_date.isoformat(),
                    **seed_chinese_demo_data(
                        demo_date,
                        reset_demo_data=False,
                        span_days=1,
                        **counts,
                    ),
                })
            demo_data = {
                "daily_runs": demo_runs,
                "reset_demo_data": True,
                "cleared_tables": cleared_tables,
                "cleared_mongo": cleared_mongo,
            }
        else:
            demo_dates = list(dict.fromkeys(missing_dates + [stat_date]))
            for demo_date in demo_dates:
                if day_has_play_history(demo_date):
                    demo_runs.append({
                        "date": demo_date.isoformat(),
                        "skipped_existing": True,
                        "users": 0,
                        "profiles": 0,
                        "devices": 0,
                        "bindings": 0,
                        "orders": 0,
                        "order_items": 0,
                        "songs": 0,
                        "play_history": 0,
                        "support_rows": 0,
                    })
                    continue
                counts = demo_counts_for_date(
                    demo_date,
                    demo_user_count,
                    demo_device_count,
                    demo_order_count,
                    demo_play_count,
                )
                demo_runs.append({
                    "date": demo_date.isoformat(),
                    **seed_chinese_demo_data(
                        demo_date,
                        reset_demo_data=False,
                        span_days=1,
                        **counts,
                    ),
                })
            demo_data = {
                "daily_runs": demo_runs,
                "reset_demo_data": False,
            }
        mongo_play_count = sum(int(item.get("play_history") or 0) for item in demo_data.get("daily_runs", []))
        if mongo_play_count > 0:
            try:
                demo_data["mongo"] = seed_demo_mongo_data(stat_date, mongo_play_count)
            except Exception as exc:
                demo_data["mongo_error"] = str(exc)
        else:
            demo_data["mongo"] = {"skipped_no_new_play_history": True}
        for demo_date in demo_dates:
            refresh_daily_stats_from_mysql(demo_date)
            demo_processed_dates.append(demo_date.isoformat())
    else:
        for missing_date in missing_dates:
            stats_for_missing = refresh_daily_stats_from_mysql(missing_date)
            backfilled_dates.append({
                "stat_date": missing_date.isoformat(),
                "total_play_count": int(stats_for_missing.get("total_play_count") or 0),
                "unique_user_count": int(stats_for_missing.get("unique_user_count") or 0),
                "unique_device_count": int(stats_for_missing.get("unique_device_count") or 0),
            })

    use_business_demo = bool(getattr(args, "generate_demo_data", False))
    seeded = [] if args.skip_seed or use_business_demo else seed_song_catalog(keywords)
    generated_logs = [] if args.skip_generate or use_business_demo else generate_play_logs(stat_date, args.generate_count)
    stats = (
        aggregate_from_mysql_play_history(stat_date)
        if use_business_demo
        else aggregate_from_play_logs(stat_date) if needs_mongo else aggregate_from_mysql_play_history(stat_date)
    )
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
        "processed_dates": list(dict.fromkeys([item["stat_date"] for item in backfilled_dates] + demo_processed_dates + [stat_date.isoformat()])),
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
    demo_user_count=DEFAULT_DEMO_USER_COUNT,
    demo_device_count=DEFAULT_DEMO_DEVICE_COUNT,
    demo_order_count=DEFAULT_DEMO_ORDER_COUNT,
    demo_play_count=DEFAULT_DEMO_PLAY_COUNT,
    reset_demo_data=False,
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
    args.demo_play_count = demo_play_count if demo_play_count is not None else DEFAULT_DEMO_PLAY_COUNT
    args.reset_demo_data = reset_demo_data
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
    parser.add_argument("--demo-user-count", type=int, default=DEFAULT_DEMO_USER_COUNT, help="Average number of Chinese demo users per day.")
    parser.add_argument("--demo-device-count", type=int, default=DEFAULT_DEMO_DEVICE_COUNT, help="Average number of demo devices per day.")
    parser.add_argument("--demo-order-count", type=int, default=DEFAULT_DEMO_ORDER_COUNT, help="Average number of demo paid orders per day.")
    parser.add_argument("--demo-play-count", type=int, default=DEFAULT_DEMO_PLAY_COUNT, help="Average number of demo play_history rows per day.")
    parser.add_argument("--reset-demo-data", action="store_true", help="Clear existing demo business data and rebuild the recent 14-day dataset.")
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
