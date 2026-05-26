import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime

BASE = "https://api.musicplayer.cn"
CTX = ssl._create_unverified_context()

room_id = None
task_id = None

def req(name, method, path, body=None):
    global room_id, task_id

    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    try:
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(r, context=CTX, timeout=12) as resp:
            text = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"FAIL {name}: 请求异常 {repr(e)}")
        return {"name": name, "ok": False, "status": None, "error": repr(e)}

    try:
        js = json.loads(text)
    except Exception:
        js = {"raw": text[:300]}

    code = js.get("code", 200 if status == 200 else status)
    ok = status < 500 and code not in (500,)

    print(("PASS" if ok else "FAIL"), name, "HTTP", status, "code", code)

    if name == "listen-room/create" and ok:
        data_obj = js.get("data") or {}
        room_id = data_obj.get("roomId") or data_obj.get("room_id") or data_obj.get("roomId".lower())

    if name == "device/bind" and ok:
        data_obj = js.get("data") or {}
        task_id = data_obj.get("taskId") or data_obj.get("task_id")

    return {"name": name, "ok": ok, "status": status, "code": code, "response": js}

TS = datetime.now().strftime("%Y%m%d_%H%M%S")

tests = [
    ("health", "GET", "/api/_health", None),

    ("auth/wechat-login", "POST", "/api/auth/wechat-login", {
        "code": "test_code_" + TS,
        "encryptedData": "test_encrypted",
        "iv": "test_iv"
    }),

    ("home/overview", "GET", "/api/home/overview", None),

    ("player/control", "POST", "/api/player/control", {
        "deviceId": "dev_01",
        "action": "pause",
        "source": "netease"
    }),
    ("player/volume", "POST", "/api/player/volume", {
        "deviceId": "dev_01",
        "volume": 55,
        "source": "netease"
    }),
    ("player/play-song", "POST", "/api/player/play-song", {
        "deviceId": "dev_01",
        "songId": "1491830535"
    }),
    ("player/add-next", "POST", "/api/player/add-next", {
        "deviceId": "dev_01",
        "songId": "1491830535"
    }),

    ("friends/listening", "GET", "/api/friends/listening", None),
    ("friends/search", "GET", "/api/friends/search?keyword=%E9%98%BF", None),

    ("song-info", "GET", "/api/song-info?songId=1491830535", None),
    ("play-history/list", "GET", "/api/play-history/list?page=1&pageSize=10", None),

    ("listening-data/summary", "GET", "/api/listening-data/summary?period=week&value=19", None),
    ("listening-data/weekly-report", "GET", "/api/listening-data/weekly-report?year=2026&week=19", None),
    ("listening-data/generate-card", "POST", "/api/listening-data/generate-card", {
        "year": 2026,
        "week": 19,
        "cardType": "weekly"
    }),

    ("device/detail", "GET", "/api/device/detail?deviceId=dev_01", None),
    ("device/list legacy", "GET", "/device/list", None),
    ("device/battery", "GET", "/api/device/battery?deviceId=dev_01", None),
    ("device/power-save", "POST", "/api/device/power-save", {
        "deviceId": "dev_01",
        "enabled": False
    }),
    ("device/battery-notice", "POST", "/api/device/battery-notice", {
        "deviceId": "dev_01",
        "lowBatteryEnabled": True,
        "threshold": 25,
        "fullChargeNotice": True
    }),
    ("device/rename", "POST", "/api/device/rename", {
        "deviceId": "dev_01",
        "name": "回归测试音箱_" + TS
    }),
    ("device/advanced-settings", "POST", "/api/device/advanced-settings", {
        "deviceId": "dev_01",
        "volumeLimit": 80,
        "nightModeEnabled": True,
        "nightStart": "23:00",
        "nightEnd": "07:00",
        "autoFirmwareUpdate": True
    }),
    ("device/search-nearby", "GET", "/api/device/search-nearby?keyword=dev", None),
    ("device/bind", "POST", "/api/device/bind", {
        "deviceSn": "dev_01",
        "wifiName": "Test-WiFi",
        "wifiPassword": "12345678"
    }),
    ("device/unbind fake", "POST", "/api/device/unbind", {
        "deviceId": "not_exists_for_test"
    }),

    ("music-service/bind", "POST", "/api/music-service/bind", {
        "service": "qq",
        "authCode": "test_auth_" + TS
    }),
    ("music-service/list", "GET", "/api/music-service/list", None),
    ("music-service/sync-progress", "GET", "/api/music-service/sync-progress?service=qq", None),
    ("music-service/permissions", "POST", "/api/music-service/permissions", {
        "service": "qq",
        "permissions": {
            "readPlaylist": True,
            "syncHistory": True,
            "personalRecommend": True
        }
    }),
    ("music-service/unbind", "POST", "/api/music-service/unbind", {
        "service": "qq"
    }),
]

results = []
for t in tests:
    results.append(req(*t))

# 房间链路单独跑，因为后续接口依赖 roomId
results.append(req("listen-room/create", "POST", "/api/listen-room/create", {
    "songId": "1491830535",
    "deviceId": "dev_01"
}))

rid = room_id or "1"

room_tests = [
    ("listen-room/join", "POST", "/api/listen-room/join", {"roomId": str(rid)}),
    ("listen-room/detail", "GET", "/api/listen-room/detail?roomId=" + urllib.parse.quote(str(rid)), None),
    ("listen-room/comment", "POST", "/api/listen-room/comment", {
        "roomId": str(rid),
        "content": "回归测试评论_" + TS
    }),
    ("share/song-link", "POST", "/api/share/song-link", {
        "songId": "1491830535",
        "roomId": str(rid)
    }),
    ("share/song-card", "POST", "/api/share/song-card", {
        "songId": "1491830535",
        "roomId": str(rid)
    }),
    ("listen-room/leave", "POST", "/api/listen-room/leave", {"roomId": str(rid)}),
]

for t in room_tests:
    results.append(req(*t))

passed = sum(1 for x in results if x["ok"])
failed = [x for x in results if not x["ok"]]

print("\n" + "=" * 80)
print("总接口数：", len(results))
print("通过：", passed)
print("失败：", len(failed))

if failed:
    print("\n失败列表：")
    for x in failed:
        print("-", x["name"], "HTTP", x["status"], "code", x.get("code"))
        print("  response:", json.dumps(x.get("response"), ensure_ascii=False)[:500])

with open("runtime/smoke_existing_apis_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print("\n结果已保存：runtime/smoke_existing_apis_result.json")
