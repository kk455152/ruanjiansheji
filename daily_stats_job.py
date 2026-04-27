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
    utcnow,
)


LOCAL_TZ = timezone(timedelta(hours=8))
DEFAULT_SONG_KEYWORDS = ["稻香", "晴天", "夜曲", "青花瓷", "七里香"]
DEFAULT_DEVICES = [f"dev_{index:02d}" for index in range(1, 6)]


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
    connection = pymysql.connect(**get_mysql_config())
    try:
        with connection.cursor() as cursor:
            cursor.execute(DAILY_STATS_TABLE_SQL)
    finally:
        connection.close()


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
    INSERT INTO Daily_Stats (
        stat_date,
        total_play_count,
        unique_song_count,
        unique_user_count,
        unique_device_count,
        total_play_duration_seconds,
        avg_play_duration_seconds,
        hottest_song_id,
        hottest_song_name,
        hottest_artist,
        hottest_play_count,
        generated_at,
        updated_at
    ) VALUES (
        %(stat_date)s,
        %(total_play_count)s,
        %(unique_song_count)s,
        %(unique_user_count)s,
        %(unique_device_count)s,
        %(total_play_duration_seconds)s,
        %(avg_play_duration_seconds)s,
        %(hottest_song_id)s,
        %(hottest_song_name)s,
        %(hottest_artist)s,
        %(hottest_play_count)s,
        NOW(),
        NOW()
    )
    ON DUPLICATE KEY UPDATE
        total_play_count = VALUES(total_play_count),
        unique_song_count = VALUES(unique_song_count),
        unique_user_count = VALUES(unique_user_count),
        unique_device_count = VALUES(unique_device_count),
        total_play_duration_seconds = VALUES(total_play_duration_seconds),
        avg_play_duration_seconds = VALUES(avg_play_duration_seconds),
        hottest_song_id = VALUES(hottest_song_id),
        hottest_song_name = VALUES(hottest_song_name),
        hottest_artist = VALUES(hottest_artist),
        hottest_play_count = VALUES(hottest_play_count),
        updated_at = NOW()
    """
    connection = pymysql.connect(**get_mysql_config())
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, stats)
    finally:
        connection.close()


def run_once(args):
    stat_date = parse_stat_date(args.date)
    keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]

    ensure_mongo_schema()
    ensure_daily_stats_table()

    seeded = [] if args.skip_seed else seed_song_catalog(keywords)
    generated_logs = [] if args.skip_generate else generate_play_logs(stat_date, args.generate_count)
    stats = aggregate_from_play_logs(stat_date)
    upsert_daily_stats(stats)

    return {
        "ok": True,
        "mongo_database": get_mongo_database_name(),
        "song_collection": "song_info",
        "play_log_collection": "play_logs",
        "daily_stats_table": "Daily_Stats",
        "stat_date": stat_date.isoformat(),
        "seeded_song_count": len(seeded),
        "generated_play_log_count": len(generated_logs),
        "stats": {
            **stats,
            "stat_date": stats["stat_date"].isoformat(),
        },
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Seed song JSON and build MySQL Daily_Stats.")
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
