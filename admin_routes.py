import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, jsonify, request, g

from api_pkg.common import json_safe, load_state, mysql_all, mysql_exec, mysql_one, save_state


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
admin_compat_bp = Blueprint("admin_compat", __name__)

TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET", "smart-speaker-admin-secret")
TOKEN_EXPIRE_SECONDS = int(os.environ.get("ADMIN_TOKEN_EXPIRE_SECONDS", "7200"))
ADMIN_CACHE_TTL_SECONDS = float(os.environ.get("ADMIN_CACHE_TTL_SECONDS", "30"))
_ADMIN_CACHE = {}
_ADMIN_CACHE_LOCK = threading.Lock()


DEFAULT_ADMINS = {
    "admin": {
        "adminId": 1,
        "username": "admin",
        "password": os.environ.get("ADMIN_PASSWORD", "123456"),
        "role": "super_admin",
        "roleName": "超级管理员",
        "realName": "张三",
        "jobNo": "A001",
        "position": "超级管理员",
        "phone": "13800000001",
        "email": "admin@example.com",
    },
    "market": {
        "adminId": 2,
        "username": "market",
        "password": os.environ.get("MARKET_ADMIN_PASSWORD", "123456"),
        "role": "market_admin",
        "roleName": "市场分析管理员",
        "realName": "李四",
        "jobNo": "M001",
        "position": "市场分析管理员",
        "phone": "13800000000",
        "email": "market@example.com",
        "wechatOpenId": "oXxx123456789",
    },
    "operator": {
        "adminId": 3,
        "username": "operator",
        "password": os.environ.get("OPERATOR_ADMIN_PASSWORD", "123456"),
        "role": "operator_admin",
        "roleName": "普通管理员",
        "realName": "王五",
        "jobNo": "O001",
        "position": "普通管理员",
        "phone": "13800000002",
        "email": "operator@example.com",
    },
}

ROLE_SCOPES = {
    "super_admin": {"super", "market", "operator"},
    "market_admin": {"market"},
    "operator_admin": {"operator"},
}

def response_ok(data=None, message=None, code=200):
    body = {"code": code}
    if message is not None:
        body["message"] = message
    body["data"] = json_safe(data)
    return jsonify(body), code


def response_error(code, message, error_details=None):
    body = {"code": code, "message": message}
    if error_details is not None:
        body["error_details"] = error_details
    else:
        body["data"] = None
    return jsonify(body), code


def _b64_encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(text):
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def public_admin_info(admin, include_private=False):
    keys = [
        "adminId",
        "username",
        "role",
        "roleName",
        "realName",
        "jobNo",
        "position",
    ]
    if include_private:
        keys += ["phone", "email", "wechatOpenId"]
    return {key: admin.get(key) for key in keys if key in admin}


def sign_token(admin):
    payload = {
        "adminId": admin["adminId"],
        "username": admin["username"],
        "role": admin["role"],
        "exp": int((datetime.now() + timedelta(seconds=TOKEN_EXPIRE_SECONDS)).timestamp()),
        "nonce": secrets.token_hex(8),
    }
    payload_part = _b64_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64_encode(signature)}"


def decode_token(token):
    try:
        payload_part, signature_part = token.split(".", 1)
        expected = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64_decode(signature_part), expected):
            return None
        payload = json.loads(_b64_decode(payload_part).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now().timestamp()):
            return None
        admin = DEFAULT_ADMINS.get(payload.get("username"))
        if not admin or admin.get("role") != payload.get("role"):
            return None
        return admin
    except Exception:
        return None


def bearer_token():
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth or None


def require_admin(*scopes):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            admin = decode_token(bearer_token() or "")
            if not admin:
                return response_error(401, "未登录", "请先登录后台管理系统")

            allowed = ROLE_SCOPES.get(admin["role"], set())
            if scopes and not any(scope in allowed for scope in scopes):
                return response_error(403, "无权限访问", "当前账号无权访问该后台接口")

            g.admin = admin
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def _float(value, default=0.0):
    try:
        return float(value or default)
    except Exception:
        return default


def cached_value(key, loader, ttl=ADMIN_CACHE_TTL_SECONDS):
    now = datetime.now().timestamp()
    with _ADMIN_CACHE_LOCK:
        item = _ADMIN_CACHE.get(key)
        if item and item["expire_at"] > now:
            return item["value"]

    value = loader()
    with _ADMIN_CACHE_LOCK:
        _ADMIN_CACHE[key] = {"value": value, "expire_at": now + ttl}
    return value


def count_sql(sql, params=(), fallback=0):
    def loader():
        row = mysql_one(sql, params)
        if not row:
            return fallback
        return _int(next(iter(row.values())), fallback)

    return cached_value(("count", sql, tuple(params), fallback), loader)


def cached_mysql_all(sql, params=(), fallback=None):
    return cached_value(
        ("all", sql, tuple(params)),
        lambda: mysql_all(sql, params) or (fallback or []),
    )


def current_device():
    state_device = load_state().get("device", {})
    row = mysql_one(
        """
        SELECT
            d.device_id,
            d.device_number,
            d.model_name,
            d.status,
            d.last_active,
            b.custom_device_name,
            u.username AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        ORDER BY d.device_id ASC
        LIMIT 1
        """
    )
    if row:
        return {
            "deviceId": str(row.get("device_id")),
            "deviceSn": row.get("device_number") or "SHMINI-A1-0001",
            "deviceName": row.get("custom_device_name") or "客厅音箱",
            "modelName": row.get("model_name") or "SH-Mini A1",
            "ownerName": row.get("owner_name") or "张三",
            "online": bool(row.get("status")),
            "firmwareVersion": state_device.get("firmware", "1.0.3"),
            "lastOnlineAt": str(row.get("last_active") or "2026-05-20 10:00:00"),
            "volume": state_device.get("volume", 60),
            "battery": state_device.get("battery", 82),
            "signalStrength": state_device.get("signalStrength", -73.59),
            "currentNetwork": state_device.get("currentNetwork", "Home-5G"),
            "createdAt": "2026-05-01 10:00:00",
        }

    return {
        "deviceId": state_device.get("deviceId", "dev_001"),
        "deviceSn": state_device.get("deviceSn", "SHMINI-A1-0001"),
        "deviceName": state_device.get("deviceName", "客厅音箱"),
        "modelName": state_device.get("modelName", "SH-Mini A1"),
        "ownerName": "张三",
        "online": bool(state_device.get("online", True)),
        "firmwareVersion": state_device.get("firmware", "1.0.3"),
        "lastOnlineAt": "2026-05-20 10:00:00",
        "volume": state_device.get("volume", 60),
        "battery": state_device.get("battery", 82),
        "signalStrength": state_device.get("signalStrength", -73.59),
        "currentNetwork": state_device.get("currentNetwork", "Home-5G"),
        "createdAt": "2026-05-01 10:00:00",
    }


def fallback_series(metric_type, dimension):
    today = datetime.now().date()
    base = {"user": 120, "device": 80, "sales": 65000}.get(metric_type, 120)
    result = []

    if dimension == "week":
        for index in range(8):
            week_day = today - timedelta(weeks=7 - index)
            label = f"{week_day.isocalendar().year}-W{week_day.isocalendar().week:02d}"
            result.append({"date": label, "value": base + index * (48 if metric_type != "sales" else 12500)})
        return result

    if dimension == "month":
        year = today.year
        month = today.month
        for index in range(12):
            offset = 11 - index
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            result.append({"date": f"{y}-{m:02d}", "value": base + index * (96 if metric_type != "sales" else 28000)})
        return result

    if dimension == "year":
        for index in range(5):
            result.append({"date": str(today.year - 4 + index), "value": base + index * (380 if metric_type != "sales" else 120000)})
        return result

    for index in range(12):
        day = today - timedelta(days=11 - index)
        result.append({"date": day.isoformat(), "value": base + index * (13 if metric_type != "sales" else 3500)})
    return result


def distribution_data(kind):
    if kind == "age":
        return [
            {"ageRange": "18-25", "count": 320},
            {"ageRange": "26-35", "count": 460},
            {"ageRange": "36-45", "count": 260},
            {"ageRange": "46+", "count": 120},
        ]
    if kind == "region":
        return [
            {"regionName": "广东省", "count": 500},
            {"regionName": "重庆市", "count": 260},
            {"regionName": "四川省", "count": 220},
            {"regionName": "浙江省", "count": 180},
        ]
    if kind == "activity":
        return [
            {"level": "high", "levelName": "高活跃", "count": 260},
            {"level": "normal", "levelName": "普通用户", "count": 900},
            {"level": "silent", "levelName": "沉默用户", "count": 120},
        ]
    return [
        {"service": "qq", "serviceName": "QQ音乐", "count": 300},
        {"service": "netease", "serviceName": "网易云音乐", "count": 260},
        {"service": "kuwo", "serviceName": "酷我音乐", "count": 90},
    ]


def heatmap(kind):
    rows = [
        ("440000", "广东省", 65000, 50, 520, 180),
        ("500000", "重庆市", 42000, 32, 260, 92),
        ("510000", "四川省", 38000, 28, 220, 76),
        ("330000", "浙江省", 35000, 25, 180, 66),
    ]
    if kind == "sales":
        return [{"regionCode": code, "regionName": name, "salesAmount": sales, "orderCount": orders} for code, name, sales, orders, _, _ in rows]
    return [{"regionCode": code, "regionName": name, "userCount": users, "activeUserCount": active} for code, name, _, _, users, active in rows]


def feedback_rows():
    rows = cached_mysql_all(
        """
        SELECT f.feedback_id, f.user_id, f.content, u.username, u.phone
        FROM user_feedback f
        LEFT JOIN `user` u ON u.user_id = f.user_id
        ORDER BY f.feedback_id DESC
        LIMIT 50
        """
    )
    if rows:
        result = []
        for row in rows:
            feedback_id = str(row.get("feedback_id"))
            result.append({
                "feedbackId": feedback_id,
                "userId": row.get("user_id"),
                "nickname": row.get("username") or "用户",
                "avatar": f"https://example.com/avatar/{row.get('user_id') or 0}.png",
                "phone": row.get("phone") or "138****8888",
                "feedbackType": "suggestion",
                "feedbackTypeText": "意见建议",
                "content": row.get("content") or "",
                "images": [],
                "contact": row.get("phone") or "",
                "status": "pending",
                "statusText": "待处理",
                "priority": "normal",
                "priorityText": "普通",
                "rating": 4,
                "ratingText": "4星",
                "handlerId": None,
                "handlerName": None,
                "replyContent": None,
                "handledAt": None,
                "createdAt": "2026-05-20 10:20:30",
            })
        return result

    return [
        {
            "feedbackId": "FB202501310001",
            "userId": 10086,
            "nickname": "张三",
            "avatar": "https://example.com/avatar/10086.png",
            "phone": "138****8888",
            "feedbackType": "bug",
            "feedbackTypeText": "问题反馈",
            "content": "登录时偶尔提示网络异常，但网络是正常的。",
            "images": [
                "https://example.com/feedback/FB202501310001_1.png",
                "https://example.com/feedback/FB202501310001_2.png",
            ],
            "contact": "13888888888",
            "status": "pending",
            "statusText": "待处理",
            "priority": "normal",
            "priorityText": "普通",
            "rating": 4,
            "ratingText": "4星",
            "handlerId": None,
            "handlerName": None,
            "replyContent": None,
            "handledAt": None,
            "createdAt": "2025-01-31 10:20:30",
        },
        {
            "feedbackId": "FB202501310002",
            "userId": 10087,
            "nickname": "李雷",
            "avatar": "https://example.com/avatar/10087.png",
            "phone": "139****6666",
            "feedbackType": "suggestion",
            "feedbackTypeText": "意见建议",
            "content": "希望数据分析页面增加更多图表。",
            "images": [],
            "contact": "13966666666",
            "status": "processing",
            "statusText": "处理中",
            "priority": "high",
            "priorityText": "高",
            "rating": 5,
            "ratingText": "5星",
            "handlerId": 3,
            "handlerName": "普通管理员",
            "replyContent": None,
            "handledAt": None,
            "createdAt": "2025-02-01 14:08:10",
        },
    ]


def feedback_detail(feedback_id):
    row = next((item for item in feedback_rows() if str(item["feedbackId"]) == str(feedback_id)), feedback_rows()[0])
    return {
        "feedbackId": row["feedbackId"],
        "userInfo": {
            "userId": row["userId"],
            "nickname": row["nickname"],
            "avatar": row["avatar"],
            "phone": row["phone"],
            "email": "zhangsan@example.com",
            "registerTime": "2024-08-12 09:30:20",
            "userStatus": "normal",
            "userStatusText": "正常",
        },
        "feedbackInfo": {
            "feedbackType": row["feedbackType"],
            "feedbackTypeText": row["feedbackTypeText"],
            "title": "登录时提示网络异常",
            "content": row["content"],
            "images": row["images"],
            "contact": row["contact"],
            "source": "app",
            "sourceText": "移动端 App",
            "appVersion": "1.2.5",
            "deviceInfo": {"deviceType": "iOS", "deviceModel": "iPhone 14", "systemVersion": "17.4"},
        },
        "processInfo": {
            "status": row["status"],
            "statusText": row["statusText"],
            "priority": row["priority"],
            "priorityText": row["priorityText"],
            "rating": row.get("rating", 4),
            "ratingText": row.get("ratingText", "4星"),
            "handlerId": row["handlerId"],
            "handlerName": row["handlerName"],
            "replyContent": row["replyContent"],
            "handledAt": row["handledAt"],
            "createdAt": row["createdAt"],
        },
    }


@admin_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()

    if not username or not password:
        return response_error(400, "登录失败", "请求参数不完整，用户名和密码不能为空。")

    admin = DEFAULT_ADMINS.get(username)
    if not admin or not hmac.compare_digest(password, admin["password"]):
        return response_error(401, "认证失败", "用户名或密码错误，请重新输入。")

    token = sign_token(admin)
    return response_ok({"token": token, "adminInfo": public_admin_info(admin)}, "登录成功")


@admin_bp.post("/wechat-login")
def wechat_login():
    body = request.get_json(silent=True) or {}
    if not str(body.get("code", "")).strip():
        return response_error(400, "请求参数错误", "code 不能为空")

    admin = DEFAULT_ADMINS["market"]
    token = sign_token(admin)
    return response_ok(
        {
            "access_token": token,
            "token": token,
            "token_type": "Bearer",
            "expires_in": TOKEN_EXPIRE_SECONDS,
            "adminInfo": public_admin_info(admin, include_private=True),
        },
        "微信登录成功",
    )


@admin_bp.get("/profile")
@require_admin("super", "market", "operator")
def profile():
    return response_ok(public_admin_info(g.admin, include_private=True))


@admin_bp.post("/logout")
@require_admin("super", "market", "operator")
def logout():
    return response_ok(None, "退出登录成功")


@admin_bp.get("/super/overview/user-count")
@require_admin("super")
def user_count():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    new_count = count_sql("SELECT COUNT(*) AS c FROM `user` WHERE created_at >= CURDATE()", fallback=35)
    return response_ok({"userCount": total, "newUserCount": new_count})


@admin_bp.get("/super/overview/device-count")
@require_admin("super")
def device_count():
    total = count_sql("SELECT COUNT(*) AS c FROM device", fallback=860)
    online = count_sql("SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0) = 1", fallback=320)
    return response_ok({"deviceCount": total, "onlineDeviceCount": online, "offlineDeviceCount": max(total - online, 0)})


@admin_bp.get("/super/overview/sales-amount")
@require_admin("super")
def sales_amount():
    return response_ok({"salesAmount": 325000.5, "orderCount": 240})


@admin_bp.get("/super/overview/activity-rate")
@require_admin("super")
def activity_rate():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    active = count_sql(
        "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        fallback=380,
    )
    return response_ok({"activeUserCount": active, "totalUserCount": total, "activityRate": round(active / max(total, 1), 4)})


@admin_bp.get("/super/trend/growth")
@require_admin("super")
def growth_trend():
    metric_type = request.args.get("type", "user")
    dimension = request.args.get("dimension", "day")
    return response_ok({"type": metric_type, "dimension": dimension, "list": fallback_series(metric_type, dimension)})


@admin_bp.get("/super/region/sales-heatmap")
@admin_bp.get("/market/region/sales-heatmap")
@require_admin("super", "market")
def sales_heatmap():
    return response_ok({"list": heatmap("sales")})


@admin_bp.get("/super/region/user-heatmap")
@admin_bp.get("/market/region/user-heatmap")
@require_admin("super", "market")
def user_heatmap():
    return response_ok({"list": heatmap("user")})


@admin_bp.get("/super/user-value/normal-users")
@admin_bp.get("/market/user-value/normal-users")
@require_admin("super", "market")
def normal_users():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    high_active = count_sql(
        "SELECT COUNT(*) AS c FROM (SELECT user_id FROM play_history GROUP BY user_id HAVING COUNT(*) >= 10) t",
        fallback=260,
    )
    return response_ok({"normalUserCount": max(total - high_active, 0) or 900})


@admin_bp.get("/super/user-value/high-active-users")
@admin_bp.get("/market/user-value/high-active-users")
@require_admin("super", "market")
def high_active_users():
    count = count_sql(
        "SELECT COUNT(*) AS c FROM (SELECT user_id FROM play_history GROUP BY user_id HAVING COUNT(*) >= 10) t",
        fallback=260,
    )
    return response_ok({"highActiveUserCount": count})


@admin_bp.get("/super/user-profile/age-distribution")
@admin_bp.get("/market/user-profile/age-distribution")
@require_admin("super", "market")
def age_distribution():
    return response_ok({"list": distribution_data("age")})


@admin_bp.get("/super/user-profile/region-distribution")
@admin_bp.get("/market/user-profile/region-distribution")
@require_admin("super", "market")
def region_distribution():
    return response_ok({"list": distribution_data("region")})


@admin_bp.get("/super/user-profile/activity-distribution")
@admin_bp.get("/market/user-profile/activity-distribution")
@require_admin("super", "market")
def activity_distribution():
    return response_ok({"list": distribution_data("activity")})


@admin_bp.get("/super/user-profile/music-service-distribution")
@admin_bp.get("/market/user-profile/music-service-distribution")
@require_admin("super", "market")
def music_service_distribution():
    return response_ok({"list": distribution_data("service")})


@admin_bp.get("/super/feedback/list")
@admin_bp.get("/operator/feedback/list")
@require_admin("super", "operator")
def feedback_list():
    rows = feedback_rows()
    page = max(_int(request.args.get("page"), 1), 1)
    page_size = max(min(_int(request.args.get("pageSize"), 10), 100), 1)
    start = (page - 1) * page_size
    return response_ok(
        {
            "page": page,
            "pageSize": page_size,
            "total": len(rows),
            "totalPages": (len(rows) + page_size - 1) // page_size,
            "list": rows[start:start + page_size],
        },
        "获取成功",
    )


@admin_bp.get("/super/feedback/detail")
@admin_bp.get("/operator/feedback/detail")
@require_admin("super", "operator")
def feedback_detail_route():
    feedback_id = request.args.get("feedbackId", "FB202501310001")
    return response_ok(feedback_detail(feedback_id), "获取成功")


@admin_bp.get("/market/top-songs")
@require_admin("super", "market")
def top_songs():
    rows = cached_mysql_all(
        """
        SELECT hottest_song_name, hottest_artist, hottest_play_count
        FROM Daily_Stats
        WHERE hottest_song_name IS NOT NULL
        ORDER BY stat_date DESC
        LIMIT 10
        """
    )
    if rows:
        data = [
            {
                "rank": index + 1,
                "songName": row.get("hottest_song_name") or "城市夜航",
                "artist": row.get("hottest_artist") or "Luna Echo",
                "platform": "netease",
                "playCount": _int(row.get("hottest_play_count"), 0),
                "userCount": max(_int(row.get("hottest_play_count"), 0) // 2, 1),
            }
            for index, row in enumerate(rows)
        ]
    else:
        data = [
            {"rank": 1, "songName": "城市夜航", "artist": "Luna Echo", "platform": "qq", "playCount": 128, "userCount": 60},
            {"rank": 2, "songName": "雨后电台", "artist": "阿青", "platform": "netease", "playCount": 96, "userCount": 44},
        ]
    return response_ok({"list": data})


@admin_bp.get("/market/retention/device-purchase")
@require_admin("super", "market")
def retention_device_purchase():
    today = datetime.now().date()
    data = []
    for index in range(7):
        date_value = today - timedelta(days=6 - index)
        purchases = 80 + index * 7
        day1 = int(purchases * 0.62)
        day7 = int(purchases * 0.35)
        day30 = int(purchases * 0.18)
        data.append({
            "date": date_value.isoformat(),
            "purchaseUserCount": purchases,
            "day1RetainedCount": day1,
            "day7RetainedCount": day7,
            "day30RetainedCount": day30,
            "day1RetentionRate": round(day1 / purchases, 4),
            "day7RetentionRate": round(day7 / purchases, 4),
            "day30RetentionRate": round(day30 / purchases, 4),
        })
    return response_ok({"list": data})


@admin_bp.get("/market/profile")
@require_admin("super", "market")
def market_profile():
    admin = g.admin if g.admin["role"] == "market_admin" else DEFAULT_ADMINS["market"]
    return response_ok(public_admin_info(admin, include_private=True))


@admin_bp.get("/operator/device/firmware-version")
@require_admin("super", "operator")
def firmware_version():
    device = current_device()
    return response_ok({
        "deviceId": device["deviceId"],
        "deviceName": device["deviceName"],
        "modelName": device["modelName"],
        "currentVersion": device["firmwareVersion"],
        "latestVersion": os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"),
        "needUpdate": device["firmwareVersion"] != os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"),
    })


@admin_bp.post("/operator/device/update-firmware")
@require_admin("super", "operator")
def update_firmware():
    body = request.get_json(silent=True) or {}
    device = current_device()
    return response_ok(
        {
            "taskId": int(datetime.now().strftime("%m%d%H%M%S")),
            "deviceId": body.get("deviceId") or device["deviceId"],
            "targetVersion": body.get("targetVersion") or os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"),
            "status": "pending",
        },
        "固件更新任务已创建",
    )


@admin_bp.get("/operator/device/list")
@require_admin("super", "operator")
def operator_device_list():
    rows = cached_mysql_all(
        """
        SELECT
            d.device_id,
            d.model_name,
            d.status,
            d.last_active,
            b.custom_device_name,
            u.username AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        ORDER BY d.device_id ASC
        LIMIT 100
        """
    )
    if rows:
        devices = [
            {
                "deviceId": str(row.get("device_id")),
                "deviceName": row.get("custom_device_name") or "客厅音箱",
                "modelName": row.get("model_name") or "SH-Mini A1",
                "ownerName": row.get("owner_name") or "张三",
                "online": bool(row.get("status")),
                "firmwareVersion": "1.0.3",
                "lastOnlineAt": str(row.get("last_active") or "2026-05-20 10:00:00"),
            }
            for row in rows
        ]
    else:
        d = current_device()
        devices = [{
            "deviceId": d["deviceId"],
            "deviceName": d["deviceName"],
            "modelName": d["modelName"],
            "ownerName": d["ownerName"],
            "online": d["online"],
            "firmwareVersion": d["firmwareVersion"],
            "lastOnlineAt": d["lastOnlineAt"],
        }]
    return response_ok({"total": len(devices), "list": devices})


@admin_bp.get("/operator/device/detail")
@require_admin("super", "operator")
def operator_device_detail():
    return response_ok(current_device())


@admin_bp.get("/operator/device/runtime-status")
@require_admin("super", "operator")
def runtime_status():
    state = load_state()
    device = current_device()
    playing = state.get("playing", {})
    return response_ok({
        "deviceId": request.args.get("deviceId") or device["deviceId"],
        "online": device["online"],
        "battery": device["battery"],
        "volume": device["volume"],
        "currentSong": playing.get("songName") or playing.get("name") or "城市夜航",
        "currentArtist": playing.get("artist") or "Luna Echo",
        "lastHeartbeat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@admin_bp.post("/operator/device/rename")
@require_admin("super", "operator")
def rename_device():
    body = request.get_json(silent=True) or {}
    device_id = str(body.get("deviceId") or current_device()["deviceId"])
    name = str(body.get("name") or body.get("deviceName") or "客厅音箱").strip()
    mysql_exec(
        "UPDATE user_device_binding SET custom_device_name=%s WHERE device_id=%s",
        (name, device_id),
    )
    state = load_state()
    state.setdefault("device", {})["deviceName"] = name
    save_state(state)
    return response_ok({"deviceId": device_id, "name": name}, "设备名称修改成功")


@admin_bp.post("/operator/device/unbind")
@require_admin("super", "operator")
def unbind_device():
    body = request.get_json(silent=True) or {}
    device_id = str(body.get("deviceId") or current_device()["deviceId"])
    mysql_exec("DELETE FROM user_device_binding WHERE device_id=%s", (device_id,))
    return response_ok({"deviceId": device_id, "unbound": True}, "设备解绑成功")


@admin_bp.get("/operator/device/logs")
@require_admin("super", "operator")
def device_logs():
    device = current_device()
    rows = [
        {"logId": 1, "deviceId": device["deviceId"], "deviceName": device["deviceName"], "logType": "online", "content": "设备上线", "createdAt": "2026-05-20 10:00:00"},
        {"logId": 2, "deviceId": device["deviceId"], "deviceName": device["deviceName"], "logType": "firmware", "content": "固件升级任务已下发", "createdAt": "2026-05-20 10:30:00"},
    ]
    return response_ok({"total": len(rows), "list": rows})


@admin_bp.get("/operator/device/log-detail")
@require_admin("super", "operator")
def device_log_detail():
    device = current_device()
    return response_ok(
        {
            "logId": _int(request.args.get("logId"), 900001),
            "deviceId": device["deviceId"],
            "deviceSn": device["deviceSn"],
            "deviceName": device["deviceName"],
            "deviceType": "speaker",
            "deviceTypeText": "智能音箱",
            "deviceModel": device["modelName"],
            "logType": "firmware",
            "logTypeText": "固件日志",
            "logLevel": "info",
            "logLevelText": "普通信息",
            "title": "固件升级任务已下发",
            "content": "设备接收到固件升级任务，目标版本：1.3.0",
            "eventCode": "FIRMWARE_UPDATE_ISSUED",
            "traceId": "TRACE202501310001",
            "taskId": "FWU202501310001",
            "firmwareVersion": "1.3.0",
            "onlineStatus": "online" if device["online"] else "offline",
            "onlineStatusText": "在线" if device["online"] else "离线",
            "ipAddress": "192.168.1.100",
            "networkType": "wifi",
            "location": "客厅",
            "extra": {
                "currentVersion": device["firmwareVersion"],
                "targetVersion": "1.3.0",
                "batteryLevel": device["battery"],
                "signalStrength": device["signalStrength"],
            },
            "stackTrace": None,
            "requestInfo": {"method": "POST", "path": "/api/admin/operator/device/update-firmware"},
            "createdAt": "2026-05-20 10:30:00",
        },
        "获取成功",
    )


@admin_compat_bp.get("/api/operator/market/profile")
@require_admin("super", "market", "operator")
def legacy_operator_market_profile():
    admin = g.admin if g.admin["role"] in ("market_admin", "operator_admin") else DEFAULT_ADMINS["market"]
    return response_ok(public_admin_info(admin, include_private=True))
