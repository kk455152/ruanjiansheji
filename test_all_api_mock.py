import json
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://127.0.0.1:5000"


def build_url(path):
    if "?" in path:
        route, query = path.split("?", 1)
        return BASE + urllib.parse.quote(route, safe="/") + "?" + urllib.parse.quote(query, safe="=&")
    return BASE + urllib.parse.quote(path, safe="/")


def request_api(method, path, token=None, body=None):
    url = build_url(path)
    data = None
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = "Bearer " + token

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, True, json.loads(text)
            except Exception:
                return resp.status, False, text[:120]
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, True, json.loads(text)
        except Exception:
            return e.code, False, text[:120]
    except Exception as e:
        return 0, False, str(e)


login_status, login_json, login_resp = request_api(
    "POST",
    "/api/auth/wechat-login",
    body={"code": "test_code_all_api", "encryptedData": "demo_encrypted", "iv": "demo_iv", "nickname": "接口测试用户"},
)

token = login_resp.get("token", "") if isinstance(login_resp, dict) else ""

tests = [
    ("GET", "/api/_health", None),
    ("POST", "/api/auth/wechat-login", {"code": "test_code_all_api_2", "encryptedData": "demo", "iv": "demo"}),
    ("GET", "/api/home/overview", None),
    ("POST", "/api/player/control", {"deviceId": "dev_001", "action": "pause", "source": "netease"}),
    ("POST", "/api/player/volume", {"deviceId": "dev_001", "volume": 60, "source": "netease"}),
    ("POST", "/api/player/play-song", {"deviceId": "dev_001", "songId": "1491830535"}),
    ("POST", "/api/player/add-next", {"deviceId": "dev_001", "songId": "1491830535"}),
    ("GET", "/api/friends/listening", None),
    ("GET", "/api/friends/search?keyword=阿青", None),
    ("POST", "/api/listen-room/create", {"songId": "song_001", "deviceId": "dev_001"}),
    ("POST", "/api/listen-room/join", {"roomId": "room_001"}),
    ("GET", "/api/listen-room/detail?roomId=room_001", None),
    ("POST", "/api/listen-room/comment", {"roomId": "room_001", "content": "这首歌很好听"}),
    ("POST", "/api/listen-room/leave", {"roomId": "room_001"}),
    ("POST", "/api/share/song-link", {"songId": "song_001", "roomId": "room_001"}),
    ("POST", "/api/share/song-card", {"songId": "song_001", "roomId": "room_001"}),
    ("GET", "/api/listening-data/summary?period=week&value=19", None),
    ("GET", "/api/song-info?songId=1491830535", None),
    ("GET", "/api/play-history/list?source=netease&keyword=城市", None),
    ("DELETE", "/api/play-history/clear-old", {"days": 30}),
    ("DELETE", "/api/play-history/delete", {"historyId": "__test_history__"}),
    ("GET", "/api/listening-data/weekly-report?year=2026&week=19", None),
    ("POST", "/api/listening-data/generate-card", {"year": 2026, "week": 19, "cardType": "weekly"}),
    ("GET", "/api/device/list", None),
    ("GET", "/device/list", None),
    ("GET", "/api/device/detail?deviceId=dev_001", None),
    ("GET", "/api/device/battery?deviceId=dev_001", None),
    ("POST", "/api/device/power-save", {"deviceId": "dev_001", "enabled": True}),
    ("POST", "/api/device/battery-notice", {"deviceId": "dev_001", "lowBatteryEnabled": True, "threshold": 20, "fullChargeNotice": True}),
    ("POST", "/api/device/rename", {"deviceId": "dev_001", "name": "客厅音箱"}),
    ("POST", "/api/device/advanced-settings", {"deviceId": "dev_001", "volumeLimit": 80, "nightModeEnabled": True, "nightStart": "23:00", "nightEnd": "07:00", "autoFirmwareUpdate": True}),
    ("GET", "/api/device/search-nearby?keyword=Mini", None),
    ("POST", "/api/device/bind", {"deviceSn": "SHMINI-A1-0001", "wifiName": "Home-5G", "wifiPassword": "12345678"}),
    ("GET", "/api/device/bind-progress?taskId=bind_001", None),
    ("POST", "/api/device/unbind", {"deviceId": "dev_001"}),
    ("POST", "/api/music-service/bind", {"service": "qq", "authCode": "demo_auth_code"}),
    ("GET", "/api/music-service/list", None),
    ("GET", "/api/music-service/sync-progress?service=qq", None),
    ("POST", "/api/music-service/permissions", {"service": "qq", "permissions": {"readPlaylist": True, "syncHistory": True, "personalRecommend": True}}),
    ("POST", "/api/music-service/unbind", {"service": "qq"}),
]

print("登录接口:", login_status, "JSON" if login_json else "非JSON", "TOKEN=", bool(token))
print()
print("{:<8} {:<55} {:<8} {:<8} {}".format("METHOD", "PATH", "STATUS", "JSON", "RESULT"))

failed = 0

for method, path, body in tests:
    status, is_json, resp = request_api(method, path, token=token, body=body)
    passed = 200 <= status < 300 and is_json

    if path.startswith("/api/player/add-next") and status == 409 and is_json:
        passed = True

    if not passed:
        failed += 1

    if isinstance(resp, dict):
        msg = resp.get("message") or resp.get("msg") or "OK"
    else:
        msg = str(resp).replace("\n", " ")[:80]

    print("{:<8} {:<55} {:<8} {:<8} {}".format(method, path[:55], status, "YES" if is_json else "NO", msg))

print()
print("失败数量:", failed)
print("结论:", "全接口验收通过" if failed == 0 else "还有接口需要修")
