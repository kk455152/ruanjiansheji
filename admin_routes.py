import base64
import hashlib
import hmac
import json
import os
import random
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
    "boss": {
        "adminId": 4,
        "username": "boss",
        "password": os.environ.get("BOSS_PASSWORD", "123456"),
        "role": "boss",
        "roleName": "老板",
        "realName": "老板",
        "jobNo": "B001",
        "position": "老板",
        "phone": "13800000004",
        "email": "boss@example.com",
    },
}

ROLE_SCOPES = {
    "super_admin": {"super", "market", "operator"},
    "market_admin": {"market"},
    "operator_admin": {"operator"},
    # 老板：只读经营分析视角，授予分析类只读接口的访问范围
    "boss": {"boss"},
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

    return _fallback_feedback_rows()


_FEEDBACK_SEEDS = [
    ("张三", 10086, "138****8888", "bug", "问题反馈",
     "登录时偶尔提示网络异常，但网络是正常的。", "pending", "待处理", "normal", "普通", 4),
    ("李雷", 10087, "139****6666", "suggestion", "意见建议",
     "希望数据分析页面增加更多图表。", "processing", "处理中", "high", "高", 5),
    ("韩梅梅", 10088, "137****1234", "suggestion", "意见建议",
     "音箱能不能支持自定义唤醒词？现在的唤醒词太长了。", "pending", "待处理", "normal", "普通", 4),
    ("王芳", 10089, "135****5678", "bug", "问题反馈",
     "升级到最新固件后，蓝牙连接经常自动断开。", "pending", "待处理", "high", "高", 2),
    ("赵磊", 10090, "136****4321", "suggestion", "意见建议",
     "建议增加儿童模式，能限制播放内容和使用时长。", "processing", "处理中", "normal", "普通", 5),
    ("陈静", 10091, "133****8765", "praise", "表扬建议",
     "音质很棒，语音识别也很准，整体体验非常满意！", "processed", "已处理", "low", "低", 5),
    ("刘洋", 10092, "188****2468", "bug", "问题反馈",
     "多设备组网后，客厅和卧室的音箱播放不同步，有回声。", "pending", "待处理", "high", "高", 3),
    ("孙悦", 10093, "189****1357", "suggestion", "意见建议",
     "希望 App 能查看历史播放记录，方便找回喜欢的歌。", "pending", "待处理", "normal", "普通", 4),
    ("周杰", 10094, "150****9090", "bug", "问题反馈",
     "闹钟设置后偶尔不响，错过了好几次上班时间。", "processing", "处理中", "high", "高", 2),
    ("吴敏", 10095, "151****3030", "suggestion", "意见建议",
     "能不能接入更多音乐平台？现在曲库里有些歌找不到。", "pending", "待处理", "normal", "普通", 4),
    ("郑爽", 10096, "152****6060", "praise", "表扬建议",
     "客服响应很快，上次反馈的问题第二天就修复了，点赞。", "processed", "已处理", "low", "低", 5),
    ("冯刚", 10097, "153****7070", "bug", "问题反馈",
     "语音助手有时会无故被触发，半夜突然说话吓人一跳。", "pending", "待处理", "high", "高", 2),
]


def _fallback_feedback_rows():
    seeds = list(_FEEDBACK_SEEDS)
    # 没有真实数据时，每次刷新随机抽取并打乱顺序，使刷新可见地更新反馈列表
    random.shuffle(seeds)
    count = random.randint(5, len(seeds))
    seeds = seeds[:count]
    rows = []
    base = datetime.now()
    for index, (nickname, user_id, phone, ftype, ftype_text, content,
                status, status_text, priority, priority_text, rating) in enumerate(seeds):
        created = base - timedelta(hours=index * 6 + random.randint(0, 5),
                                   minutes=random.randint(0, 59))
        rows.append({
            "feedbackId": f"FB{created.strftime('%Y%m%d')}{user_id}{index:02d}",
            "userId": user_id,
            "nickname": nickname,
            "avatar": f"https://example.com/avatar/{user_id}.png",
            "phone": phone,
            "feedbackType": ftype,
            "feedbackTypeText": ftype_text,
            "content": content,
            "images": [],
            "contact": phone.replace("****", "0000"),
            "status": status,
            "statusText": status_text,
            "priority": priority,
            "priorityText": priority_text,
            "rating": rating,
            "ratingText": f"{rating}星",
            "handlerId": 3 if status != "pending" else None,
            "handlerName": "普通管理员" if status != "pending" else None,
            "replyContent": "已记录，将在下个版本优化" if status == "processed" else None,
            "handledAt": created.strftime("%Y-%m-%d %H:%M:%S") if status != "pending" else None,
            "createdAt": created.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return rows


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
@require_admin("super", "market", "operator", "boss")
def profile():
    return response_ok(public_admin_info(g.admin, include_private=True))


@admin_bp.post("/logout")
@require_admin("super", "market", "operator", "boss")
def logout():
    return response_ok(None, "退出登录成功")


@admin_bp.get("/super/overview/user-count")
@require_admin("super", "boss")
def user_count():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    new_count = count_sql("SELECT COUNT(*) AS c FROM `user` WHERE created_at >= CURDATE()", fallback=35)
    return response_ok({"userCount": total, "newUserCount": new_count})


@admin_bp.get("/super/overview/device-count")
@require_admin("super", "boss")
def device_count():
    total = count_sql("SELECT COUNT(*) AS c FROM device", fallback=860)
    online = count_sql("SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0) = 1", fallback=320)
    return response_ok({"deviceCount": total, "onlineDeviceCount": online, "offlineDeviceCount": max(total - online, 0)})


@admin_bp.get("/super/overview/sales-amount")
@require_admin("super", "boss")
def sales_amount():
    return response_ok({"salesAmount": 325000.5, "orderCount": 240})


@admin_bp.get("/super/overview/activity-rate")
@require_admin("super", "boss")
def activity_rate():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    active = count_sql(
        "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        fallback=380,
    )
    return response_ok({"activeUserCount": active, "totalUserCount": total, "activityRate": round(active / max(total, 1), 4)})


@admin_bp.get("/super/trend/growth")
@require_admin("super", "boss")
def growth_trend():
    metric_type = request.args.get("type", "user")
    dimension = request.args.get("dimension", "day")
    return response_ok({"type": metric_type, "dimension": dimension, "list": fallback_series(metric_type, dimension)})


@admin_bp.get("/super/region/sales-heatmap")
@admin_bp.get("/market/region/sales-heatmap")
@require_admin("super", "market", "boss")
def sales_heatmap():
    return response_ok({"list": heatmap("sales")})


@admin_bp.get("/super/region/user-heatmap")
@admin_bp.get("/market/region/user-heatmap")
@require_admin("super", "market", "boss")
def user_heatmap():
    return response_ok({"list": heatmap("user")})


@admin_bp.get("/super/user-value/normal-users")
@admin_bp.get("/market/user-value/normal-users")
@require_admin("super", "market", "boss")
def normal_users():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    high_active = count_sql(
        "SELECT COUNT(*) AS c FROM (SELECT user_id FROM play_history GROUP BY user_id HAVING COUNT(*) >= 10) t",
        fallback=260,
    )
    return response_ok({"normalUserCount": max(total - high_active, 0) or 900})


@admin_bp.get("/super/user-value/high-active-users")
@admin_bp.get("/market/user-value/high-active-users")
@require_admin("super", "market", "boss")
def high_active_users():
    count = count_sql(
        "SELECT COUNT(*) AS c FROM (SELECT user_id FROM play_history GROUP BY user_id HAVING COUNT(*) >= 10) t",
        fallback=260,
    )
    return response_ok({"highActiveUserCount": count})


@admin_bp.get("/super/user-profile/age-distribution")
@admin_bp.get("/market/user-profile/age-distribution")
@require_admin("super", "market", "boss")
def age_distribution():
    return response_ok({"list": distribution_data("age")})


@admin_bp.get("/super/user-profile/region-distribution")
@admin_bp.get("/market/user-profile/region-distribution")
@require_admin("super", "market", "boss")
def region_distribution():
    return response_ok({"list": distribution_data("region")})


@admin_bp.get("/super/user-profile/activity-distribution")
@admin_bp.get("/market/user-profile/activity-distribution")
@require_admin("super", "market", "boss")
def activity_distribution():
    return response_ok({"list": distribution_data("activity")})


@admin_bp.get("/super/user-profile/music-service-distribution")
@admin_bp.get("/market/user-profile/music-service-distribution")
@require_admin("super", "market", "boss")
def music_service_distribution():
    return response_ok({"list": distribution_data("service")})


@admin_bp.get("/super/feedback/list")
@admin_bp.get("/operator/feedback/list")
@require_admin("super", "operator", "boss")
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
@require_admin("super", "operator", "boss")
def feedback_detail_route():
    feedback_id = request.args.get("feedbackId", "FB202501310001")
    return response_ok(feedback_detail(feedback_id), "获取成功")


@admin_bp.get("/market/top-songs")
@require_admin("super", "market", "boss")
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


def admin_state_section(name, default):
    state = load_state()
    admin_state = state.setdefault("admin_console", {})
    section = admin_state.setdefault(name, default)
    save_state(state)
    return section


def save_admin_state_section(name, value):
    state = load_state()
    state.setdefault("admin_console", {})[name] = value
    save_state(state)
    return value


def daily_stats_rows(limit=12):
    limit = max(min(_int(limit, 12), 60), 1)
    rows = cached_mysql_all(
        f"""
        SELECT stat_date, total_play_count, unique_user_count, unique_device_count,
               total_play_duration_seconds, avg_play_duration_seconds,
               hottest_song_name, hottest_artist, hottest_play_count
        FROM Daily_Stats
        ORDER BY stat_date DESC
        LIMIT {limit}
        """
    )
    if rows:
        return list(reversed(rows))

    today = datetime.now().date()
    return [
        {
            "stat_date": (today - timedelta(days=limit - index - 1)).isoformat(),
            "total_play_count": 1200 + index * 86,
            "unique_user_count": 180 + index * 9,
            "unique_device_count": 96 + index * 5,
            "total_play_duration_seconds": 180000 + index * 7600,
            "avg_play_duration_seconds": 188 + index,
            "hottest_song_name": "城市夜航",
            "hottest_artist": "Luna Echo",
            "hottest_play_count": 96 + index * 6,
        }
        for index in range(limit)
    ]


def admin_users_data():
    rows = cached_mysql_all(
        """
        SELECT user_id, username, phone, created_at
        FROM `user`
        ORDER BY user_id ASC
        LIMIT 20
        """
    )
    users = [
        {
            "adminId": admin["adminId"],
            "username": admin["username"],
            "realName": admin["realName"],
            "role": admin["role"],
            "roleName": admin["roleName"],
            "jobNo": admin["jobNo"],
            "position": admin["position"],
            "phone": admin.get("phone"),
            "email": admin.get("email"),
            "status": "enabled",
            "lastLoginAt": "2026-05-29 09:30:00",
        }
        for admin in DEFAULT_ADMINS.values()
    ]
    for row in rows[:6]:
        users.append(
            {
                "adminId": f"user-{row.get('user_id')}",
                "username": row.get("username") or f"user{row.get('user_id')}",
                "realName": row.get("username") or "业务用户",
                "role": "customer",
                "roleName": "绑定用户",
                "jobNo": "-",
                "position": "智能音箱用户",
                "phone": row.get("phone"),
                "email": "",
                "status": "readonly",
                "lastLoginAt": str(row.get("created_at") or "-"),
            }
        )
    return users


def device_admin_rows():
    rows = cached_mysql_all(
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
        LIMIT 100
        """
    )
    if rows:
        return [
            {
                "deviceId": str(row.get("device_id")),
                "deviceSn": row.get("device_number") or str(row.get("device_id")),
                "deviceName": row.get("custom_device_name") or "声盒 Mini",
                "modelName": row.get("model_name") or "SH-Mini A1",
                "ownerName": row.get("owner_name") or "未绑定",
                "online": bool(row.get("status")),
                "firmwareVersion": "1.0.3",
                "lastOnlineAt": str(row.get("last_active") or "-"),
            }
            for row in rows
        ]

    device = current_device()
    return [
        {
            "deviceId": device["deviceId"],
            "deviceSn": device["deviceSn"],
            "deviceName": device["deviceName"],
            "modelName": device["modelName"],
            "ownerName": device["ownerName"],
            "online": device["online"],
            "firmwareVersion": device["firmwareVersion"],
            "lastOnlineAt": device["lastOnlineAt"],
        }
    ]


def role_rows():
    return [
        {
            "role": "super_admin",
            "roleName": "超级管理员",
            "description": "系统配置、用户权限、审计、安全和全量业务数据",
            "permissions": ["system", "users", "roles", "audit", "reports", "devices", "feedback"],
            "userCount": 1,
        },
        {
            "role": "market_admin",
            "roleName": "市场分析管理员",
            "description": "用户画像、区域分析、留存分析、热歌排行和报表导出",
            "permissions": ["decision", "profile", "region", "segments", "reports", "songs"],
            "userCount": 1,
        },
        {
            "role": "operator_admin",
            "roleName": "普通管理员",
            "description": "设备运维、固件升级、用户反馈、日志和告警处理",
            "permissions": ["devices", "firmware", "tasks", "alerts", "feedback", "logs"],
            "userCount": 1,
        },
    ]


# 后台所有可授权的功能模块（key 与前端菜单 key 一一对应）
PERMISSION_CATALOG = {
    "overview": "数据总览",
    "decision": "决策驾驶舱",
    "trend": "趋势分析",
    "region": "区域热力图",
    "profile": "用户画像",
    "value": "用户价值",
    "segments": "用户分群",
    "insights": "营销洞察",
    "songs": "热歌排行",
    "reports": "决策报表",
    "feedback": "用户反馈",
    "devices": "设备管理",
    "groups": "设备分组",
    "alerts": "告警中心",
    "firmware": "设备固件",
    "tasks": "任务中心",
    "logs": "设备日志",
    "users": "用户管理",
    "roles": "角色权限",
    "system": "系统配置",
    "monitor": "系统监控",
    "notices": "系统公告",
    "audit": "审计日志",
    "account": "个人信息",
}


def merged_role_rows():
    """基础角色 + 已保存的权限覆盖。"""
    overrides = admin_state_section("rolePermissions", {})
    rows = []
    for base in role_rows():
        row = dict(base)
        saved = overrides.get(base["role"])
        if isinstance(saved, list):
            row["permissions"] = [p for p in saved if p in PERMISSION_CATALOG]
        rows.append(row)
    return rows


@admin_bp.get("/super/system/config")
@require_admin("super")
def system_config():
    return response_ok(
        admin_state_section(
            "systemConfig",
            {
                "systemName": "声盒 Mini 后台管理系统",
                "logoText": "Mini",
                "defaultTheme": "green",
                "uploadLimitMb": 100,
                "apiTimeoutSeconds": 15,
                "dataRetentionDays": 365,
                "tokenExpireSeconds": TOKEN_EXPIRE_SECONDS,
                "wechatLoginEnabled": True,
            },
        )
    )


@admin_bp.post("/super/system/config")
@require_admin("super")
def update_system_config():
    body = request.get_json(silent=True) or {}
    current = admin_state_section("systemConfig", {})
    current.update({key: value for key, value in body.items() if value is not None})
    return response_ok(save_admin_state_section("systemConfig", current), "系统配置已保存")


@admin_bp.get("/super/users")
@require_admin("super")
def admin_users():
    users = admin_users_data()
    return response_ok({"total": len(users), "list": users})


@admin_bp.get("/super/roles")
@require_admin("super")
def admin_roles():
    rows = merged_role_rows()
    catalog = [{"key": key, "label": label} for key, label in PERMISSION_CATALOG.items()]
    return response_ok({"total": len(rows), "list": rows, "catalog": catalog})


@admin_bp.post("/super/roles/permissions")
@require_admin("super")
def update_role_permissions():
    body = request.get_json(silent=True) or {}
    role = body.get("role")
    permissions = body.get("permissions")

    valid_roles = {row["role"] for row in role_rows()}
    if role not in valid_roles:
        return response_error(400, "无效的角色")
    if not isinstance(permissions, list):
        return response_error(400, "权限格式不正确")

    invalid = [p for p in permissions if p not in PERMISSION_CATALOG]
    if invalid:
        return response_error(400, f"包含未知权限：{'、'.join(invalid)}")

    # 去重并按目录顺序归一化
    cleaned = [key for key in PERMISSION_CATALOG if key in set(permissions)]

    overrides = dict(admin_state_section("rolePermissions", {}))
    overrides[role] = cleaned
    save_admin_state_section("rolePermissions", overrides)

    rows = merged_role_rows()
    return response_ok({"list": rows}, "角色权限已更新")


@admin_bp.get("/super/security/logs")
@require_admin("super")
def security_logs():
    rows = [
        {"logId": "SEC-001", "level": "info", "event": "管理员登录", "actor": "admin", "ip": "127.0.0.1", "createdAt": "2026-05-29 09:30:00"},
        {"logId": "SEC-002", "level": "warning", "event": "设备固件任务下发", "actor": g.admin["username"], "ip": "127.0.0.1", "createdAt": "2026-05-29 10:12:00"},
        {"logId": "SEC-003", "level": "info", "event": "查看用户画像报表", "actor": "market", "ip": "127.0.0.1", "createdAt": "2026-05-29 10:35:00"},
    ]
    return response_ok({"total": len(rows), "list": rows})


@admin_bp.get("/super/monitor")
@require_admin("super", "boss")
def system_monitor():
    total_users = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    total_devices = count_sql("SELECT COUNT(*) AS c FROM device", fallback=860)
    online_devices = count_sql("SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0) = 1", fallback=320)
    feedback_total = len(feedback_rows())
    return response_ok(
        {
            "services": [
                {"name": "Web API", "status": "healthy", "latencyMs": 46},
                {"name": "MySQL", "status": "healthy", "latencyMs": 28},
                {"name": "MongoDB", "status": "connected", "latencyMs": 62},
            ],
            "metrics": {
                "totalUsers": total_users,
                "totalDevices": total_devices,
                "onlineDevices": online_devices,
                "feedbackTotal": feedback_total,
                "apiErrorRate": 0.004,
                "storageUsage": "62%",
            },
            "exceptions": [
                {"code": "DEVICE_OFFLINE_SPIKE", "title": "设备离线率上升", "count": max(total_devices - online_devices, 0), "level": "warning"},
                {"code": "FEEDBACK_PENDING", "title": "待处理反馈", "count": feedback_total, "level": "info"},
            ],
        }
    )


@admin_bp.get("/super/notices")
@require_admin("super")
def admin_notices():
    notices = admin_state_section(
        "notices",
        [
            {"noticeId": "N-001", "title": "固件 1.0.5 灰度发布", "type": "upgrade", "status": "published", "createdAt": "2026-05-29 09:00:00"},
            {"noticeId": "N-002", "title": "本周后台维护窗口", "type": "maintenance", "status": "draft", "createdAt": "2026-05-28 18:00:00"},
        ],
    )
    return response_ok({"total": len(notices), "list": notices})


@admin_bp.post("/super/notices")
@require_admin("super")
def create_admin_notice():
    body = request.get_json(silent=True) or {}
    notices = admin_state_section("notices", [])
    notice = {
        "noticeId": f"N-{len(notices) + 1:03d}",
        "title": body.get("title") or "新的系统公告",
        "type": body.get("type") or "notice",
        "status": body.get("status") or "draft",
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    notices.insert(0, notice)
    save_admin_state_section("notices", notices)
    return response_ok(notice, "公告已创建")


@admin_bp.get("/super/decision/summary")
@admin_bp.get("/market/decision/summary")
@require_admin("super", "market")
def decision_summary():
    stats = daily_stats_rows(8)
    latest = stats[-1] if stats else {}
    return response_ok(
        {
            "cards": [
                {"label": "播放次数", "value": _int(latest.get("total_play_count"), 0), "trend": "+12%"},
                {"label": "活跃用户", "value": _int(latest.get("unique_user_count"), 0), "trend": "+8%"},
                {"label": "活跃设备", "value": _int(latest.get("unique_device_count"), 0), "trend": "+6%"},
                {"label": "平均播放时长", "value": f"{_int(latest.get('avg_play_duration_seconds'), 0)} 秒", "trend": "+3%"},
            ],
            "trend": stats,
            "risks": [
                {"name": "设备离线异常", "level": "warning", "value": "需关注"},
                {"name": "差评突增", "level": "normal", "value": "稳定"},
                {"name": "销售下降", "level": "normal", "value": "未触发"},
            ],
        }
    )


@admin_bp.get("/super/reports")
@admin_bp.get("/market/reports")
@require_admin("super", "market")
def admin_reports():
    stats = daily_stats_rows(10)
    reports = [
        {
            "reportId": f"R-{index + 1:03d}",
            "name": f"{row.get('stat_date')} 智能音箱运营日报",
            "type": "daily",
            "summary": f"播放 {row.get('total_play_count')} 次，活跃用户 {row.get('unique_user_count')} 人",
            "exportFormats": ["PDF", "Excel"],
            "createdAt": str(row.get("stat_date")),
        }
        for index, row in enumerate(reversed(stats[-5:]))
    ]
    return response_ok({"total": len(reports), "list": reports, "raw": stats})


@admin_bp.get("/market/segments")
@require_admin("super", "market")
def market_segments():
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=1280)
    active = count_sql(
        "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        fallback=380,
    )
    device_total = count_sql("SELECT COUNT(*) AS c FROM device", fallback=860)
    return response_ok(
        {
            "total": 4,
            "list": [
                {"name": "高活跃用户", "rule": "近 7 天播放 >= 10 次", "count": active, "action": "推送会员权益"},
                {"name": "潜在流失用户", "rule": "近 14 天无播放", "count": max(total - active, 0), "action": "召回提醒"},
                {"name": "新购设备用户", "rule": "设备绑定 <= 30 天", "count": max(device_total // 5, 1), "action": "新手引导"},
                {"name": "音乐平台深度用户", "rule": "绑定 QQ/网易云", "count": max(total // 3, 1), "action": "歌单推荐"},
            ],
        }
    )


@admin_bp.get("/market/insights")
@require_admin("super", "market")
def market_insights():
    return response_ok(
        {
            "funnels": [
                {"label": "新增用户", "value": 420, "rate": 1},
                {"label": "绑定设备", "value": 318, "rate": 0.76},
                {"label": "完成首播", "value": 246, "rate": 0.59},
                {"label": "7 日留存", "value": 148, "rate": 0.35},
            ],
            "recommendations": [
                "针对潜在流失用户推送热门歌单",
                "广东、重庆地区适合投放设备升级活动",
                "提升固件升级成功率可降低售后反馈量",
            ],
        }
    )


@admin_bp.get("/operator/device/groups")
@require_admin("super", "operator")
def device_groups():
    devices = device_admin_rows()
    groups = {}
    for device in devices:
        key = device.get("modelName") or "未知型号"
        group = groups.setdefault(key, {"groupName": key, "deviceCount": 0, "onlineCount": 0, "firmwareVersions": set()})
        group["deviceCount"] += 1
        group["onlineCount"] += 1 if device.get("online") else 0
        group["firmwareVersions"].add(device.get("firmwareVersion") or "-")
    result = [
        {
            **group,
            "firmwareVersions": "、".join(sorted(group["firmwareVersions"])),
            "offlineCount": group["deviceCount"] - group["onlineCount"],
        }
        for group in groups.values()
    ]
    return response_ok({"total": len(result), "list": result})


@admin_bp.get("/operator/device/alerts")
@require_admin("super", "operator")
def device_alerts():
    device = current_device()
    rows = [
        {"alertId": "A-001", "level": "warning", "title": "设备离线过久", "deviceName": device["deviceName"], "status": "open", "createdAt": "2026-05-29 08:12:00"},
        {"alertId": "A-002", "level": "info", "title": "固件升级失败重试", "deviceName": device["deviceName"], "status": "processing", "createdAt": "2026-05-29 09:25:00"},
        {"alertId": "A-003", "level": "normal", "title": "低电量提醒", "deviceName": device["deviceName"], "status": "closed", "createdAt": "2026-05-28 21:30:00"},
    ]
    return response_ok({"total": len(rows), "list": rows})


@admin_bp.get("/operator/device/firmware-packages")
@require_admin("super", "operator")
def firmware_packages():
    device = current_device()
    rows = [
        {"packageId": "FW-105", "version": os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"), "modelName": device["modelName"], "status": "gray", "sizeMb": 42, "uploadedAt": "2026-05-29 09:00:00"},
        {"packageId": "FW-103", "version": device["firmwareVersion"], "modelName": device["modelName"], "status": "stable", "sizeMb": 39, "uploadedAt": "2026-05-18 18:20:00"},
        {"packageId": "FW-100", "version": "1.0.0", "modelName": device["modelName"], "status": "rollback", "sizeMb": 35, "uploadedAt": "2026-05-01 10:00:00"},
    ]
    # 合并管理员后续「上传」入库的固件包
    uploaded = admin_state_section("firmwarePackages", [])
    existing_ids = {row["packageId"] for row in rows}
    for pkg in uploaded:
        if pkg.get("packageId") not in existing_ids:
            rows.insert(0, pkg)
    return response_ok({"total": len(rows), "list": rows})


# 固定生成的、允许上传入库的固件包候选（不接受任意文件，只能从此列表上传）
def firmware_upload_catalog():
    device = current_device()
    model = device["modelName"]
    return [
        {"packageId": "FW-106", "version": "1.0.6", "modelName": model, "channel": "gray", "sizeMb": 44, "checksum": "a1b2c3d4", "releaseNote": "优化语音唤醒灵敏度"},
        {"packageId": "FW-110", "version": "1.1.0", "modelName": model, "channel": "stable", "sizeMb": 47, "checksum": "e5f6a7b8", "releaseNote": "新增多设备组网与音效均衡"},
        {"packageId": "FW-201", "version": "2.0.1-beta", "modelName": model, "channel": "gray", "sizeMb": 51, "checksum": "c9d0e1f2", "releaseNote": "实验版：本地大模型语音助手"},
    ]


@admin_bp.get("/operator/device/firmware-upload-options")
@require_admin("super", "operator")
def firmware_upload_options():
    catalog = firmware_upload_catalog()
    uploaded_ids = {pkg.get("packageId") for pkg in admin_state_section("firmwarePackages", [])}
    options = [{**item, "uploaded": item["packageId"] in uploaded_ids} for item in catalog]
    return response_ok({"total": len(options), "list": options})


@admin_bp.post("/operator/device/firmware-upload")
@require_admin("super", "operator")
def upload_firmware_package():
    body = request.get_json(silent=True) or {}
    package_id = body.get("packageId")

    catalog = {item["packageId"]: item for item in firmware_upload_catalog()}
    if package_id not in catalog:
        return response_error(400, "只能上传系统预置的固件包")

    chosen = catalog[package_id]
    uploaded = list(admin_state_section("firmwarePackages", []))
    if any(pkg.get("packageId") == package_id for pkg in uploaded):
        return response_error(409, f"固件包 {chosen['version']} 已上传，请勿重复上传")

    package = {
        "packageId": chosen["packageId"],
        "version": chosen["version"],
        "modelName": chosen["modelName"],
        "status": chosen["channel"],
        "sizeMb": chosen["sizeMb"],
        "checksum": chosen["checksum"],
        "releaseNote": chosen["releaseNote"],
        "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uploadedBy": g.admin["roleName"],
    }
    uploaded.insert(0, package)
    save_admin_state_section("firmwarePackages", uploaded)
    return response_ok(package, f"固件包 {chosen['version']} 上传成功")


@admin_bp.get("/operator/device/firmware-tasks")
@require_admin("super", "operator")
def firmware_tasks():
    device = current_device()
    tasks = admin_state_section(
        "firmwareTasks",
        [
            {"taskId": "FWU-001", "targetVersion": "1.0.5", "targetScope": "灰度 20%", "status": "processing", "successCount": 18, "failCount": 2, "failureReason": "2 台设备离线", "createdAt": "2026-05-29 09:15:00"},
            {"taskId": "FWU-000", "targetVersion": device["firmwareVersion"], "targetScope": "全部设备", "status": "success", "successCount": 86, "failCount": 0, "failureReason": "-", "createdAt": "2026-05-20 10:30:00"},
        ],
    )
    return response_ok({"total": len(tasks), "list": tasks})


@admin_bp.post("/operator/device/firmware-task")
@require_admin("super", "operator")
def create_firmware_task():
    body = request.get_json(silent=True) or {}
    tasks = admin_state_section("firmwareTasks", [])
    task = {
        "taskId": f"FWU-{datetime.now().strftime('%m%d%H%M%S')}",
        "targetVersion": body.get("targetVersion") or os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"),
        "targetScope": body.get("targetScope") or "选中设备",
        "status": "pending",
        "successCount": 0,
        "failCount": 0,
        "failureReason": "-",
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    tasks.insert(0, task)
    save_admin_state_section("firmwareTasks", tasks)
    return response_ok(task, "固件升级任务已创建")


@admin_bp.post("/operator/feedback/handle")
@require_admin("super", "operator")
def handle_feedback():
    body = request.get_json(silent=True) or {}
    return response_ok(
        {
            "feedbackId": body.get("feedbackId"),
            "status": body.get("status") or "processed",
            "handlerName": g.admin["roleName"],
            "handledAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remark": body.get("remark") or "已记录处理意见",
        },
        "反馈处理状态已更新",
    )


@admin_compat_bp.get("/api/operator/market/profile")
@require_admin("super", "market", "operator")
def legacy_operator_market_profile():
    admin = g.admin if g.admin["role"] in ("market_admin", "operator_admin") else DEFAULT_ADMINS["market"]
    return response_ok(public_admin_info(admin, include_private=True))
