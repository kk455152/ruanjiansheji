import os
import sys
import json
import time
import urllib.request
from datetime import datetime

ROOT = "/www/wwwroot/mysite"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from db import get_mysql_conn, mongo_db

BASE = "http://127.0.0.1:5000"
TAG = "FINAL_CHECK_" + datetime.now().strftime("%Y%m%d_%H%M%S")

MYSQL_CANDIDATES = [
    "share_record",
    "api_share_record",
    "play_history",
    "api_play_history",
]

MONGO_CANDIDATES = [
    "operation_logs",
    "play_logs",
    "play_queue",
    "player_state",
    "device_runtime",
]


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        return resp.status, text


def mysql_tables():
    conn = get_mysql_conn()
    try:
        with conn.cursor() as c:
            c.execute("SHOW TABLES")
            return [list(row.values())[0] for row in c.fetchall()]
    finally:
        conn.close()


def mysql_count(table):
    conn = get_mysql_conn()
    try:
        with conn.cursor() as c:
            c.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
            return int(c.fetchone()["cnt"])
    finally:
        conn.close()


def mongo_count(collection):
    if collection not in mongo_db.list_collection_names():
        return None
    return mongo_db[collection].count_documents({})


existing_mysql = [t for t in MYSQL_CANDIDATES if t in mysql_tables()]
existing_mongo = [c for c in MONGO_CANDIDATES if c in mongo_db.list_collection_names()]

before = {}
for t in existing_mysql:
    before["MySQL." + t] = mysql_count(t)
for c in existing_mongo:
    before["MongoDB." + c] = mongo_count(c)

print("========== 本次测试标记 ==========")
print(TAG)

print("\n========== 调用接口 ==========")

calls = [
    ("/api/share/song-link", {
        "songId": "song_" + TAG + "_share",
        "roomId": "room_001",
        "testTag": TAG,
    }),
    ("/api/player/volume", {
        "deviceId": "dev_001",
        "volume": 88,
        "source": "netease",
        "testTag": TAG,
    }),
    ("/api/player/play-song", {
        "deviceId": "dev_001",
        "songId": "song_" + TAG + "_play",
        "source": "netease",
        "testTag": TAG,
    }),
    ("/api/player/add-next", {
        "deviceId": "dev_001",
        "songId": "song_" + TAG + "_next",
        "source": "netease",
        "testTag": TAG,
    }),
]

for path, data in calls:
    status, text = post(path, data)
    print(f"{path:<28} {status}")

time.sleep(2)

after = {}
for t in existing_mysql:
    after["MySQL." + t] = mysql_count(t)
for c in existing_mongo:
    after["MongoDB." + c] = mongo_count(c)

print("\n========== 数据库数量变化 ==========")
print(f"{'数据库对象':<32} {'测试前':>8} {'测试后':>8} {'变化':>8}")
print("-" * 62)

changed_items = []

for name in before:
    old = before[name]
    new = after[name]
    diff = new - old
    if diff != 0:
        changed_items.append(name)
    print(f"{name:<32} {old:>8} {new:>8} {diff:>8}")

print("\n========== 小判断 ==========")

mysql_changed = any(name.startswith("MySQL.") and after[name] > before[name] for name in before)
mongo_changed = any(name.startswith("MongoDB.") and after[name] > before[name] for name in before)

if mysql_changed and mongo_changed:
    print("结论：本次测试通过。接口调用后，MySQL 和 MongoDB 的真实数据数量均发生增加。")
    print("说明：接口不是只返回 200，而是产生了实际落库数据。")
elif mysql_changed and not mongo_changed:
    print("结论：部分通过。MySQL 数量增加，但 MongoDB 数量没有增加。")
elif mongo_changed and not mysql_changed:
    print("结论：部分通过。MongoDB 数量增加，但 MySQL 数量没有增加。")
else:
    print("结论：未通过。接口有响应，但数据库数量没有变化。")

print("\n发生变化的对象：")
if changed_items:
    for item in changed_items:
        print("-", item)
else:
    print("无")
