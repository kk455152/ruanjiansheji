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

from api_pkg.common import json_safe, load_state, mongo_many, mongo_one, mysql_all, mysql_exec, mysql_one, save_state


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

ROLE_NAME_MAP = {
    "super_admin": "超级管理员",
    "market_admin": "市场分析管理员",
    "operator_admin": "普通管理员",
    "boss": "老板",
}


def admin_accounts_overlay():
    """读取持久化的管理员账号覆盖层（只读，不触发写盘）。"""
    state = load_state()
    overlay = (state.get("admin_console", {}) or {}).get("adminAccounts") or {}
    return {
        "accounts": overlay.get("accounts", {}) or {},
        "deleted": list(overlay.get("deleted", []) or []),
    }


def all_admins():
    """DEFAULT_ADMINS 叠加持久化覆盖层，得到当前全部管理员账号。"""
    db_rows = mysql_all(
        """
        SELECT admin_id, username, password_hash, role, real_name, job_no,
               position, phone, email, wechat_open_id, status, last_login_at,
               is_super_admin
        FROM admin_user
        WHERE COALESCE(status, 1) <> 0
        ORDER BY admin_id ASC
        """
    )
    if db_rows:
        result = {}
        for row in db_rows:
            role = row.get("role") or ("super_admin" if row.get("is_super_admin") else "operator_admin")
            username = row.get("username")
            if not username:
                continue
            result[username] = {
                "adminId": row.get("admin_id"),
                "username": username,
                "password": row.get("password_hash") or "",
                "role": role,
                "roleName": ROLE_NAME_MAP.get(role, role),
                "realName": row.get("real_name") or username,
                "jobNo": row.get("job_no") or "-",
                "position": row.get("position") or ROLE_NAME_MAP.get(role, role),
                "phone": row.get("phone") or "",
                "email": row.get("email") or "",
                "wechatOpenId": row.get("wechat_open_id") or "",
                "status": "enabled" if str(row.get("status")) not in ("0", "disabled") else "disabled",
                "lastLoginAt": str(row.get("last_login_at") or ""),
            }
        if result:
            return result

    overlay = admin_accounts_overlay()
    result = {username: dict(record) for username, record in DEFAULT_ADMINS.items()}
    for username in overlay["deleted"]:
        result.pop(username, None)
    for username, record in overlay["accounts"].items():
        if username in result:
            result[username].update(record)
        else:
            result[username] = dict(record)
    return result


def find_admin(username):
    return all_admins().get(username)


def verify_admin_password(raw_password, stored_password):
    stored = str(stored_password or "")
    raw = str(raw_password or "")
    if hmac.compare_digest(raw, stored):
        return True
    if len(stored) == 64:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if hmac.compare_digest(digest, stored):
            return True
    md5_digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return hmac.compare_digest(md5_digest, stored)


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


def mask_phone(phone):
    text = str(phone or "").strip()
    if len(text) >= 11:
        return text[:3] + "****" + text[-4:]
    if len(text) >= 7:
        return text[:3] + "****" + text[-2:]
    return text or "—"


def fmt_dt(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


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
        admin = find_admin(payload.get("username"))
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
    if os.environ.get("ADMIN_REALTIME_DB", "true").lower() in ("1", "true", "yes", "on"):
        return loader()

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
            return 0
        return _int(next(iter(row.values())), 0)

    return cached_value(("count", sql, tuple(params), fallback), loader)


def quote_identifier(name):
    return "`" + str(name).replace("`", "``") + "`"


def cached_mysql_all(sql, params=(), fallback=None):
    return cached_value(
        ("all", sql, tuple(params)),
        lambda: mysql_all(sql, params) or (fallback or []),
    )


def _config_default():
    return {
        "systemName": "声盒 Mini 后台管理系统",
        "logoText": "Mini",
        "defaultTheme": "green",
        "uploadLimitMb": 100,
        "apiTimeoutSeconds": 15,
        "dataRetentionDays": 365,
        "tokenExpireSeconds": TOKEN_EXPIRE_SECONDS,
        "wechatLoginEnabled": True,
        "apiErrorRate": 0.004,
        "storageUsage": "62%",
    }


def _typed_config_value(value, config_type=None):
    text = "" if value is None else str(value)
    ctype = str(config_type or "").lower()
    if ctype in ("bool", "boolean"):
        return text.lower() in ("1", "true", "yes", "on", "enabled")
    if ctype in ("int", "integer", "number"):
        return _int(text, 0)
    if ctype in ("float", "decimal"):
        return _float(text, 0.0)
    return text


def _infer_config_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "string"


def _system_config_values(defaults=None):
    data = dict(defaults or {})
    rows = mysql_all(
        """
        SELECT config_key, config_value, config_type
        FROM system_config
        WHERE COALESCE(editable, 1) <> 0
        ORDER BY config_id ASC
        """
    )
    for row in rows:
        key = row.get("config_key")
        if not key:
            continue
        data[key] = _typed_config_value(row.get("config_value"), row.get("config_type"))
    return data


def _system_config_group_rows(group_name, limit=50):
    return mysql_all(
        """
        SELECT config_id, config_key, config_value, config_type, config_group,
               config_name, description, created_at, updated_at
        FROM system_config
        WHERE config_group=%s
        ORDER BY updated_at DESC, created_at DESC, config_id DESC
        LIMIT %s
        """,
        (group_name, limit),
    )


def _save_system_config_value(key, value, group_name="system", config_name=None):
    config_type = _infer_config_type(value)
    stored_value = "1" if isinstance(value, bool) and value else "0" if isinstance(value, bool) else str(value)
    updated = mysql_exec(
        """
        UPDATE system_config
        SET config_value=%s, config_type=%s, config_group=%s,
            config_name=COALESCE(NULLIF(%s, ''), config_name),
            updated_at=NOW()
        WHERE config_key=%s
        """,
        (stored_value, config_type, group_name, config_name or "", key),
    )
    if updated:
        return True
    inserted = mysql_exec(
        """
        INSERT INTO system_config
            (config_key, config_value, config_type, config_group, config_name, editable, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())
        """,
        (key, stored_value, config_type, group_name, config_name or key),
    )
    return bool(inserted)


def _latest_firmware_version(default_version):
    row = mysql_one(
        """
        SELECT version
        FROM device_firmware
        WHERE COALESCE(status, '') NOT IN ('deleted', 'disabled')
        ORDER BY COALESCE(version_code, 0) DESC, updated_at DESC, created_at DESC, firmware_id DESC
        LIMIT 1
        """
    )
    return str(row.get("version") or default_version) if row else default_version


def device_runtime_doc(device_id):
    if not device_id:
        return {}
    queries = [
        {"device_id": str(device_id)},
        {"deviceId": str(device_id)},
    ]
    try:
        int_id = int(device_id)
        queries.append({"device_id": int_id})
    except Exception:
        pass
    for query in queries:
        doc = mongo_one(
            ["device_runtime", "runtime_state", "device_status", "device_metrics"],
            query,
            sort=[("updated_at", -1), ("_id", -1)],
        )
        if doc:
            metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else doc
            return metrics or {}
    return {}


def current_device(device_id=None):
    params = ()
    where = ""
    if device_id:
        where = "WHERE CAST(d.device_id AS CHAR)=%s OR d.device_number=%s"
        params = (str(device_id), str(device_id))
    row = mysql_one(
        f"""
        SELECT
            d.device_id,
            d.device_number,
            d.model_name,
            d.status,
            d.last_active,
            d.firmware_version,
            b.custom_device_name,
            b.current_network,
            u.username AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        {where}
        ORDER BY d.device_id ASC
        LIMIT 1
        """,
        params,
    )
    if row:
        runtime = device_runtime_doc(row.get("device_id"))

        def runtime_int(*names, default=0):
            for name in names:
                if runtime.get(name) is not None:
                    try:
                        return int(runtime.get(name))
                    except Exception:
                        return default
            return default

        return {
            "deviceId": str(row.get("device_id")),
            "deviceSn": row.get("device_number") or "",
            "deviceName": row.get("custom_device_name") or row.get("device_number") or "",
            "modelName": row.get("model_name") or "",
            "ownerName": row.get("owner_name") or "",
            "online": bool(row.get("status")),
            "firmwareVersion": row.get("firmware_version") or "",
            "lastOnlineAt": str(row.get("last_active") or ""),
            "volume": runtime_int("volume", default=0),
            "battery": runtime_int("battery", "battery_level", default=0),
            "signalStrength": runtime.get("signal_strength", runtime.get("signalStrength", "")),
            "currentNetwork": row.get("current_network") or runtime.get("current_network") or runtime.get("networkType") or "",
            "createdAt": "",
        }

    return {
        "deviceId": "",
        "deviceSn": "",
        "deviceName": "",
        "modelName": "",
        "ownerName": "",
        "online": False,
        "firmwareVersion": "",
        "lastOnlineAt": "",
        "volume": 0,
        "battery": 0,
        "signalStrength": "",
        "currentNetwork": "",
        "createdAt": "",
    }


def platform_text(value):
    text = str(value or "").strip()
    mapping = {
        "netease": "网易云音乐",
        "netease_cloud": "网易云音乐",
        "qq": "QQ音乐",
        "qq_music": "QQ音乐",
        "wechat": "微信小程序",
        "mini_program": "微信小程序",
        "local": "本地曲库",
    }
    return mapping.get(text, text or "未知来源")


def service_text(value):
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    if not parts:
        return "未知平台"
    return "、".join(platform_text(part) for part in parts)


def latest_song_row(device_id=None):
    rows = []
    if device_id:
        rows = mysql_all(
            """
            SELECT ph.created_at, COALESCE(ph.source_platform, mm.platform) AS source_platform,
                   mm.song_title, mm.artist
            FROM play_history ph
            LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
            WHERE CAST(ph.device_id AS CHAR)=%s
            ORDER BY ph.created_at DESC
            LIMIT 1
            """,
            (str(device_id),),
        )
        return rows[0] if rows else {}
    if not rows:
        rows = mysql_all(
            """
            SELECT ph.created_at, COALESCE(ph.source_platform, mm.platform) AS source_platform,
                   mm.song_title, mm.artist
            FROM play_history ph
            LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
            ORDER BY ph.created_at DESC
            LIMIT 1
            """
        )
    return rows[0] if rows else {}


def fallback_series(metric_type, dimension):
    metric_columns = {
        "user": "new_user_count",
        "device": "new_device_count",
        "sales": "total_sales_amount",
        "retention": "active_user_count",
    }
    column = metric_columns.get(metric_type, "new_user_count")
    buckets = {
        "week": ("DATE_FORMAT(stat_date, '%%x-W%%v')", 8),
        "month": ("DATE_FORMAT(stat_date, '%%Y-%%m')", 12),
        "year": ("DATE_FORMAT(stat_date, '%%Y')", 5),
        "day": ("DATE_FORMAT(stat_date, '%%Y-%%m-%%d')", 12),
    }
    bucket_sql, limit = buckets.get(dimension, buckets["day"])
    rows = mysql_all(
        f"""
        SELECT {bucket_sql} AS label, SUM({column}) AS value
        FROM daily_stats
        GROUP BY label
        ORDER BY label DESC
        LIMIT {limit}
        """
    )
    return [
        {"date": row.get("label"), "value": _float(row.get("value"), 0)}
        for row in reversed(rows or [])
    ]


def distribution_data(kind):
    if kind == "age":
        rows = mysql_all(
            """
            SELECT COALESCE(age_range, 'unknown') AS label, COUNT(*) AS count
            FROM user_profile
            GROUP BY COALESCE(age_range, 'unknown')
            ORDER BY count DESC
            """
        )
        return [{"ageRange": row.get("label"), "count": _int(row.get("count"), 0)} for row in rows]
    if kind == "region":
        rows = mysql_all(
            """
            SELECT COALESCE(province_name, 'unknown') AS label, COUNT(*) AS count
            FROM user_profile
            GROUP BY COALESCE(province_name, 'unknown')
            ORDER BY count DESC
            """
        )
        return [{"regionName": row.get("label"), "count": _int(row.get("count"), 0)} for row in rows]
    if kind == "activity":
        rows = mysql_all(
            """
            SELECT COALESCE(active_level, 'unknown') AS level, COUNT(*) AS count
            FROM user_profile
            GROUP BY COALESCE(active_level, 'unknown')
            ORDER BY count DESC
            """
        )
        return [{"level": row.get("level"), "levelName": row.get("level"), "count": _int(row.get("count"), 0)} for row in rows]
    rows = mysql_all(
        """
        SELECT COALESCE(bound_platforms, 'unknown') AS service, COUNT(*) AS count
        FROM user_profile
        GROUP BY COALESCE(bound_platforms, 'unknown')
        ORDER BY count DESC
        """
    )
    return [{"service": row.get("service"), "serviceName": service_text(row.get("service")), "count": _int(row.get("count"), 0)} for row in rows]


def heatmap(kind):
    rows = mysql_all(
        """
        SELECT region_code, region_name, sales_amount, order_count,
               user_count, active_user_count
        FROM region_stats_daily
        WHERE stat_date = (SELECT MAX(stat_date) FROM region_stats_daily)
        ORDER BY sales_amount DESC, user_count DESC
        LIMIT 20
        """
    )
    if kind == "sales":
        return [
            {
                "regionCode": row.get("region_code"),
                "regionName": row.get("region_name"),
                "salesAmount": _float(row.get("sales_amount"), 0),
                "orderCount": _int(row.get("order_count"), 0),
            }
            for row in rows
        ]
    return [
        {
            "regionCode": row.get("region_code"),
            "regionName": row.get("region_name"),
            "userCount": _int(row.get("user_count"), 0),
            "activeUserCount": _int(row.get("active_user_count"), 0),
        }
        for row in rows
    ]


def feedback_rows():
    rows = cached_mysql_all(
        """
        SELECT f.feedback_id, f.feedback_no, f.user_id, f.title, f.content,
               f.feedback_type, f.status, f.priority, f.star_rating, f.rating_tags,
               f.device_info, f.handler_name, f.reply_content, f.handled_at,
               f.closed_at, f.created_at, u.username, u.nickname, u.avatar,
               u.phone, u.email, u.status AS user_status, u.created_at AS user_created_at,
               u.last_login_at, f.contact
        FROM user_feedback f
        LEFT JOIN `user` u ON u.user_id = f.user_id
        ORDER BY f.feedback_id DESC
        LIMIT 50
        """
    )
    if rows:
        type_text = {
            "bug": "问题反馈",
            "suggestion": "功能建议",
            "complaint": "投诉",
            "praise": "表扬建议",
        }
        status_text = {
            "open": "待处理",
            "pending": "待处理",
            "processing": "处理中",
            "processed": "已处理",
            "closed": "已关闭",
        }
        priority_text = {
            "high": "高",
            "normal": "普通",
            "low": "低",
        }
        result = []
        for row in rows:
            feedback_id = str(row.get("feedback_no") or row.get("feedback_id"))
            feedback_type = row.get("feedback_type") or "suggestion"
            status = row.get("status") or "open"
            priority = row.get("priority") or "normal"
            rating = _int(row.get("star_rating"), 0)
            result.append({
                "feedbackId": feedback_id,
                "userId": row.get("user_id"),
                "nickname": row.get("nickname") or row.get("username") or "用户",
                "avatar": row.get("avatar") or f"https://example.com/avatar/{row.get('user_id') or 0}.png",
                "phone": mask_phone(row.get("phone") or ""),
                "feedbackType": feedback_type,
                "feedbackTypeText": type_text.get(feedback_type, feedback_type),
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "images": [],
                "contact": row.get("contact") or row.get("phone") or "",
                "status": status,
                "statusText": status_text.get(status, status),
                "priority": priority,
                "priorityText": priority_text.get(priority, priority),
                "rating": rating,
                "ratingText": f"{rating}星" if rating else "未评分",
                "ratingTags": row.get("rating_tags") or "",
                "deviceInfo": row.get("device_info") or "",
                "handlerId": None,
                "handlerName": row.get("handler_name"),
                "replyContent": row.get("reply_content"),
                "handledAt": fmt_dt(row.get("handled_at")),
                "closedAt": fmt_dt(row.get("closed_at")),
                "createdAt": fmt_dt(row.get("created_at")),
                "email": row.get("email") or "",
                "registerTime": fmt_dt(row.get("user_created_at")),
                "lastLoginAt": fmt_dt(row.get("last_login_at")),
                "userStatus": row.get("user_status") or "normal",
            })
        return result

    return []


def feedback_detail(feedback_id):
    rows = feedback_rows()
    if not rows:
        return {}
    row = next((item for item in rows if str(item["feedbackId"]) == str(feedback_id)), rows[0])
    return {
        "feedbackId": row["feedbackId"],
        "userInfo": {
            "userId": row["userId"],
            "nickname": row["nickname"],
            "avatar": row["avatar"],
            "phone": row["phone"],
            "email": row.get("email") or "",
            "registerTime": row.get("registerTime") or "",
            "lastLoginAt": row.get("lastLoginAt") or "",
            "userStatus": row.get("userStatus") or "normal",
            "userStatusText": "正常" if row.get("userStatus") != "inactive" else "停用",
        },
        "feedbackInfo": {
            "feedbackType": row["feedbackType"],
            "feedbackTypeText": row["feedbackTypeText"],
            "title": row.get("title") or "",
            "content": row["content"],
            "images": row["images"],
            "contact": row["contact"],
            "source": "mini_program",
            "sourceText": "小程序",
            "appVersion": "1.2.5",
            "deviceInfo": row.get("deviceInfo") or "",
        },
        "processInfo": {
            "status": row["status"],
            "statusText": row["statusText"],
            "priority": row["priority"],
            "priorityText": row["priorityText"],
            "rating": row.get("rating", 4),
            "ratingText": row.get("ratingText", "4星"),
            "ratingTags": row.get("ratingTags") or "",
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

    admin = find_admin(username)
    if not admin or not verify_admin_password(password, admin.get("password", "")):
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
    total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=0)
    new_count = count_sql("SELECT COUNT(*) AS c FROM `user` WHERE created_at >= CURDATE()", fallback=0)
    return response_ok({"userCount": total, "newUserCount": new_count})


@admin_bp.get("/super/overview/device-count")
@require_admin("super", "boss")
def device_count():
    total = count_sql("SELECT COUNT(*) AS c FROM device", fallback=0)
    online = count_sql("SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0) = 1", fallback=0)
    return response_ok({"deviceCount": total, "onlineDeviceCount": online, "offlineDeviceCount": max(total - online, 0)})


@admin_bp.get("/super/overview/sales-amount")
@require_admin("super", "boss")
def sales_amount():
    row = mysql_one(
        """
        SELECT COALESCE(SUM(pay_amount), 0) AS sales_amount,
               COUNT(*) AS order_count
        FROM sales_order
        WHERE pay_status IN ('paid', 'success', 'finished')
        """
    ) or {}
    return response_ok({"salesAmount": _float(row.get("sales_amount"), 0), "orderCount": _int(row.get("order_count"), 0)})


@admin_bp.get("/super/overview/activity-rate")
@require_admin("super", "boss")
def activity_rate():
    total = count_sql("SELECT COUNT(*) AS c FROM user_profile", fallback=0)
    if not total:
        total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=0)
    active = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level = 'high'", fallback=0)
    return response_ok({"activeUserCount": active, "totalUserCount": total, "activityRate": round(active / max(total, 1), 4)})


@admin_bp.get("/super/trend/growth")
@require_admin("super", "boss")
def growth_trend():
    metric_type = request.args.get("type", "user")
    dimension = request.args.get("dimension", "day")
    metric_columns = {
        "user": "new_user_count",
        "device": "new_device_count",
        "sales": "total_sales_amount",
        "retention": "active_user_count",
    }
    column = metric_columns.get(metric_type, "new_user_count")
    rows = mysql_all(
        f"""
        SELECT stat_date, {quote_identifier(column)} AS value
        FROM daily_stats
        ORDER BY stat_date DESC
        LIMIT 14
        """
    )
    data = [
        {"date": str(row.get("stat_date")), "value": _float(row.get("value"), 0) if metric_type == "sales" else _int(row.get("value"), 0)}
        for row in reversed(rows)
    ]
    return response_ok({"type": metric_type, "dimension": dimension, "list": data})


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
    total = count_sql("SELECT COUNT(*) AS c FROM user_profile", fallback=0)
    if not total:
        total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=0)
    high_active = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level = 'high'", fallback=0)
    return response_ok({"normalUserCount": max(total - high_active, 0)})


@admin_bp.get("/super/user-value/high-active-users")
@admin_bp.get("/market/user-value/high-active-users")
@require_admin("super", "market", "boss")
def high_active_users():
    count = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level = 'high'", fallback=0)
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
    feedback_id = request.args.get("feedbackId", "")
    return response_ok(feedback_detail(feedback_id), "获取成功")


@admin_bp.get("/market/top-songs")
@require_admin("super", "market", "boss")
def top_songs():
    ranking_rows = mysql_all(
        """
        SELECT ranking_date, rank_no, target_id, target_name, target_category,
               metric_value, metric_unit, scope_type
        FROM hot_ranking_daily
        WHERE ranking_type = 'song'
          AND ranking_date = (
              SELECT MAX(ranking_date)
              FROM hot_ranking_daily
              WHERE ranking_type = 'song'
          )
        ORDER BY metric_value DESC, rank_no ASC, target_name ASC
        LIMIT 10
        """
    )
    if ranking_rows:
        return response_ok({
            "list": [
                {
                    "rank": index + 1,
                    "songName": row.get("target_name") or "未知歌曲",
                    "artist": row.get("target_category") or "未知歌手",
                    "platform": row.get("scope_type") or "global",
                    "playCount": _int(row.get("metric_value"), 0),
                    "userCount": 0,
                    "rankingDate": str(row.get("ranking_date")),
                    "targetId": row.get("target_id"),
                    "metricUnit": row.get("metric_unit") or "plays",
                }
                for index, row in enumerate(ranking_rows)
            ]
        })

    return response_ok({"list": []})


@admin_bp.get("/market/retention/device-purchase")
@require_admin("super", "market")
def retention_device_purchase():
    rows = mysql_all(
        """
        SELECT DATE(created_at) AS date_value, COUNT(DISTINCT user_id) AS purchases
        FROM sales_order
        WHERE pay_status IN ('paid', 'success', 'finished')
        GROUP BY DATE(created_at)
        ORDER BY date_value DESC
        LIMIT 7
        """
    )
    data = []
    for row in reversed(rows or []):
        date_value = row.get("date_value")
        purchases = _int(row.get("purchases"), 0)
        if not purchases:
            continue
        day1 = count_sql(
            "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at) >= DATE_ADD(%s, INTERVAL 1 DAY)",
            (date_value,),
        )
        day7 = count_sql(
            "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at) >= DATE_ADD(%s, INTERVAL 7 DAY)",
            (date_value,),
        )
        day30 = count_sql(
            "SELECT COUNT(DISTINCT user_id) AS c FROM play_history WHERE DATE(created_at) >= DATE_ADD(%s, INTERVAL 30 DAY)",
            (date_value,),
        )
        data.append({
            "date": str(date_value),
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
    latest = _latest_firmware_version(os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"))
    return response_ok({
        "deviceId": device["deviceId"],
        "deviceName": device["deviceName"],
        "modelName": device["modelName"],
        "currentVersion": device["firmwareVersion"],
        "latestVersion": latest,
        "needUpdate": device["firmwareVersion"] != latest,
    })


@admin_bp.post("/operator/device/update-firmware")
@require_admin("super", "operator")
def update_firmware():
    body = request.get_json(silent=True) or {}
    device = current_device()
    target_version = body.get("targetVersion") or _latest_firmware_version(os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"))
    task_no = f"FWU-{datetime.now().strftime('%m%d%H%M%S')}"
    inserted = mysql_exec(
        """
        INSERT INTO device_firmware_update_task
            (task_no, device_id, current_version, target_version, status, progress, fail_reason, operator_name, started_at, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'pending', 0, '-', %s, NOW(), NOW(), NOW())
        """,
        (task_no, body.get("deviceId") or device["deviceId"], device["firmwareVersion"], target_version, g.admin.get("realName") or g.admin.get("username")),
        fetch_last_id=True,
    )
    return response_ok(
        {
            "taskId": inserted or task_no,
            "deviceId": body.get("deviceId") or device["deviceId"],
            "targetVersion": target_version,
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
            d.device_number,
            d.model_name,
            d.status,
            d.firmware_version,
            d.last_active,
            b.user_id,
            b.custom_device_name,
            COALESCE(p.nickname, u.nickname, u.username) AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        LEFT JOIN user_profile p ON p.user_id = u.user_id
        ORDER BY d.device_id ASC
        LIMIT 100
        """
    )
    if rows:
        devices = [
            {
                "deviceId": str(row.get("device_id")),
                "deviceSn": row.get("device_number") or "",
                "deviceName": row.get("custom_device_name") or row.get("device_number") or "",
                "modelName": row.get("model_name") or "",
                "ownerName": row.get("owner_name") or "",
                "userId": str(row.get("user_id")) if row.get("user_id") is not None else "",
                "online": bool(row.get("status")),
                "firmwareVersion": row.get("firmware_version") or "",
                "lastOnlineAt": str(row.get("last_active") or ""),
            }
            for row in rows
        ]
    else:
        devices = []

    return response_ok({"total": len(devices), "list": devices})


@admin_bp.get("/operator/device/detail")
@require_admin("super", "operator")
def operator_device_detail():
    return response_ok(current_device())


@admin_bp.get("/operator/device/bound-user")
@require_admin("super", "operator")
def operator_device_bound_user():
    device_id = str(request.args.get("deviceId") or "").strip()
    row = None
    if device_id.isdigit():
        row = mysql_one(
            """
            SELECT
                u.user_id,
                u.username,
                u.phone,
                u.email,
                u.status,
                u.created_at AS register_time,
                u.last_login_at,
                COALESCE(p.nickname, u.nickname) AS nickname,
                p.gender,
                p.age,
                p.age_range,
                p.province_name,
                p.city_name,
                p.active_level,
                p.value_level,
                d.device_number,
                b.custom_device_name,
                b.default_room,
                b.bind_time
            FROM user_device_binding b
            JOIN `user` u ON u.user_id = b.user_id
            LEFT JOIN user_profile p ON p.user_id = u.user_id
            LEFT JOIN device d ON d.device_id = b.device_id
            WHERE b.device_id = %s
            ORDER BY b.is_primary DESC, b.bind_time ASC
            LIMIT 1
            """,
            (device_id,),
        )

    if row:
        active_map = {"high": "高活跃", "medium": "中活跃", "low": "低活跃"}
        value_map = {"high": "高价值", "normal": "普通", "low": "低价值"}
        status_map = {"active": "正常", "normal": "正常", "frozen": "已冻结", "disabled": "已禁用"}
        gender_map = {"male": "男", "female": "女", "unknown": "未知"}
        active = str(row.get("active_level") or "")
        value = str(row.get("value_level") or "")
        gender = str(row.get("gender") or "")
        status = str(row.get("status") or "")
        data = {
            "userId": str(row.get("user_id")),
            "nickname": row.get("nickname") or row.get("username") or "智能音箱用户",
            "username": row.get("username") or "—",
            "phone": mask_phone(row.get("phone")),
            "email": row.get("email") or "—",
            "gender": gender_map.get(gender, gender or "未知"),
            "age": row.get("age") if row.get("age") is not None else "—",
            "ageRange": row.get("age_range") or "—",
            "region": " · ".join([p for p in [row.get("province_name"), row.get("city_name")] if p]) or "—",
            "activeLevel": active_map.get(active, active or "—"),
            "valueLevel": value_map.get(value, value or "—"),
            "status": status_map.get(status, status or "正常"),
            "registerTime": str(row.get("register_time") or "—"),
            "lastLoginAt": str(row.get("last_login_at") or "—"),
            "deviceSn": row.get("device_number") or "—",
            "deviceName": row.get("custom_device_name") or "客厅音箱",
            "defaultRoom": row.get("default_room") or "—",
            "bindTime": str(row.get("bind_time") or "—"),
        }
        return response_ok(data)

    return response_ok({})


@admin_bp.get("/operator/device/runtime-status")
@require_admin("super", "operator")
def runtime_status():
    requested_device_id = request.args.get("deviceId")
    device = current_device(requested_device_id)
    playing = latest_song_row(device["deviceId"] or requested_device_id)
    return response_ok({
        "deviceId": requested_device_id or device["deviceId"],
        "online": device["online"],
        "battery": device["battery"],
        "volume": device["volume"],
        "currentSong": playing.get("song_title") or "",
        "currentArtist": playing.get("artist") or "",
        "lastHeartbeat": device.get("lastOnlineAt") or "",
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
    rows = mysql_all(
        """
        SELECT log_id, device_id, device_name, log_type, content, created_at
        FROM device_log
        ORDER BY created_at DESC, log_id DESC
        LIMIT 100
        """
    )
    if rows:
        result = [
            {
                "logId": row.get("log_id"),
                "deviceId": str(row.get("device_id") or ""),
                "deviceName": row.get("device_name") or "",
                "logType": row.get("log_type") or "",
                "content": row.get("content") or "",
                "createdAt": str(row.get("created_at") or ""),
            }
            for row in rows
        ]
        return response_ok({"total": len(result), "list": result})

    return response_ok({"total": 0, "list": []})


@admin_bp.get("/operator/device/log-detail")
@require_admin("super", "operator")
def device_log_detail():
    log_id = request.args.get("logId")
    row = None
    if log_id:
        row = mysql_one(
            """
            SELECT log_id, device_id, device_name, log_type, log_level, title, content,
                   event_code, online_status, ip_address, network_type, created_at
            FROM device_log
            WHERE CAST(log_id AS CHAR)=%s
            LIMIT 1
            """,
            (str(log_id),),
        )
    if not row:
        return response_ok({})

    return response_ok({
        "logId": row.get("log_id"),
        "deviceId": str(row.get("device_id") or ""),
        "deviceSn": "",
        "deviceName": row.get("device_name") or "",
        "deviceType": "",
        "deviceTypeText": "",
        "deviceModel": "",
        "logType": row.get("log_type") or "",
        "logTypeText": row.get("log_type") or "",
        "logLevel": row.get("log_level") or "",
        "logLevelText": row.get("log_level") or "",
        "title": row.get("title") or row.get("content") or "",
        "content": row.get("content") or "",
        "eventCode": row.get("event_code") or "",
        "traceId": "",
        "taskId": "",
        "firmwareVersion": "",
        "onlineStatus": row.get("online_status") or "",
        "onlineStatusText": row.get("online_status") or "",
        "ipAddress": row.get("ip_address") or "",
        "networkType": row.get("network_type") or "",
        "location": "",
        "extra": {},
        "stackTrace": None,
        "requestInfo": {},
        "createdAt": fmt_dt(row.get("created_at")),
    })


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
        FROM daily_stats
        ORDER BY stat_date DESC
        LIMIT {limit}
        """
    )
    if rows:
        return list(reversed(rows))

    return []


def admin_users_data():
    rows = cached_mysql_all(
        """
        SELECT u.user_id, u.username, COALESCE(p.nickname, u.nickname, u.username) AS display_name,
               u.phone, u.created_at, u.last_login_at
        FROM `user` u
        LEFT JOIN user_profile p ON p.user_id=u.user_id
        ORDER BY u.user_id ASC
        LIMIT 20
        """
    )
    users = [
        {
            "adminId": admin["adminId"],
            "username": admin["username"],
            "realName": admin["realName"],
            "role": admin["role"],
            "roleName": admin.get("roleName") or ROLE_NAME_MAP.get(admin["role"], admin["role"]),
            "jobNo": admin.get("jobNo") or "-",
            "position": admin.get("position") or admin.get("roleName") or "",
            "phone": admin.get("phone"),
            "email": admin.get("email"),
            "status": admin.get("status", "enabled"),
            "lastLoginAt": admin.get("lastLoginAt", "2026-05-29 09:30:00"),
            "editable": True,
        }
        for admin in all_admins().values()
    ]
    for row in rows[:6]:
        users.append(
            {
                "adminId": f"user-{row.get('user_id')}",
                "username": row.get("username") or f"user{row.get('user_id')}",
                "realName": row.get("display_name") or row.get("username") or "业务用户",
                "role": "customer",
                "roleName": "绑定用户",
                "jobNo": "-",
                "position": "智能音箱用户",
                "phone": row.get("phone"),
                "email": "",
                "status": "readonly",
                "lastLoginAt": str(row.get("last_login_at") or row.get("created_at") or "-"),
                "editable": False,
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
            COALESCE(p.nickname, u.nickname, u.username) AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        LEFT JOIN user_profile p ON p.user_id = u.user_id
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

    return []


def role_rows():
    db_rows = _system_config_group_rows("admin_role", 20)
    if db_rows:
        rows = []
        for row in db_rows:
            role = row.get("config_key")
            if not role:
                continue
            permissions = [
                item.strip()
                for item in str(row.get("description") or "").split(",")
                if item.strip() in PERMISSION_CATALOG
            ]
            rows.append(
                {
                    "role": role,
                    "roleName": row.get("config_name") or role,
                    "description": row.get("config_value") or "",
                    "permissions": permissions,
                    "userCount": count_sql("SELECT COUNT(*) AS c FROM admin_user WHERE role=%s", (role,), fallback=0),
                }
            )
        if rows:
            return rows

    db_roles = mysql_all(
        """
        SELECT role, COUNT(*) AS user_count
        FROM admin_user
        WHERE role IS NOT NULL AND role <> ''
        GROUP BY role
        ORDER BY role ASC
        """
    )
    if db_roles:
        return [
            {
                "role": row.get("role"),
                "roleName": row.get("role"),
                "description": "",
                "permissions": [],
                "userCount": _int(row.get("user_count"), 0),
            }
            for row in db_roles
        ]

    return []

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
    defaults = admin_state_section("systemConfig", _config_default())
    return response_ok(_system_config_values(defaults))




@admin_bp.post("/super/system/config")
@require_admin("super")
def update_system_config():
    body = request.get_json(silent=True) or {}
    saved_to_db = False
    for key, value in body.items():
        if value is None:
            continue
        saved_to_db = _save_system_config_value(key, value, "system", key) or saved_to_db

    current = admin_state_section("systemConfig", {})
    current.update({key: value for key, value in body.items() if value is not None})
    fallback = save_admin_state_section("systemConfig", current)
    return response_ok(_system_config_values(fallback) if saved_to_db else fallback, "system config saved")

    current = admin_state_section("systemConfig", {})
    current.update({key: value for key, value in body.items() if value is not None})
    return response_ok(save_admin_state_section("systemConfig", current), "系统配置已保存")


@admin_bp.get("/super/users")
@require_admin("super")
def admin_users():
    users = admin_users_data()
    return response_ok({"total": len(users), "list": users})


def _save_admin_overlay(overlay):
    save_admin_state_section("adminAccounts", overlay)


def _next_admin_id(admins):
    ids = [int(a["adminId"]) for a in admins.values() if str(a.get("adminId", "")).isdigit()]
    return (max(ids) + 1) if ids else 1


def _validate_role(role):
    return role if role in ROLE_NAME_MAP else None


@admin_bp.post("/super/users/create")
@require_admin("super")
def admin_user_create():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()
    role = _validate_role(str(body.get("role", "")).strip())
    real_name = str(body.get("realName", "")).strip() or username

    if not username or not password:
        return response_error(400, "创建失败", "用户名和密码不能为空。")
    if not role:
        return response_error(400, "创建失败", "请选择有效的角色。")
    if find_admin(username):
        return response_error(409, "创建失败", "该用户名已存在。")

    overlay = admin_accounts_overlay()
    accounts = dict(overlay["accounts"])
    deleted = [u for u in overlay["deleted"] if u != username]
    record = {
        "adminId": _next_admin_id(all_admins()),
        "username": username,
        "password": password,
        "role": role,
        "roleName": ROLE_NAME_MAP[role],
        "realName": real_name,
        "jobNo": str(body.get("jobNo", "")).strip() or "-",
        "position": str(body.get("position", "")).strip() or ROLE_NAME_MAP[role],
        "phone": str(body.get("phone", "")).strip(),
        "email": str(body.get("email", "")).strip(),
        "status": "enabled",
    }
    accounts[username] = record
    _save_admin_overlay({"accounts": accounts, "deleted": deleted})
    return response_ok(public_admin_info(record, include_private=True), "账号已创建")


@admin_bp.post("/super/users/update")
@require_admin("super")
def admin_user_update():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    admin = find_admin(username)
    if not admin:
        return response_error(404, "更新失败", "账号不存在。")

    new_password = str(body.get("password", "")).strip()
    new_role = str(body.get("role", "")).strip()
    if new_role:
        if not _validate_role(new_role):
            return response_error(400, "更新失败", "请选择有效的角色。")
        # 防止移除最后一个超级管理员
        if admin.get("role") == "super_admin" and new_role != "super_admin":
            supers = [a for a in all_admins().values() if a.get("role") == "super_admin"]
            if len(supers) <= 1:
                return response_error(400, "更新失败", "至少需保留一个超级管理员。")

    overlay = admin_accounts_overlay()
    accounts = dict(overlay["accounts"])
    record = dict(accounts.get(username) or admin)
    record["username"] = username
    if new_password:
        record["password"] = new_password
    if new_role:
        record["role"] = new_role
        record["roleName"] = ROLE_NAME_MAP[new_role]
    for key in ("realName", "phone", "email", "jobNo", "position"):
        if key in body and body.get(key) is not None:
            record[key] = str(body.get(key)).strip()
    accounts[username] = record
    _save_admin_overlay({"accounts": accounts, "deleted": overlay["deleted"]})
    return response_ok(public_admin_info(record, include_private=True), "账号已更新")


@admin_bp.post("/super/users/delete")
@require_admin("super")
def admin_user_delete():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    admin = find_admin(username)
    if not admin:
        return response_error(404, "删除失败", "账号不存在。")
    if username == g.admin.get("username"):
        return response_error(400, "删除失败", "不能删除当前登录的账号。")
    if admin.get("role") == "super_admin":
        supers = [a for a in all_admins().values() if a.get("role") == "super_admin"]
        if len(supers) <= 1:
            return response_error(400, "删除失败", "至少需保留一个超级管理员。")

    overlay = admin_accounts_overlay()
    accounts = {u: r for u, r in overlay["accounts"].items() if u != username}
    deleted = list(overlay["deleted"])
    if username in DEFAULT_ADMINS and username not in deleted:
        deleted.append(username)
    _save_admin_overlay({"accounts": accounts, "deleted": deleted})
    return response_ok(None, "账号已删除")

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
    db_rows = mysql_all(
        """
        SELECT log_id, action, module, operation_name, path, request_method,
               ip_address, result_status, error_message, created_at
        FROM admin_operation_log
        ORDER BY created_at DESC, log_id DESC
        LIMIT 50
        """
    )
    if db_rows:
        rows = [
            {
                "logId": row.get("log_id"),
                "level": "warning" if row.get("error_message") or str(row.get("result_status") or "").lower() not in ("", "success", "ok") else "info",
                "event": row.get("operation_name") or row.get("action") or row.get("module") or row.get("path") or "-",
                "actor": row.get("module") or row.get("action") or "-",
                "ip": row.get("ip_address") or "-",
                "createdAt": fmt_dt(row.get("created_at")),
            }
            for row in db_rows
        ]
        return response_ok({"total": len(rows), "list": rows})

    return response_ok({"total": 0, "list": []})


@admin_bp.get("/super/monitor")
@require_admin("super", "boss")
def system_monitor():
    total_users = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=0)
    total_devices = count_sql("SELECT COUNT(*) AS c FROM device", fallback=0)
    online_devices = count_sql("SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0) = 1", fallback=0)
    feedback_total = len(feedback_rows())
    monitor_config = _system_config_values({"apiErrorRate": 0, "storageUsage": ""})
    services = [
        {
            "name": row.get("config_name") or row.get("config_key") or "-",
            "status": row.get("config_value") or "",
            "latencyMs": _int(row.get("description"), 0),
        }
        for row in _system_config_group_rows("monitor_service", 20)
    ]
    exceptions = [
        {
            "code": row.get("config_key") or f"EX-{row.get('config_id')}",
            "title": row.get("config_name") or row.get("config_value") or "-",
            "count": _int(row.get("description"), 0),
            "level": row.get("config_type") or "",
        }
        for row in _system_config_group_rows("monitor_exception", 20)
    ]
    return response_ok({
        "services": services,
        "metrics": {
            "totalUsers": total_users,
            "totalDevices": total_devices,
            "onlineDevices": online_devices,
            "feedbackTotal": feedback_total,
            "apiErrorRate": _float(monitor_config.get("apiErrorRate"), 0),
            "storageUsage": str(monitor_config.get("storageUsage") or ""),
        },
        "exceptions": exceptions,
    })

@admin_bp.get("/super/notices")
@require_admin("super")
def admin_notices():
    db_rows = mysql_all(
        """
        SELECT config_id, config_key, config_value, config_type, config_name,
               description, created_at, updated_at
        FROM system_config
        WHERE config_group IN ('notice', 'notices', 'system_notice')
           OR config_key LIKE 'notice.%'
        ORDER BY updated_at DESC, created_at DESC, config_id DESC
        LIMIT 50
        """
    )
    if db_rows:
        notices = [
            {
                "noticeId": row.get("config_key") or f"N-{row.get('config_id')}",
                "title": row.get("config_name") or row.get("config_value") or "-",
                "type": row.get("config_type") or "notice",
                "status": row.get("description") or "published",
                "createdAt": fmt_dt(row.get("created_at") or row.get("updated_at")),
            }
            for row in db_rows
        ]
        return response_ok({"total": len(notices), "list": notices})

    return response_ok({"total": 0, "list": []})



@admin_bp.post("/super/notices")
@require_admin("super")
def create_admin_notice():
    body = request.get_json(silent=True) or {}
    title = body.get("title") or ""
    notice_key = f"notice.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    saved = _save_system_config_value(notice_key, title, "notice", title)
    if saved:
        notice = {
            "noticeId": notice_key,
            "title": title,
            "type": body.get("type") or "notice",
            "status": body.get("status") or "draft",
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        mysql_exec(
            "UPDATE system_config SET config_type=%s, description=%s WHERE config_key=%s",
            (notice["type"], notice["status"], notice_key),
        )
        return response_ok(notice, "notice created")

    return response_error(500, "notice create failed", "system_config is not writable")


@admin_bp.get("/super/decision/summary")
@admin_bp.get("/market/decision/summary")
@require_admin("super", "market")
def decision_summary():
    stats = daily_stats_rows(8)
    latest = stats[-1] if stats else {}
    risk_rows = _system_config_group_rows("decision_risk", 20)
    risks = [
        {
            "name": row.get("config_name") or row.get("config_key") or "-",
            "level": row.get("config_type") or "normal",
            "value": row.get("config_value") or row.get("description") or "-",
        }
        for row in risk_rows
    ]
    return response_ok({
        "cards": [
            {"label": "播放次数", "value": _int(latest.get("total_play_count"), 0), "trend": ""},
            {"label": "活跃用户", "value": _int(latest.get("unique_user_count"), 0), "trend": ""},
            {"label": "活跃设备", "value": _int(latest.get("unique_device_count"), 0), "trend": ""},
            {"label": "平均播放时长", "value": f"{_int(latest.get('avg_play_duration_seconds'), 0)} 秒", "trend": ""},
        ],
        "trend": stats,
        "risks": risks,
    })

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
    rows = mysql_all(
        """
        SELECT stat_date, segment_code, segment_name, user_count, active_user_count,
               avg_play_count, avg_pay_amount, retention_rate
        FROM user_value_segment_daily
        WHERE stat_date = (SELECT MAX(stat_date) FROM user_value_segment_daily)
        ORDER BY user_count DESC, segment_code ASC
        """
    )
    if rows:
        return response_ok({
            "total": len(rows),
            "list": [
                {
                    "name": row.get("segment_name") or row.get("segment_code"),
                    "rule": f"{row.get('stat_date')} / {row.get('segment_code')}",
                    "count": _int(row.get("user_count"), 0),
                    "activeUserCount": _int(row.get("active_user_count"), 0),
                    "avgPlayCount": _float(row.get("avg_play_count"), 0),
                    "avgPayAmount": _float(row.get("avg_pay_amount"), 0),
                    "retentionRate": _float(row.get("retention_rate"), 0),
                    "action": "按日报分群运营",
                }
                for row in rows
            ],
        })

    return response_ok({"total": 0, "list": []})



@admin_bp.get("/market/insights")
@require_admin("super", "market")
def market_insights():
    new_users = count_sql("SELECT COUNT(*) AS c FROM `user` WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")
    bound_users = count_sql("SELECT COUNT(DISTINCT user_id) AS c FROM user_device_binding")
    first_play_users = count_sql("SELECT COUNT(DISTINCT user_id) AS c FROM play_history")
    retained_users = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level = 'high'")
    base = max(new_users, bound_users, first_play_users, retained_users, 1)
    recommendation_rows = _system_config_group_rows("market_recommendation", 20)
    recommendations = [
        row.get("config_value") or row.get("config_name") or row.get("description")
        for row in recommendation_rows
        if row.get("config_value") or row.get("config_name") or row.get("description")
    ]
    return response_ok({
        "funnels": [
            {"label": "新增用户", "value": new_users, "rate": round(new_users / base, 4)},
            {"label": "绑定设备", "value": bound_users, "rate": round(bound_users / base, 4)},
            {"label": "完成首播", "value": first_play_users, "rate": round(first_play_users / base, 4)},
            {"label": "7 日活跃", "value": retained_users, "rate": round(retained_users / base, 4)},
        ],
        "recommendations": recommendations,
    })

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
    db_rows = mysql_all(
        """
        SELECT log_id, log_level, title, content, device_name, online_status, created_at
        FROM device_log
        WHERE COALESCE(log_type, '') IN ('alert', 'warning', 'error')
           OR COALESCE(log_level, '') IN ('warning', 'error', 'critical')
        ORDER BY created_at DESC, log_id DESC
        LIMIT 50
        """
    )
    if db_rows:
        rows = [
            {
                "alertId": row.get("log_id"),
                "level": row.get("log_level") or "warning",
                "title": row.get("title") or row.get("content") or "-",
                "deviceName": row.get("device_name") or "-",
                "status": row.get("online_status") or "open",
                "createdAt": fmt_dt(row.get("created_at")),
            }
            for row in db_rows
        ]
        return response_ok({"total": len(rows), "list": rows})

    return response_ok({"total": 0, "list": []})



@admin_bp.get("/operator/device/firmware-packages")
@require_admin("super", "operator")
def firmware_packages():
    db_rows = mysql_all(
        """
        SELECT firmware_id, model_name, version, version_code, file_size,
               description, status, created_at, updated_at
        FROM device_firmware
        WHERE COALESCE(status, '') NOT IN ('deleted', 'disabled')
        ORDER BY COALESCE(version_code, 0) DESC, updated_at DESC, created_at DESC, firmware_id DESC
        LIMIT 50
        """
    )
    if db_rows:
        rows = [
            {
                "packageId": f"FW-{row.get('firmware_id')}",
                "version": row.get("version") or "-",
                "modelName": row.get("model_name") or "-",
                "status": row.get("status") or "stable",
                "sizeMb": round(_float(row.get("file_size"), 0) / 1024 / 1024, 2) if row.get("file_size") else 0,
                "uploadedAt": fmt_dt(row.get("updated_at") or row.get("created_at")),
                "releaseNote": row.get("description") or "",
            }
            for row in db_rows
        ]
        return response_ok({"total": len(rows), "list": rows})

    return response_ok({"total": 0, "list": []})


def firmware_upload_catalog():
    return []


@admin_bp.get("/operator/device/firmware-upload-options")
@require_admin("super", "operator")
def firmware_upload_options():
    return response_ok({"total": 0, "list": []})


@admin_bp.post("/operator/device/firmware-upload")
@require_admin("super", "operator")
def upload_firmware_package():
    return response_error(400, "firmware upload catalog is empty")


@admin_bp.get("/operator/device/firmware-tasks")
@require_admin("super", "operator")
def firmware_tasks():
    db_rows = mysql_all(
        """
        SELECT task_id, task_no, device_id, current_version, target_version,
               status, progress, fail_reason, started_at, created_at, updated_at
        FROM device_firmware_update_task
        ORDER BY created_at DESC, updated_at DESC, task_id DESC
        LIMIT 50
        """
    )
    if db_rows:
        tasks = [
            {
                "taskId": row.get("task_no") or row.get("task_id"),
                "targetVersion": row.get("target_version") or "-",
                "targetScope": f"device {row.get('device_id')}" if row.get("device_id") else "全部设备",
                "status": row.get("status") or "pending",
                "successCount": _int(row.get("progress"), 0),
                "failCount": 0 if not row.get("fail_reason") or row.get("fail_reason") == "-" else 1,
                "failureReason": row.get("fail_reason") or "-",
                "createdAt": fmt_dt(row.get("created_at") or row.get("started_at") or row.get("updated_at")),
            }
            for row in db_rows
        ]
        return response_ok({"total": len(tasks), "list": tasks})

    return response_ok({"total": 0, "list": []})


@admin_bp.post("/operator/device/firmware-task")
@require_admin("super", "operator")
def create_firmware_task():
    body = request.get_json(silent=True) or {}
    device = current_device()
    task_no = f"FWU-{datetime.now().strftime('%m%d%H%M%S')}"
    target_version = body.get("targetVersion") or _latest_firmware_version(os.environ.get("LATEST_FIRMWARE_VERSION", "1.0.5"))
    inserted = mysql_exec(
        """
        INSERT INTO device_firmware_update_task
            (task_no, device_id, current_version, target_version, status, progress, fail_reason, operator_name, started_at, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'pending', 0, '-', %s, NOW(), NOW(), NOW())
        """,
        (task_no, body.get("deviceId") or device["deviceId"], device["firmwareVersion"], target_version, g.admin.get("realName") or g.admin.get("username")),
        fetch_last_id=True,
    )
    if inserted:
        task = {
            "taskId": task_no,
            "targetVersion": target_version,
            "targetScope": body.get("targetScope") or "",
            "status": "pending",
            "successCount": 0,
            "failCount": 0,
            "failureReason": "-",
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return response_ok(task, "firmware task created")

    return response_error(500, "firmware task create failed", "device_firmware_update_task is not writable")


@admin_bp.post("/operator/feedback/handle")
@require_admin("super", "operator")
def handle_feedback():
    body = request.get_json(silent=True) or {}
    feedback_id = str(body.get("feedbackId") or "").strip()
    status = str(body.get("status") or "processed").strip()
    remark = str(body.get("remark") or "").strip()

    if not feedback_id:
        return response_error(400, "处理失败", "feedbackId 不能为空")

    valid_status = {"open", "pending", "processing", "processed", "closed"}
    if status not in valid_status:
        return response_error(400, "处理失败", "status 必须是 open、pending、processing、processed 或 closed")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    handled_at = now if status in {"processing", "processed", "closed"} else None
    closed_at = now if status == "closed" else None
    handler_name = g.admin.get("realName") or g.admin.get("roleName") or g.admin.get("username")
    admin_id = g.admin.get("adminId")

    affected = mysql_exec(
        """
        UPDATE user_feedback
        SET status=%s,
            admin_id=%s,
            handler_name=%s,
            reply_content=%s,
            handled_at=COALESCE(%s, handled_at),
            closed_at=%s,
            updated_at=NOW()
        WHERE feedback_no=%s OR CAST(feedback_id AS CHAR)=%s
        """,
        (
            status,
            admin_id,
            handler_name,
            remark or "已记录处理意见",
            handled_at,
            closed_at,
            feedback_id,
            feedback_id,
        ),
    )

    if not affected:
        return response_error(404, "处理失败", "反馈不存在")

    with _ADMIN_CACHE_LOCK:
        _ADMIN_CACHE.clear()

    return response_ok(
        {
            "result": True,
            "feedbackId": feedback_id,
            "status": status,
            "handlerName": handler_name,
            "handledAt": handled_at or "",
            "remark": remark or "已记录处理意见",
        },
        "反馈处理状态已更新",
    )


@admin_compat_bp.get("/api/operator/market/profile")
@require_admin("super", "market", "operator")
def legacy_operator_market_profile():
    admin = g.admin if g.admin["role"] in ("market_admin", "operator_admin") else DEFAULT_ADMINS["market"]
    return response_ok(public_admin_info(admin, include_private=True))
