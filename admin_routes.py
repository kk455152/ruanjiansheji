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
CAPTCHA_EXPIRE_SECONDS = int(os.environ.get("ADMIN_CAPTCHA_EXPIRE_SECONDS", "300"))
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
    last_login_map = ((load_state().get("admin_console", {}) or {}).get("adminLastLoginAt") or {})
    for username in overlay["deleted"]:
        result.pop(username, None)
    for username, record in overlay["accounts"].items():
        if username in result:
            result[username].update(record)
        else:
            result[username] = dict(record)
    for username, last_login_at in last_login_map.items():
        if username in result:
            result[username]["lastLoginAt"] = last_login_at
    return result


def find_admin(username):
    return all_admins().get(username)


def update_admin_password(admin, new_password):
    username = str(admin.get("username") or "").strip()
    if not username:
        return False

    db_row = mysql_one(
        "SELECT admin_id FROM admin_user WHERE username=%s LIMIT 1",
        (username,),
    )
    if db_row and db_row.get("admin_id"):
        updated = mysql_exec(
            "UPDATE admin_user SET password_hash=%s, updated_at=NOW() WHERE admin_id=%s",
            (new_password, db_row.get("admin_id")),
        )
        return bool(updated is not False)

    overlay = admin_accounts_overlay()
    accounts = dict(overlay["accounts"])
    record = dict(accounts.get(username) or DEFAULT_ADMINS.get(username) or admin)
    record["username"] = username
    record["password"] = new_password
    record["role"] = record.get("role") or admin.get("role")
    record["roleName"] = ROLE_NAME_MAP.get(record.get("role"), record.get("roleName") or "")
    accounts[username] = record
    _save_admin_overlay({"accounts": accounts, "deleted": overlay["deleted"]})
    return True


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


def write_admin_audit(action, module, operation_name, target="", result_status="success", error_message="", admin=None, params=None):
    actor = admin or getattr(g, "admin", None) or {}
    payload = {
        "target": target,
        **(params or {}),
    }
    try:
        param_text = json.dumps(json_safe(payload), ensure_ascii=False)
    except Exception:
        param_text = str(payload)
    mysql_exec(
        """
        INSERT INTO admin_operation_log
            (admin_id, action, module, operation_name, path, request_method,
             ip_address, user_agent, params, result_status, error_message, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            actor.get("adminId"),
            action,
            module,
            operation_name,
            request.path if request else "",
            request.method if request else "",
            request.headers.get("X-Forwarded-For", request.remote_addr or "") if request else "",
            request.headers.get("User-Agent", "")[:500] if request else "",
            param_text[:2000],
            result_status,
            error_message[:500] if error_message else "",
        ),
    )


def record_admin_login(admin):
    login_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    admin_id = admin.get("adminId")
    if admin_id:
        mysql_exec(
            "UPDATE admin_user SET last_login_at=%s WHERE admin_id=%s",
            (login_at, admin_id),
        )
    try:
        state = load_state()
        state.setdefault("admin_console", {}).setdefault("adminLastLoginAt", {})[admin["username"]] = login_at
        save_state(state)
    except Exception:
        pass
    admin["lastLoginAt"] = login_at
    return login_at


def _b64_encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(text):
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _captcha_answer_hash(answer, salt):
    return hashlib.sha256(f"{salt}:{answer}:{TOKEN_SECRET}".encode("utf-8")).hexdigest()


def sign_captcha(answer):
    salt = secrets.token_hex(8)
    payload = {
        "salt": salt,
        "answerHash": _captcha_answer_hash(str(answer), salt),
        "exp": int((datetime.now() + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS)).timestamp()),
        "nonce": secrets.token_hex(8),
    }
    payload_part = _b64_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), f"captcha.{payload_part}".encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64_encode(signature)}"


def verify_captcha(token, answer):
    try:
        payload_part, signature_part = str(token or "").split(".", 1)
        expected = hmac.new(TOKEN_SECRET.encode("utf-8"), f"captcha.{payload_part}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64_decode(signature_part), expected):
            return False
        payload = json.loads(_b64_decode(payload_part).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now().timestamp()):
            return False
        answer_text = str(answer or "").strip()
        if not answer_text:
            return False
        actual_hash = _captcha_answer_hash(answer_text, str(payload.get("salt") or ""))
        return hmac.compare_digest(actual_hash, str(payload.get("answerHash") or ""))
    except Exception:
        return False


def make_captcha_challenge():
    operator = ["+", "-", "x"][secrets.randbelow(3)]
    if operator == "+":
        left = 10 + secrets.randbelow(30)
        right = 1 + secrets.randbelow(20)
        answer = left + right
    elif operator == "-":
        left = 20 + secrets.randbelow(40)
        right = 1 + secrets.randbelow(min(left - 1, 25))
        answer = left - right
    else:
        left = 2 + secrets.randbelow(8)
        right = 2 + secrets.randbelow(8)
        answer = left * right
    return {
        "question": f"{left} {operator} {right} = ?",
        "captchaToken": sign_captcha(answer),
        "expiresIn": CAPTCHA_EXPIRE_SECONDS,
    }


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
    info = {key: admin.get(key) for key in keys if key in admin}
    info["permissions"] = effective_role_permissions(admin.get("role"))
    info["permissionsUpdatedAt"] = role_permissions_updated_at()
    return info


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


def request_permission_keys():
    path = request.path
    for prefixes, permissions in API_PERMISSION_RULES:
        if any(path.startswith(prefix) for prefix in prefixes):
            return permissions
    return ()


def admin_has_any_permission(admin, permissions):
    granted = set(effective_role_permissions(admin.get("role")))
    return any(permission in granted for permission in permissions)


def require_admin(*scopes):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            admin = decode_token(bearer_token() or "")
            if not admin:
                return response_error(401, "未登录", "请先登录后台管理系统")

            permission_keys = request_permission_keys()
            if permission_keys:
                if not admin_has_any_permission(admin, permission_keys):
                    return response_error(403, "无权限访问", "当前账号无权访问该功能模块")
            else:
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


def ratio(numerator, denominator):
    base = max(_float(denominator, 0), 1)
    value = _float(numerator, 0) / base
    return round(min(max(value, 0), 1), 4)


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


def device_online(row):
    text = str(row.get("online_status") or "").strip().lower()
    if text in {"online", "true", "1", "yes", "在线"}:
        return True
    if text in {"offline", "false", "0", "no", "离线"}:
        return False
    return bool(row.get("status"))


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
            d.online_status,
            d.last_active,
            d.firmware_version,
            d.device_name,
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
            "deviceName": row.get("device_name") or row.get("custom_device_name") or row.get("device_number") or "",
            "modelName": row.get("model_name") or "",
            "ownerName": row.get("owner_name") or "",
            "online": device_online(row),
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


def normalized_music_service(value):
    text = platform_text(value).replace(" ", "")
    if text in {"网易云音乐", "网易云"}:
        return "网易云音乐"
    if text in {"QQ音乐", "QQ"}:
        return "QQ音乐"
    return None


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
    rows = mysql_all("SELECT bound_platforms FROM user_profile")
    counts = {"网易云音乐": 0, "QQ音乐": 0}
    for row in rows:
        values = str(row.get("bound_platforms") or "").replace("、", ",").split(",")
        for value in values:
            service = normalized_music_service(value.strip())
            if service:
                counts[service] += 1
    return [
        {"service": "netease", "serviceName": "网易云音乐", "count": counts["网易云音乐"]},
        {"service": "qq_music", "serviceName": "QQ音乐", "count": counts["QQ音乐"]},
    ]


def heatmap(kind):
    order_sql = "sales_amount DESC, order_count DESC, region_name ASC" if kind == "sales" else "user_count DESC, active_user_count DESC, region_name ASC"
    rows = mysql_all(
        f"""
        SELECT region_code, region_name, sales_amount, order_count,
               user_count, active_user_count
        FROM region_stats_daily
        WHERE stat_date = (SELECT MAX(stat_date) FROM region_stats_daily)
        ORDER BY {order_sql}
        LIMIT 20
        """
    )
    if not rows and kind == "sales":
        rows = mysql_all(
            """
            SELECT
                COALESCE(province_code, 'unknown') AS region_code,
                COALESCE(province_name, city_name, '未知地区') AS region_name,
                COALESCE(SUM(pay_amount), 0) AS sales_amount,
                COUNT(*) AS order_count,
                0 AS user_count,
                0 AS active_user_count
            FROM sales_order
            WHERE pay_status IN ('paid', 'success', 'finished')
            GROUP BY COALESCE(province_code, 'unknown'),
                     COALESCE(province_name, city_name, '未知地区')
            ORDER BY sales_amount DESC, order_count DESC
            LIMIT 20
            """
        )
    if not rows and kind == "user":
        rows = mysql_all(
            """
            SELECT
                COALESCE(province_code, 'unknown') AS region_code,
                COALESCE(province_name, city_name, '未知地区') AS region_name,
                0 AS sales_amount,
                0 AS order_count,
                COUNT(*) AS user_count,
                COUNT(CASE WHEN active_level='high' THEN 1 END) AS active_user_count
            FROM user_profile
            GROUP BY COALESCE(province_code, 'unknown'),
                     COALESCE(province_name, city_name, '未知地区')
            ORDER BY user_count DESC, active_user_count DESC
            LIMIT 20
            """
        )
    rows = [
        row for row in rows
        if valid_region_row(row)
    ]
    rows = merge_region_rows(rows, kind)
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


PROVINCE_NAME_BY_CODE = {
    "110000": "北京市",
    "310000": "上海市",
    "320000": "江苏省",
    "330000": "浙江省",
    "370000": "山东省",
    "420000": "湖北省",
    "440000": "广东省",
    "500000": "重庆市",
    "510000": "四川省",
    "610000": "陕西省",
}


PROVINCE_CODE_BY_NAME = {name: code for code, name in PROVINCE_NAME_BY_CODE.items()}


def normalize_region_group(row):
    raw_code = str(row.get("region_code") or "").strip()
    raw_name = str(row.get("region_name") or "").strip()
    name = raw_name.split("/")[0].strip()
    name = name.split("／")[0].strip()
    if raw_code.isdigit() and len(raw_code) == 6:
        province_code = raw_code[:2] + "0000"
        province_name = PROVINCE_NAME_BY_CODE.get(province_code) or name
        return province_code, province_name
    if name in PROVINCE_CODE_BY_NAME:
        return PROVINCE_CODE_BY_NAME[name], name
    if raw_code in PROVINCE_CODE_BY_NAME:
        return PROVINCE_CODE_BY_NAME[raw_code], raw_code
    return raw_code or name, name or raw_code


def merge_region_rows(rows, kind):
    merged = {}
    for row in rows:
        code, name = normalize_region_group(row)
        if not name:
            continue
        item = merged.setdefault(code or name, {
            "region_code": code,
            "region_name": name,
            "sales_amount": 0,
            "order_count": 0,
            "user_count": 0,
            "active_user_count": 0,
        })
        item["sales_amount"] += _float(row.get("sales_amount"), 0)
        item["order_count"] += _int(row.get("order_count"), 0)
        item["user_count"] += _int(row.get("user_count"), 0)
        item["active_user_count"] += _int(row.get("active_user_count"), 0)
    sort_key = (
        (lambda item: (-_float(item.get("sales_amount"), 0), -_int(item.get("order_count"), 0), item.get("region_name") or ""))
        if kind == "sales"
        else (lambda item: (-_int(item.get("user_count"), 0), -_int(item.get("active_user_count"), 0), item.get("region_name") or ""))
    )
    return sorted(merged.values(), key=sort_key)[:20]


def valid_region_row(row):
    region_name = str(row.get("region_name") or "").strip()
    region_code = str(row.get("region_code") or "").strip().lower()
    if not region_name or set(region_name) <= {"?"}:
        return False
    if region_code in {"unknown", "datefix"}:
        return False
    return True


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
            normalized_status = "pending" if status in ("open", "pending") else status
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
                "status": normalized_status,
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


@admin_bp.get("/captcha")
def captcha():
    return response_ok(make_captcha_challenge(), "验证码已生成")


@admin_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()
    captcha_token = str(body.get("captchaToken", "")).strip()
    captcha_answer = str(body.get("captchaAnswer", "")).strip()

    if not username or not password:
        return response_error(400, "登录失败", "请求参数不完整，用户名和密码不能为空。")
    if not captcha_token or not captcha_answer:
        write_admin_audit("login_failed", "认证", "登录机器人验证失败", username, "failed", "机器人验证未完成", None)
        return response_error(400, "验证失败", "请先完成机器人验证。")
    if not verify_captcha(captcha_token, captcha_answer):
        write_admin_audit("login_failed", "认证", "登录机器人验证失败", username, "failed", "机器人验证错误或已过期", None)
        return response_error(400, "验证失败", "机器人验证错误或已过期，请刷新后重试。")

    admin = find_admin(username)
    if not admin or not verify_admin_password(password, admin.get("password", "")):
        write_admin_audit("login_failed", "认证", "登录系统失败", username, "failed", "用户名或密码错误", None)
        return response_error(401, "认证失败", "用户名或密码错误，请重新输入。")

    token = sign_token(admin)
    record_admin_login(admin)
    write_admin_audit("login", "认证", "登录系统", username, "success", "", admin)
    return response_ok({"token": token, "adminInfo": public_admin_info(admin)}, "登录成功")


@admin_bp.get("/profile")
@require_admin("super", "market", "operator", "boss")
def profile():
    return response_ok(public_admin_info(g.admin, include_private=True))


@admin_bp.post("/password")
@require_admin("super", "market", "operator", "boss")
def change_password():
    body = request.get_json(silent=True) or {}
    current_password = str(body.get("currentPassword") or "").strip()
    new_password = str(body.get("newPassword") or "").strip()
    confirm_password = str(body.get("confirmPassword") or "").strip()
    username = g.admin.get("username") or ""

    if not current_password or not new_password or not confirm_password:
        return response_error(400, "修改失败", "当前密码、新密码和确认密码不能为空。")
    if len(new_password) < 6 or len(new_password) > 32:
        return response_error(400, "修改失败", "新密码长度需为 6 到 32 位。")
    if new_password != confirm_password:
        return response_error(400, "修改失败", "两次输入的新密码不一致。")
    if not verify_admin_password(current_password, g.admin.get("password", "")):
        write_admin_audit("change_own_password", "账户", "修改个人密码", username, "failed", "当前密码错误", g.admin)
        return response_error(401, "修改失败", "当前密码错误，请重新输入。")
    if verify_admin_password(new_password, g.admin.get("password", "")):
        return response_error(400, "修改失败", "新密码不能与当前密码相同。")

    if not update_admin_password(g.admin, new_password):
        write_admin_audit("change_own_password", "账户", "修改个人密码", username, "failed", "密码保存失败", g.admin)
        return response_error(500, "修改失败", "密码保存失败，请稍后重试。")

    write_admin_audit("change_own_password", "账户", "修改个人密码", username, "success", "", g.admin)
    return response_ok(public_admin_info(find_admin(username) or g.admin, include_private=True), "密码已更新")


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
    online = count_sql(f"SELECT COUNT(*) AS c FROM device WHERE {ONLINE_DEVICE_CONDITION}", fallback=0)
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
    metrics = overview_activity_metrics()
    return response_ok(metrics)


def overview_activity_metrics():
    total = count_sql("SELECT COUNT(*) AS c FROM user_profile", fallback=0)
    if not total:
        total = count_sql("SELECT COUNT(*) AS c FROM `user`", fallback=0)
    active = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level = 'high'", fallback=0)
    return {"activeUserCount": active, "totalUserCount": total, "activityRate": round(active / max(total, 1), 4)}


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
        SELECT h.ranking_date, h.rank_no, h.target_id, h.target_name, h.target_category,
               h.metric_value, h.metric_unit, h.scope_type, h.scope_code,
               COALESCE(
                   NULLIF(NULLIF(h.scope_code, 'global'), ''),
                   (
                       SELECT mm.platform
                       FROM media_mapping mm
                       WHERE mm.external_id = h.target_id OR mm.song_title = h.target_name
                       ORDER BY mm.mapping_id DESC
                       LIMIT 1
                   )
               ) AS source_platform,
               (
                   SELECT COUNT(DISTINCT ph.user_id)
                   FROM play_history ph
                   LEFT JOIN media_mapping mm2 ON mm2.mapping_id = ph.mapping_id
                   WHERE DATE(ph.created_at) = h.ranking_date
                     AND (
                         COALESCE(mm2.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)) = h.target_id
                         OR mm2.song_title = h.target_name
                     )
               ) AS user_count
        FROM hot_ranking_daily h
        WHERE h.ranking_type = 'song'
          AND h.ranking_date = (
              SELECT MAX(ranking_date)
              FROM hot_ranking_daily
              WHERE ranking_type = 'song'
          )
        ORDER BY metric_value DESC, rank_no ASC, target_name ASC
        LIMIT 10
        """
    )
    if not ranking_rows:
        ranking_rows = mysql_all(
            """
            SELECT
                DATE(ph.created_at) AS ranking_date,
                0 AS rank_no,
                COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)) AS target_id,
                COALESCE(mm.song_title, '未知歌曲') AS target_name,
                COALESCE(mm.artist, '未知歌手') AS target_category,
                COUNT(*) AS metric_value,
                'plays' AS metric_unit,
                'platform' AS scope_type,
                COALESCE(ph.source_platform, mm.platform, '未知平台') AS scope_code,
                COALESCE(ph.source_platform, mm.platform, '未知平台') AS source_platform,
                COUNT(DISTINCT ph.user_id) AS user_count
            FROM play_history ph
            LEFT JOIN media_mapping mm ON mm.mapping_id = ph.mapping_id
            WHERE DATE(ph.created_at) = (SELECT MAX(DATE(created_at)) FROM play_history)
            GROUP BY DATE(ph.created_at),
                     COALESCE(mm.external_id, CAST(ph.mapping_id AS CHAR), CAST(ph.history_id AS CHAR)),
                     COALESCE(mm.song_title, '未知歌曲'),
                     COALESCE(mm.artist, '未知歌手'),
                     COALESCE(ph.source_platform, mm.platform, '未知平台')
            ORDER BY metric_value DESC, target_name ASC
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
                    "platform": platform_text(row.get("source_platform") or row.get("scope_code") or row.get("scope_type")),
                    "playCount": _int(row.get("metric_value"), 0),
                    "userCount": _int(row.get("user_count"), 0),
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

        def retained_count(days):
            return count_sql(
                """
                SELECT COUNT(DISTINCT so.user_id) AS c
                FROM sales_order so
                JOIN play_history ph ON ph.user_id = so.user_id
                WHERE so.pay_status IN ('paid', 'success', 'finished')
                  AND DATE(so.created_at) = %s
                  AND DATE(ph.created_at) >= DATE_ADD(DATE(so.created_at), INTERVAL %s DAY)
                  AND DATE(ph.created_at) < DATE_ADD(DATE(so.created_at), INTERVAL %s DAY)
                """,
                (date_value, days, days + 1),
            )

        day1 = min(retained_count(1), purchases)
        day7 = min(retained_count(7), purchases)
        day30 = min(retained_count(30), purchases)
        data.append({
            "date": str(date_value),
            "purchaseUserCount": purchases,
            "day1RetainedCount": day1,
            "day7RetainedCount": day7,
            "day30RetainedCount": day30,
            "day1RetentionRate": ratio(day1, purchases),
            "day7RetentionRate": ratio(day7, purchases),
            "day30RetentionRate": ratio(day30, purchases),
        })
    return response_ok({"list": data})


@admin_bp.get("/market/profile")
@require_admin("super", "market")
def market_profile():
    admin = g.admin if g.admin["role"] == "market_admin" else DEFAULT_ADMINS["market"]
    return response_ok(public_admin_info(admin, include_private=True))


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
            d.online_status,
            d.firmware_version,
            d.last_active,
            d.device_name,
            b.user_id,
            b.custom_device_name,
            COALESCE(p.nickname, u.nickname, u.username) AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id
        LEFT JOIN `user` u ON u.user_id = b.user_id
        LEFT JOIN user_profile p ON p.user_id = u.user_id
        ORDER BY d.device_id ASC
        """
    )
    if rows:
        devices = [
            {
                "deviceId": str(row.get("device_id")),
                "deviceSn": row.get("device_number") or "",
                "deviceName": row.get("device_name") or row.get("custom_device_name") or row.get("device_number") or "",
                "modelName": row.get("model_name") or "",
                "ownerName": row.get("owner_name") or "",
                "userId": str(row.get("user_id")) if row.get("user_id") is not None else "",
                "online": device_online(row),
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
    device_id = request.args.get("deviceId")
    device = current_device(device_id)
    device["unbindMeaning"] = "解绑只删除 user_device_binding 里的用户-设备绑定关系，不删除 device 设备本体。"
    return response_ok(device)


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
        "UPDATE device SET device_name=%s, updated_at=NOW() WHERE device_id=%s",
        (name, device_id),
    )
    mysql_exec(
        "UPDATE user_device_binding SET custom_device_name=%s WHERE device_id=%s",
        (name, device_id),
    )
    write_admin_audit("rename_device", "设备管理", "修改设备名称", device_id, "success", "", params={"deviceName": name})
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
    write_admin_audit("unbind_device", "设备管理", "解绑设备", device_id, "success")
    return response_ok({"deviceId": device_id, "unbound": True}, "设备解绑成功")


@admin_bp.get("/operator/device/logs")
@require_admin("super", "operator")
def device_logs():
    page = max(_int(request.args.get("page"), 1), 1)
    page_size = min(max(_int(request.args.get("pageSize"), 20), 1), 100)
    db_total = count_sql("SELECT COUNT(*) AS c FROM device_log", fallback=0)
    rows = mysql_all(
        """
        SELECT
            dl.log_id,
            dl.device_id,
            COALESCE(NULLIF(dl.device_name, ''), NULLIF(d.device_name, ''), d.device_number) AS device_name,
            COALESCE(NULLIF(dl.device_sn, ''), d.device_number) AS device_sn,
            COALESCE(NULLIF(dl.device_model, ''), d.model_name) AS device_model,
            dl.log_type,
            dl.log_level,
            dl.title,
            dl.content,
            dl.event_code,
            dl.trace_id,
            dl.created_at
        FROM device_log dl
        LEFT JOIN device d ON d.device_id = dl.device_id
        ORDER BY dl.created_at DESC, dl.log_id DESC
        LIMIT 100
        """,
    )
    result = [format_device_log_row(row) for row in rows]
    synthetic_rows = synthetic_device_log_rows()
    result.extend(synthetic_rows)
    result = sorted(result, key=lambda item: item.get("createdAt") or "", reverse=True)
    start = (page - 1) * page_size
    visible = result[start:start + page_size]
    total = (db_total or len(rows)) + len(synthetic_rows)
    return response_ok({"total": total or len(result), "page": page, "pageSize": page_size, "list": visible})


def format_device_log_row(row):
    return {
        "logId": row.get("log_id"),
        "deviceId": str(row.get("device_id") or ""),
        "deviceSn": row.get("device_sn") or "",
        "deviceName": row.get("device_name") or "",
        "deviceModel": row.get("device_model") or "",
        "logType": row.get("log_type") or "",
        "logLevel": row.get("log_level") or "",
        "title": row.get("title") or row.get("content") or "",
        "content": row.get("content") or "",
        "eventCode": row.get("event_code") or "",
        "traceId": row.get("trace_id") or "",
        "createdAt": str(row.get("created_at") or ""),
    }


def synthetic_device_log_rows():
    rows = []
    device_rows = mysql_all(
        """
        SELECT device_id, device_number, device_name, model_name, online_status,
               status, firmware_version, ip_address, location, last_active
        FROM device
        ORDER BY last_active DESC, device_id DESC
        LIMIT 20
        """
    )
    for row in device_rows:
        online = device_online(row)
        title = "设备上线" if online else "设备离线"
        created_at = fmt_dt(row.get("last_active"))
        device_name = row.get("device_name") or row.get("device_number") or f"device {row.get('device_id')}"
        rows.append({
            "logId": f"device-state-{row.get('device_id')}",
            "deviceId": str(row.get("device_id") or ""),
            "deviceSn": row.get("device_number") or "",
            "deviceName": device_name,
            "deviceModel": row.get("model_name") or "",
            "logType": "online" if online else "offline",
            "logLevel": "info" if online else "warning",
            "title": title,
            "content": f"{device_name} 当前{'在线' if online else '离线'}，最近活跃时间：{created_at or '-'}",
            "eventCode": "DEVICE_ONLINE" if online else "DEVICE_OFFLINE",
            "traceId": f"device-{row.get('device_id')}-{str(created_at).replace(' ', '-')}",
            "createdAt": created_at,
        })

    task_rows = mysql_all(
        """
        SELECT t.task_id, t.task_no, t.device_id, t.current_version, t.target_version,
               t.status, t.progress, t.fail_reason, t.started_at, t.finished_at,
               t.created_at, t.updated_at,
               d.device_number, d.device_name, d.model_name, d.ip_address, d.location
        FROM device_firmware_update_task t
        LEFT JOIN device d ON d.device_id=t.device_id
        ORDER BY t.created_at DESC, t.updated_at DESC, t.task_id DESC
        LIMIT 20
        """
    )
    for row in task_rows:
        status = str(row.get("status") or "pending")
        fail_reason = "" if row.get("fail_reason") in ("", "-") else row.get("fail_reason") or ""
        if fail_reason or status in ("failed", "fail", "error"):
            title = "固件升级失败"
            level = "error"
        elif status in ("success", "finished", "completed"):
            title = "固件升级完成"
            level = "info"
        elif status in ("running", "processing", "upgrading"):
            title = "固件升级中"
            level = "info"
        else:
            title = "固件升级任务创建"
            level = "info"
        device_name = row.get("device_name") or row.get("device_number") or f"device {row.get('device_id') or '-'}"
        created_at = fmt_dt(row.get("updated_at") or row.get("created_at") or row.get("started_at"))
        rows.append({
            "logId": f"firmware-task-{row.get('task_id')}",
            "deviceId": str(row.get("device_id") or ""),
            "deviceSn": row.get("device_number") or "",
            "deviceName": device_name,
            "deviceModel": row.get("model_name") or "",
            "logType": "firmware",
            "logLevel": level,
            "title": title,
            "content": f"{device_name} 从 {row.get('current_version') or '-'} 升级到 {row.get('target_version') or '-'}，状态：{status}{'，失败原因：' + fail_reason if fail_reason else ''}",
            "eventCode": "FIRMWARE_UPDATE_TASK",
            "traceId": row.get("task_no") or f"firmware-task-{row.get('task_id')}",
            "createdAt": created_at,
        })
    return rows


def synthetic_device_log_detail(log_id):
    text = str(log_id or "")
    if text.startswith("device-state-"):
        device_id = text.replace("device-state-", "", 1)
        row = mysql_one(
            """
            SELECT device_id, device_number, device_name, device_type, model_name,
                   online_status, status, firmware_version, ip_address, location,
                   last_active
            FROM device
            WHERE CAST(device_id AS CHAR)=%s
            LIMIT 1
            """,
            (device_id,),
        )
        if not row:
            return {}
        online = device_online(row)
        created_at = fmt_dt(row.get("last_active"))
        device_name = row.get("device_name") or row.get("device_number") or f"device {row.get('device_id')}"
        return {
            "logId": text,
            "deviceId": str(row.get("device_id") or ""),
            "deviceSn": row.get("device_number") or "",
            "deviceName": device_name,
            "deviceType": row.get("device_type") or "",
            "deviceTypeText": row.get("device_type") or "",
            "deviceModel": row.get("model_name") or "",
            "logType": "online" if online else "offline",
            "logTypeText": "设备上线" if online else "设备离线",
            "logLevel": "info" if online else "warning",
            "logLevelText": "info" if online else "warning",
            "title": "设备上线" if online else "设备离线",
            "content": f"{device_name} 当前{'在线' if online else '离线'}，最近活跃时间：{created_at or '-'}",
            "eventCode": "DEVICE_ONLINE" if online else "DEVICE_OFFLINE",
            "traceId": f"device-{row.get('device_id')}-{str(created_at).replace(' ', '-')}",
            "taskId": "",
            "firmwareVersion": row.get("firmware_version") or "",
            "onlineStatus": row.get("online_status") or row.get("status") or "",
            "onlineStatusText": "在线" if online else "离线",
            "ipAddress": row.get("ip_address") or "",
            "networkType": "",
            "location": row.get("location") or "",
            "extra": {},
            "stackTrace": None,
            "requestInfo": {"url": "", "method": "", "requestId": "", "responseCode": None, "responseMessage": ""},
            "createdAt": created_at,
        }
    if text.startswith("firmware-task-"):
        task_id = text.replace("firmware-task-", "", 1)
        row = mysql_one(
            """
            SELECT t.task_id, t.task_no, t.device_id, t.current_version, t.target_version,
                   t.status, t.progress, t.fail_reason, t.started_at, t.finished_at,
                   t.created_at, t.updated_at,
                   d.device_number, d.device_name, d.device_type, d.model_name,
                   d.firmware_version, d.online_status, d.ip_address, d.location
            FROM device_firmware_update_task t
            LEFT JOIN device d ON d.device_id=t.device_id
            WHERE CAST(t.task_id AS CHAR)=%s
            LIMIT 1
            """,
            (task_id,),
        )
        if not row:
            return {}
        status = str(row.get("status") or "pending")
        fail_reason = "" if row.get("fail_reason") in ("", "-") else row.get("fail_reason") or ""
        title = "固件升级失败" if fail_reason or status in ("failed", "fail", "error") else "固件升级任务"
        device_name = row.get("device_name") or row.get("device_number") or f"device {row.get('device_id') or '-'}"
        return {
            "logId": text,
            "deviceId": str(row.get("device_id") or ""),
            "deviceSn": row.get("device_number") or "",
            "deviceName": device_name,
            "deviceType": row.get("device_type") or "",
            "deviceTypeText": row.get("device_type") or "",
            "deviceModel": row.get("model_name") or "",
            "logType": "firmware",
            "logTypeText": "固件升级",
            "logLevel": "error" if fail_reason else "info",
            "logLevelText": "error" if fail_reason else "info",
            "title": title,
            "content": f"{device_name} 从 {row.get('current_version') or '-'} 升级到 {row.get('target_version') or '-'}，状态：{status}{'，失败原因：' + fail_reason if fail_reason else ''}",
            "eventCode": "FIRMWARE_UPDATE_TASK",
            "traceId": row.get("task_no") or text,
            "taskId": row.get("task_no") or row.get("task_id") or "",
            "firmwareVersion": row.get("firmware_version") or row.get("target_version") or "",
            "onlineStatus": row.get("online_status") or "",
            "onlineStatusText": row.get("online_status") or "",
            "ipAddress": row.get("ip_address") or "",
            "networkType": "",
            "location": row.get("location") or "",
            "extra": {"progress": row.get("progress"), "targetVersion": row.get("target_version")},
            "stackTrace": fail_reason or None,
            "requestInfo": {"url": "", "method": "", "requestId": row.get("task_no") or "", "responseCode": None, "responseMessage": fail_reason},
            "createdAt": fmt_dt(row.get("updated_at") or row.get("created_at") or row.get("started_at")),
        }
    return {}


@admin_bp.get("/operator/device/log-detail")
@require_admin("super", "operator")
def device_log_detail():
    log_id = request.args.get("logId")
    row = None
    if log_id:
        row = mysql_one(
            """
            SELECT
                dl.log_id,
                dl.device_id,
                dl.device_sn,
                dl.device_name,
                dl.device_type,
                dl.device_model,
                dl.log_type,
                dl.log_level,
                dl.title,
                dl.content,
                dl.event_code,
                dl.trace_id,
                dl.task_id,
                dl.firmware_version,
                dl.online_status,
                dl.ip_address,
                dl.network_type,
                dl.location,
                dl.request_url,
                dl.request_method,
                dl.request_id,
                dl.response_code,
                dl.response_message,
                dl.created_at,
                d.device_number AS real_device_sn,
                d.device_name AS real_device_name,
                d.device_type AS real_device_type,
                d.model_name AS real_device_model,
                d.firmware_version AS real_firmware_version,
                d.online_status AS real_online_status,
                d.ip_address AS real_ip_address,
                d.location AS real_location
            FROM device_log dl
            LEFT JOIN device d ON d.device_id = dl.device_id
            WHERE CAST(dl.log_id AS CHAR)=%s
            LIMIT 1
            """,
            (str(log_id),),
        )
    if not row:
        return response_ok(synthetic_device_log_detail(log_id))

    return response_ok({
        "logId": row.get("log_id"),
        "deviceId": str(row.get("device_id") or ""),
        "deviceSn": row.get("device_sn") or row.get("real_device_sn") or "",
        "deviceName": row.get("device_name") or row.get("real_device_name") or row.get("real_device_sn") or "",
        "deviceType": row.get("device_type") or row.get("real_device_type") or "",
        "deviceTypeText": row.get("device_type") or row.get("real_device_type") or "",
        "deviceModel": row.get("device_model") or row.get("real_device_model") or "",
        "logType": row.get("log_type") or "",
        "logTypeText": row.get("log_type") or "",
        "logLevel": row.get("log_level") or "",
        "logLevelText": row.get("log_level") or "",
        "title": row.get("title") or row.get("content") or "",
        "content": row.get("content") or "",
        "eventCode": row.get("event_code") or "",
        "traceId": row.get("trace_id") or "",
        "taskId": row.get("task_id") or "",
        "firmwareVersion": row.get("firmware_version") or row.get("real_firmware_version") or "",
        "onlineStatus": row.get("online_status") or row.get("real_online_status") or "",
        "onlineStatusText": row.get("online_status") or row.get("real_online_status") or "",
        "ipAddress": row.get("ip_address") or row.get("real_ip_address") or "",
        "networkType": row.get("network_type") or "",
        "location": row.get("location") or row.get("real_location") or "",
        "extra": {},
        "stackTrace": None,
        "requestInfo": {
            "url": row.get("request_url") or "",
            "method": row.get("request_method") or "",
            "requestId": row.get("request_id") or "",
            "responseCode": row.get("response_code"),
            "responseMessage": row.get("response_message") or "",
        },
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
    return [
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
            "lastLoginAt": fmt_dt(admin.get("lastLoginAt")) or "尚未登录",
            "editable": True,
        }
        for admin in all_admins().values()
    ]


def device_admin_rows():
    rows = cached_mysql_all(
        """
        SELECT
            d.device_id,
            d.device_number,
            d.model_name,
            d.status,
            d.online_status,
            d.last_active,
            d.firmware_version,
            b.custom_device_name,
            COALESCE(p.nickname, u.nickname, u.username) AS owner_name
        FROM device d
        LEFT JOIN user_device_binding b ON b.device_id = d.device_id AND COALESCE(b.is_primary, 1) = 1
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
                "online": device_online(row),
                "firmwareVersion": row.get("firmware_version") or "未知版本",
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
                    "permissions": role_permissions_for_display(role, permissions),
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
                "roleName": ROLE_NAME_MAP.get(row.get("role"), row.get("role")),
                "description": DEFAULT_ROLE_DESCRIPTIONS.get(row.get("role"), ""),
                "permissions": role_permissions_for_display(row.get("role")),
                "userCount": _int(row.get("user_count"), 0),
            }
            for row in db_roles
        ]

    return [
        {
            "role": "super_admin",
            "roleName": ROLE_NAME_MAP.get("super_admin", "super_admin"),
            "description": DEFAULT_ROLE_DESCRIPTIONS["super_admin"],
            "permissions": role_permissions_for_display("super_admin"),
            "userCount": count_sql("SELECT COUNT(*) AS c FROM admin_user WHERE role=%s", ("super_admin",), fallback=1),
        },
        {
            "role": "market_admin",
            "roleName": ROLE_NAME_MAP.get("market_admin", "market_admin"),
            "description": DEFAULT_ROLE_DESCRIPTIONS["market_admin"],
            "permissions": role_permissions_for_display("market_admin"),
            "userCount": count_sql("SELECT COUNT(*) AS c FROM admin_user WHERE role=%s", ("market_admin",), fallback=1),
        },
        {
            "role": "operator_admin",
            "roleName": ROLE_NAME_MAP.get("operator_admin", "operator_admin"),
            "description": DEFAULT_ROLE_DESCRIPTIONS["operator_admin"],
            "permissions": role_permissions_for_display("operator_admin"),
            "userCount": count_sql("SELECT COUNT(*) AS c FROM admin_user WHERE role=%s", ("operator_admin",), fallback=1),
        },
        {
            "role": "boss",
            "roleName": ROLE_NAME_MAP.get("boss", "boss"),
            "description": DEFAULT_ROLE_DESCRIPTIONS["boss"],
            "permissions": role_permissions_for_display("boss"),
            "userCount": count_sql("SELECT COUNT(*) AS c FROM admin_user WHERE role=%s", ("boss",), fallback=1),
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
    "feedback": "用户反馈",
    "devices": "设备管理",
    "groups": "设备分组",
    "alerts": "告警中心",
    "logs": "设备日志",
    "users": "用户管理",
    "roles": "角色权限",
    "system": "系统配置",
    "notices": "系统公告",
    "audit": "审计日志",
    "account": "个人信息",
}

DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": list(PERMISSION_CATALOG.keys()),
    "market_admin": ["overview", "decision", "trend", "region", "profile", "value", "segments", "insights", "songs", "account"],
    "operator_admin": ["overview", "trend", "feedback", "devices", "groups", "alerts", "logs", "account"],
    "boss": ["overview", "trend", "region", "profile", "value", "songs", "feedback", "account"],
}

DEFAULT_ROLE_DESCRIPTIONS = {
    "super_admin": "系统配置、用户权限、审计、安全和全量业务数据",
    "market_admin": "用户画像、区域分析、留存分析、热歌排行和营销洞察",
    "operator_admin": "设备运维、用户反馈、日志和告警处理",
    "boss": "只读经营视角，查看核心看板、趋势、地区、画像、热歌和反馈",
}


def ensure_required_role_permissions(role, permissions):
    if role != "super_admin" and "account" in PERMISSION_CATALOG and "account" not in permissions:
        return [*permissions, "account"]
    return permissions


def role_permissions_for_display(role, permissions=None, allow_empty=False):
    if role == "super_admin":
        return list(PERMISSION_CATALOG.keys())
    if permissions is None:
        return DEFAULT_ROLE_PERMISSIONS.get(role, [])
    cleaned = [p for p in (permissions or []) if p in PERMISSION_CATALOG]
    if cleaned or allow_empty:
        return ensure_required_role_permissions(role, cleaned)
    return DEFAULT_ROLE_PERMISSIONS.get(role, [])


def role_permission_overrides():
    return ((load_state().get("admin_console", {}) or {}).get("rolePermissions") or {})


def role_permissions_updated_at():
    return ((load_state().get("admin_console", {}) or {}).get("rolePermissionsUpdatedAt") or "")


def effective_role_permissions(role):
    overrides = role_permission_overrides()
    saved = overrides.get(role)
    if isinstance(saved, list):
        return role_permissions_for_display(role, saved, allow_empty=True)
    return role_permissions_for_display(role)


API_PERMISSION_RULES = [
    (("/api/admin/super/roles",), ("roles",)),
    (("/api/admin/super/users",), ("users",)),
    (("/api/admin/super/system/config",), ("system",)),
    (("/api/admin/super/security/logs",), ("audit",)),
    (("/api/admin/super/notices",), ("notices",)),
    (("/api/admin/super/decision", "/api/admin/market/decision"), ("decision", "overview")),
    (("/api/admin/super/overview",), ("overview",)),
    (("/api/admin/super/trend",), ("trend", "overview")),
    (("/api/admin/super/region", "/api/admin/market/region"), ("region", "overview")),
    (("/api/admin/super/user-value", "/api/admin/market/user-value"), ("value", "overview")),
    (("/api/admin/super/user-profile", "/api/admin/market/user-profile"), ("profile", "overview")),
    (("/api/admin/operator/feedback/handle",), ("feedback",)),
    (("/api/admin/super/feedback", "/api/admin/operator/feedback"), ("feedback", "overview")),
    (("/api/admin/market/top-songs",), ("songs", "overview")),
    (("/api/admin/market/retention",), ("trend", "overview")),
    (("/api/admin/market/segments",), ("segments",)),
    (("/api/admin/market/insights",), ("insights",)),
    (("/api/admin/operator/device/groups",), ("groups",)),
    (("/api/admin/operator/device/alerts",), ("alerts", "overview")),
    (("/api/admin/operator/device/log",), ("logs", "trend", "overview")),
    (("/api/admin/operator/device/rename", "/api/admin/operator/device/unbind"), ("devices",)),
    (
        (
            "/api/admin/operator/device/list",
            "/api/admin/operator/device/detail",
            "/api/admin/operator/device/bound-user",
            "/api/admin/operator/device/runtime-status",
        ),
        ("devices", "overview"),
    ),
]


def merged_role_rows():
    """基础角色 + 已保存的权限覆盖。"""
    overrides = admin_state_section("rolePermissions", {})
    rows = []
    for base in role_rows():
        row = dict(base)
        saved = overrides.get(base["role"])
        if isinstance(saved, list):
            row["permissions"] = role_permissions_for_display(base["role"], saved, allow_empty=True)
        else:
            row["permissions"] = role_permissions_for_display(base["role"], row.get("permissions"))
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


def _nullable_text(value):
    text = str(value or "").strip()
    return text or None


def _admin_db_row(username):
    username = str(username or "").strip()
    if not username:
        return None
    return mysql_one(
        "SELECT admin_id, username, status FROM admin_user WHERE username=%s LIMIT 1",
        (username,),
    )


def _insert_admin_user_from_body(body, username, password, role, real_name):
    job_no = _nullable_text(body.get("jobNo"))
    position = _nullable_text(body.get("position")) or ROLE_NAME_MAP[role]
    phone = _nullable_text(body.get("phone"))
    email = _nullable_text(body.get("email"))
    admin_id = mysql_exec(
        """
        INSERT INTO admin_user
            (username, password_hash, role, status, real_name, job_no,
             position, phone, email, is_super_admin, created_at, updated_at)
        VALUES
            (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
            username,
            password,
            role,
            real_name,
            job_no,
            position,
            phone,
            email,
            1 if role == "super_admin" else 0,
        ),
        fetch_last_id=True,
    )
    if not admin_id:
        return None
    return {
        "adminId": admin_id,
        "username": username,
        "password": password,
        "role": role,
        "roleName": ROLE_NAME_MAP[role],
        "realName": real_name,
        "jobNo": job_no or "-",
        "position": position,
        "phone": phone or "",
        "email": email or "",
        "status": "enabled",
    }


def _update_admin_user_from_body(admin, body):
    username = str(admin.get("username") or "").strip()
    db_row = _admin_db_row(username)
    if not db_row or not db_row.get("admin_id"):
        return False
    fields = []
    params = []
    password = str(body.get("password", "")).strip()
    role = str(body.get("role", "")).strip()
    if password:
        fields.append("password_hash=%s")
        params.append(password)
    if role:
        fields.append("role=%s")
        params.append(role)
        fields.append("is_super_admin=%s")
        params.append(1 if role == "super_admin" else 0)
        if not _nullable_text(body.get("position")):
            fields.append("position=%s")
            params.append(ROLE_NAME_MAP[role])
    mapping = {
        "realName": "real_name",
        "jobNo": "job_no",
        "position": "position",
        "phone": "phone",
        "email": "email",
    }
    for form_key, column in mapping.items():
        if form_key in body:
            fields.append(f"{column}=%s")
            params.append(_nullable_text(body.get(form_key)))
    if not fields:
        return True
    fields.append("updated_at=NOW()")
    params.append(db_row.get("admin_id"))
    updated = mysql_exec(
        f"UPDATE admin_user SET {', '.join(fields)} WHERE admin_id=%s",
        tuple(params),
    )
    return bool(updated is not False)


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
    if find_admin(username) or _admin_db_row(username):
        return response_error(409, "创建失败", "该用户名已存在。")

    db_record = _insert_admin_user_from_body(body, username, password, role, real_name)
    if db_record:
        write_admin_audit("create_admin_user", "用户管理", "新增后台账号", username, "success", "", params={"role": role})
        return response_ok(public_admin_info(db_record, include_private=True), "账号已创建")

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
    write_admin_audit("create_admin_user", "用户管理", "新增后台账号", username, "success", "", params={"role": role})
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

    if _update_admin_user_from_body(admin, body):
        record = dict(admin)
        if new_password:
            record["password"] = new_password
        if new_role:
            record["role"] = new_role
            record["roleName"] = ROLE_NAME_MAP[new_role]
        for key in ("realName", "phone", "email", "jobNo", "position"):
            if key in body and body.get(key) is not None:
                record[key] = str(body.get(key)).strip()
        write_admin_audit("update_admin_user", "用户管理", "修改后台账号", username, "success", "", params={"role": record.get("role")})
        return response_ok(public_admin_info(record, include_private=True), "账号已更新")

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
    write_admin_audit("update_admin_user", "用户管理", "修改后台账号", username, "success", "", params={"role": record.get("role")})
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

    db_row = _admin_db_row(username)
    if db_row and db_row.get("admin_id"):
        mysql_exec(
            "UPDATE admin_user SET status=0, updated_at=NOW() WHERE admin_id=%s",
            (db_row.get("admin_id"),),
        )
        write_admin_audit("delete_admin_user", "用户管理", "删除后台账号", username, "success")
        return response_ok(None, "账号已删除")

    overlay = admin_accounts_overlay()
    accounts = {u: r for u, r in overlay["accounts"].items() if u != username}
    deleted = list(overlay["deleted"])
    if username in DEFAULT_ADMINS and username not in deleted:
        deleted.append(username)
    _save_admin_overlay({"accounts": accounts, "deleted": deleted})
    write_admin_audit("delete_admin_user", "用户管理", "删除后台账号", username, "success")
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
    cleaned = list(PERMISSION_CATALOG.keys()) if role == "super_admin" else [key for key in PERMISSION_CATALOG if key in set(permissions)]
    if role != "super_admin" and "account" not in cleaned:
        cleaned.append("account")

    overrides = dict(admin_state_section("rolePermissions", {}))
    overrides[role] = cleaned
    save_admin_state_section("rolePermissions", overrides)
    updated_at = fmt_dt(datetime.now())
    save_admin_state_section("rolePermissionsUpdatedAt", updated_at)
    affected_user_count = sum(1 for admin in all_admins().values() if admin.get("role") == role)
    write_admin_audit("update_role_permissions", "角色权限", "修改用户权限", role, "success", "", params={"permissions": cleaned})

    rows = merged_role_rows()
    return response_ok(
        {
            "list": rows,
            "updatedAt": updated_at,
            "affectedUserCount": affected_user_count,
            "currentPermissions": effective_role_permissions(g.admin.get("role")),
        },
        "角色权限已更新",
    )


def audit_result_level(result_status, error_message=""):
    status = str(result_status or "").lower()
    if error_message or status in {"fail", "failed", "error", "denied"}:
        return "warning"
    return "info"


def parse_audit_params(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_seed_audit_row(row):
    text = " ".join(
        str(row.get(key) or "")
        for key in ("action", "module", "operation_name", "path")
    ).lower()
    return "seed business data" in text or ("seed" in text and "business" in text)


MEANINGFUL_AUDIT_ACTIONS = {
    "login",
    "login_failed",
    "change_own_password",
    "unbind_device",
    "rename_device",
    "update_role_permissions",
    "create_admin_user",
    "update_admin_user",
    "delete_admin_user",
    "handle_feedback",
    "create_notice",
    "update_system_config",
}


def is_meaningful_audit_row(row):
    action = str(row.get("action") or "").strip()
    if action in MEANINGFUL_AUDIT_ACTIONS:
        return True
    operation = str(row.get("operation_name") or "")
    return any(keyword in operation for keyword in ("登录", "解绑", "修改", "新增", "删除", "处理", "公告"))


def format_audit_row(row, seed=False):
    params = parse_audit_params(row.get("params"))
    target = params.get("target") or params.get("object") or params.get("deviceId") or params.get("version") or ""
    operation = row.get("operation_name") or row.get("action") or row.get("path") or "-"
    if seed:
        operation = "初始化业务测试数据"
    result = row.get("result_status") or ("success" if not row.get("error_message") else "failed")
    event = f"{operation}：{target}" if target else operation
    event = f"{event}（结果：{result}）"
    module_actor_map = {
        "firmware": "技术人员",
        "device": "售后人员",
        "roles": "超级管理员",
        "用户管理": "超级管理员",
        "角色权限": "超级管理员",
        "设备管理": "售后人员",
        "系统公告": "超级管理员",
        "用户反馈": "客服人员",
        "认证": "系统管理员",
    }
    actor = row.get("actor_name") or module_actor_map.get(row.get("module")) or "系统管理员"
    return {
        "logId": row.get("log_id"),
        "level": audit_result_level(result, row.get("error_message")),
        "event": event,
        "operation": operation,
        "target": target or "-",
        "result": result,
        "errorMessage": row.get("error_message") or "",
        "actor": actor,
        "ip": row.get("ip_address") or "-",
        "createdAt": fmt_dt(row.get("created_at")),
    }


def dynamic_audit_rows(limit=30):
    rows = []

    for row in mysql_all(
        """
        SELECT task_id, task_no, target_version, status, fail_reason, operator_name,
               created_at, updated_at
        FROM device_firmware_update_task
        ORDER BY created_at DESC, task_id DESC
        LIMIT 10
        """
    ):
        status = row.get("status") or "pending"
        rows.append({
            "logId": f"firmware-task-{row.get('task_id')}",
            "level": audit_result_level(status, row.get("fail_reason") if row.get("fail_reason") not in ("", "-") else ""),
            "event": f"下发固件升级任务：{row.get('target_version') or '-'}（结果：{status}）",
            "operation": "下发固件升级任务",
            "target": row.get("task_no") or row.get("target_version") or "-",
            "result": status,
            "errorMessage": "" if row.get("fail_reason") in ("", "-") else row.get("fail_reason") or "",
            "actor": row.get("operator_name") or "后台管理员",
            "ip": "-",
            "createdAt": fmt_dt(row.get("created_at") or row.get("updated_at")),
        })

    for row in mysql_all(
        """
        SELECT feedback_id, feedback_no, title, status, handler_name, handled_at,
               updated_at, created_at
        FROM user_feedback
        WHERE COALESCE(handler_name, '') <> ''
           OR handled_at IS NOT NULL
        ORDER BY COALESCE(handled_at, updated_at, created_at) DESC, feedback_id DESC
        LIMIT 10
        """
    ):
        rows.append({
            "logId": f"feedback-{row.get('feedback_id')}",
            "level": audit_result_level(row.get("status")),
            "event": f"处理用户反馈：{row.get('title') or row.get('feedback_no') or '-'}（结果：{row.get('status') or 'processed'}）",
            "operation": "处理用户反馈",
            "target": row.get("feedback_no") or row.get("feedback_id") or "-",
            "result": row.get("status") or "processed",
            "errorMessage": "",
            "actor": row.get("handler_name") or "售后人员",
            "ip": "-",
            "createdAt": fmt_dt(row.get("handled_at") or row.get("updated_at") or row.get("created_at")),
        })

    for row in mysql_all(
        """
        SELECT config_id, config_key, config_name, config_value, config_type,
               description, created_at, updated_at
        FROM system_config
        WHERE config_group IN ('notice', 'notices', 'system_notice')
           OR config_key LIKE 'notice.%'
        ORDER BY updated_at DESC, created_at DESC, config_id DESC
        LIMIT 10
        """
    ):
        rows.append({
            "logId": f"notice-{row.get('config_id')}",
            "level": "info" if (row.get("description") or "published") != "failed" else "warning",
            "event": f"发布系统公告：{row.get('config_name') or row.get('config_value') or '-'}（结果：{row.get('description') or 'published'}）",
            "operation": "发布系统公告",
            "target": row.get("config_key") or "-",
            "result": row.get("description") or "published",
            "errorMessage": "",
            "actor": "超级管理员",
            "ip": "-",
            "createdAt": fmt_dt(row.get("updated_at") or row.get("created_at")),
        })

    for row in mysql_all(
        """
        SELECT admin_id, username, real_name, role, last_login_at
        FROM admin_user
        WHERE last_login_at IS NOT NULL
        ORDER BY last_login_at DESC, admin_id DESC
        LIMIT 10
        """
    ):
        rows.append({
            "logId": f"login-{row.get('admin_id')}",
            "level": "info",
            "event": f"登录系统：{row.get('username') or '-'}（结果：success）",
            "operation": "登录系统",
            "target": row.get("username") or "-",
            "result": "success",
            "errorMessage": "",
            "actor": row.get("real_name") or row.get("username") or ROLE_NAME_MAP.get(row.get("role"), "管理员"),
            "ip": "-",
            "createdAt": fmt_dt(row.get("last_login_at")),
        })

    rows = sorted(rows, key=lambda item: item.get("createdAt") or "", reverse=True)
    return rows[:limit]


@admin_bp.get("/super/security/logs")
@require_admin("super")
def security_logs():
    db_rows = mysql_all(
        """
        SELECT l.log_id, l.admin_id, l.action, l.module, l.operation_name, l.path,
               l.request_method, l.ip_address, l.params, l.result_status,
               l.error_message, l.created_at,
               COALESCE(u.real_name, u.username) AS actor_name
        FROM admin_operation_log l
        LEFT JOIN admin_user u ON u.admin_id = l.admin_id
        ORDER BY l.created_at DESC, l.log_id DESC
        LIMIT 50
        """
    )
    seed_rows = [row for row in db_rows if is_seed_audit_row(row)]
    real_rows = [row for row in db_rows if not is_seed_audit_row(row) and is_meaningful_audit_row(row)]
    rows = [format_audit_row(row) for row in real_rows]
    if len(rows) < 30:
        rows.extend(dynamic_audit_rows(30 - len(rows)))
    rows = sorted(
        rows,
        key=lambda item: item.get("createdAt") or "",
        reverse=True,
    )[:50]
    if rows:
        return response_ok({"total": len(rows), "list": rows})

    return response_ok({"total": 0, "list": []})


def alert_summary_counts(total_devices=None, online_devices=None):
    if total_devices is None:
        total_devices = count_sql("SELECT COUNT(*) AS c FROM device", fallback=0)
    if online_devices is None:
        online_devices = count_sql(f"SELECT COUNT(*) AS c FROM device WHERE {ONLINE_DEVICE_CONDITION}", fallback=0)
    log_alerts = count_sql(
        """
        SELECT COUNT(*) AS c
        FROM device_log
        WHERE COALESCE(log_type, '') IN ('alert', 'warning', 'error')
           OR COALESCE(log_level, '') IN ('warning', 'error', 'critical')
        """,
        fallback=0,
    )
    pending_feedback = count_sql(
        "SELECT COUNT(*) AS c FROM user_feedback WHERE COALESCE(status, 'open') IN ('open', 'pending')",
        fallback=0,
    )
    failed_tasks = count_sql(
        """
        SELECT COUNT(*) AS c
        FROM device_firmware_update_task
        WHERE COALESCE(status, '') IN ('failed', 'fail', 'error')
           OR COALESCE(fail_reason, '') NOT IN ('', '-')
        """,
        fallback=0,
    )
    return {
        "logAlerts": log_alerts,
        "offlineDevices": max(total_devices - online_devices, 0),
        "pendingFeedback": pending_feedback,
        "failedFirmwareTasks": failed_tasks,
    }


@admin_bp.get("/super/notices")
@require_admin("super")
def admin_notices():
    notice_sql = """
        SELECT config_id, config_key, config_value, config_type, config_name,
               description, created_at, updated_at
        FROM system_config
        WHERE config_group IN ('notice', 'notices', 'system_notice')
           OR config_key LIKE 'notice.%'
        ORDER BY updated_at DESC, created_at DESC, config_id DESC
        LIMIT 50
        """
    db_rows = mysql_all(notice_sql)
    if not db_rows:
        try:
            from db_config import get_mysql_connection
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(notice_sql)
                    db_rows = cursor.fetchall() or []
            finally:
                conn.close()
        except Exception:
            db_rows = []
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
        write_admin_audit("create_notice", "系统公告", "发布系统公告", title, "success", "", params={"noticeId": notice_key, "status": notice["status"]})
        return response_ok(notice, "notice created")

    return response_error(500, "notice create failed", "system_config is not writable")


@admin_bp.get("/super/decision/summary")
@admin_bp.get("/market/decision/summary")
@require_admin("super", "market")
def decision_summary():
    stats = daily_stats_rows(8)
    latest = stats[-1] if stats else {}
    activity = overview_activity_metrics()
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
            {"label": "活跃用户", "value": _int(activity.get("activeUserCount"), 0), "trend": ""},
            {"label": "活跃设备", "value": _int(latest.get("unique_device_count"), 0), "trend": ""},
            {"label": "平均播放时长", "value": f"{_int(latest.get('avg_play_duration_seconds'), 0)} 秒", "trend": ""},
        ],
        "trend": stats,
        "risks": risks,
    })

@admin_bp.get("/market/segments")
@require_admin("super", "market")
def market_segments():
    rows = mysql_all(
        """
        SELECT stat_date, segment_code, segment_name, user_count, active_user_count,
               avg_play_count, avg_pay_amount, retention_rate
        FROM user_value_segment_daily
        WHERE stat_date = (SELECT MAX(stat_date) FROM user_value_segment_daily)
          AND segment_code IN ('high', 'normal', 'low')
        ORDER BY user_count DESC, segment_code ASC
        """
    )
    if not rows:
        rows = mysql_all(
            """
            SELECT
                CURDATE() AS stat_date,
                COALESCE(value_level, 'normal') AS segment_code,
                CASE COALESCE(value_level, 'normal')
                    WHEN 'high' THEN '高价值用户'
                    WHEN 'low' THEN '低价值用户'
                    ELSE '普通用户'
                END AS segment_name,
                COUNT(*) AS user_count,
                COUNT(CASE WHEN active_level='high' THEN 1 END) AS active_user_count,
                0 AS avg_play_count,
                0 AS avg_pay_amount,
                COUNT(CASE WHEN active_level='high' THEN 1 END) / GREATEST(COUNT(*), 1) AS retention_rate
            FROM user_profile
            WHERE value_level IN ('high', 'normal', 'low') OR value_level IS NULL OR value_level = ''
            GROUP BY COALESCE(value_level, 'normal')
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
                    "retentionRate": ratio(row.get("retention_rate"), 1),
                    "action": "按日报分群运营",
                }
                for row in rows
            ],
        })

    return response_ok({"total": 0, "list": []})



@admin_bp.get("/market/insights")
@require_admin("super", "market")
def market_insights():
    cohort_filter = "u.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) AND u.created_at <= NOW()"
    new_users = count_sql(f"SELECT COUNT(*) AS c FROM `user` u WHERE {cohort_filter}")
    bound_users = count_sql(
        f"""
        SELECT COUNT(DISTINCT u.user_id) AS c
        FROM `user` u
        JOIN user_device_binding b ON b.user_id = u.user_id
        WHERE {cohort_filter}
          AND (b.bind_time IS NULL OR b.bind_time >= u.created_at)
          AND (b.bind_time IS NULL OR b.bind_time <= NOW())
        """
    )
    first_play_users = count_sql(
        f"""
        SELECT COUNT(*) AS c
        FROM (
            SELECT u.user_id
            FROM `user` u
            JOIN user_device_binding b ON b.user_id = u.user_id
            JOIN play_history ph ON ph.user_id = u.user_id
            WHERE {cohort_filter}
              AND (b.bind_time IS NULL OR b.bind_time >= u.created_at)
              AND (b.bind_time IS NULL OR b.bind_time <= NOW())
              AND ph.created_at >= COALESCE(b.bind_time, u.created_at)
              AND ph.created_at <= NOW()
            GROUP BY u.user_id
        ) x
        """
    )
    retained_users = count_sql(
        f"""
        SELECT COUNT(*) AS c
        FROM (
            SELECT
                u.user_id,
                MIN(ph.created_at) AS first_play_at,
                MAX(ph.created_at) AS last_play_at,
                COUNT(DISTINCT DATE(ph.created_at)) AS play_days
            FROM `user` u
            JOIN user_device_binding b ON b.user_id = u.user_id
            JOIN play_history ph ON ph.user_id = u.user_id
            WHERE {cohort_filter}
              AND (b.bind_time IS NULL OR b.bind_time >= u.created_at)
              AND (b.bind_time IS NULL OR b.bind_time <= NOW())
              AND ph.created_at >= COALESCE(b.bind_time, u.created_at)
              AND ph.created_at <= NOW()
            GROUP BY u.user_id
            HAVING play_days >= 2
               AND last_play_at >= DATE_ADD(first_play_at, INTERVAL 1 DAY)
               AND last_play_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) x
        """
    )
    bound_users = min(bound_users, new_users)
    first_play_users = min(first_play_users, bound_users)
    retained_users = min(retained_users, first_play_users)
    base = max(new_users, 1)
    recommendation_rows = _system_config_group_rows("market_recommendation", 20)
    recommendations = [
        row.get("config_value") or row.get("config_name") or row.get("description")
        for row in recommendation_rows
        if row.get("config_value") or row.get("config_name") or row.get("description")
    ]
    if not recommendations:
        if new_users and bound_users < new_users:
            recommendations.append("新增用户中仍有未绑定设备用户，优先推送配网和绑定引导。")
        if bound_users and first_play_users < bound_users:
            recommendations.append("已绑定设备但未完成首播的用户，需要用欢迎歌单和使用教程促进首播。")
        if first_play_users and retained_users < first_play_users:
            recommendations.append("首播用户最近 7 天活跃不足，建议推送个性化歌单和定时播放提醒。")
        high_active_users = count_sql("SELECT COUNT(*) AS c FROM user_profile WHERE active_level='high'")
        if high_active_users:
            recommendations.append("高活跃用户适合会员权益、复购活动和高频歌单推荐。")
        if not recommendations:
            recommendations.append("当前数据量不足，先生成模拟数据并运行每日汇总，再观察新增、绑定、首播和活跃漏斗。")
    return response_ok({
        "funnels": [
            {"label": "新增用户", "value": new_users, "rate": ratio(new_users, base)},
            {"label": "绑定设备", "value": bound_users, "rate": ratio(bound_users, base)},
            {"label": "完成首播", "value": first_play_users, "rate": ratio(first_play_users, base)},
            {"label": "7 日活跃", "value": retained_users, "rate": ratio(retained_users, base)},
        ],
        "recommendations": recommendations,
    })

@admin_bp.get("/operator/device/groups")
@require_admin("super", "operator")
def device_groups():
    rows = mysql_all(
        f"""
        SELECT
            COALESCE(model_name, '未知型号') AS group_name,
            COUNT(*) AS device_count,
            SUM(CASE WHEN {ONLINE_DEVICE_CONDITION} THEN 1 ELSE 0 END) AS online_count,
            GROUP_CONCAT(DISTINCT COALESCE(firmware_version, '-') ORDER BY firmware_version SEPARATOR '、') AS firmware_versions
        FROM device
        GROUP BY COALESCE(model_name, '未知型号')
        ORDER BY device_count DESC, group_name ASC
        """
    )
    result = [
        {
            "groupName": row.get("group_name") or "未知型号",
            "deviceCount": _int(row.get("device_count"), 0),
            "onlineCount": _int(row.get("online_count"), 0),
            "offlineCount": max(_int(row.get("device_count"), 0) - _int(row.get("online_count"), 0), 0),
            "firmwareVersions": row.get("firmware_versions") or "-",
        }
        for row in rows
    ]
    return response_ok({"total": sum(item["deviceCount"] for item in result), "groupTotal": len(result), "list": result})


@admin_bp.get("/operator/device/alerts")
@require_admin("super", "operator")
def device_alerts():
    summary_counts = alert_summary_counts()
    rows = []
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
        rows.extend([
            {
                "alertId": row.get("log_id"),
                "level": row.get("log_level") or "warning",
                "title": row.get("title") or row.get("content") or "-",
                "deviceName": row.get("device_name") or "-",
                "status": "open",
                "createdAt": fmt_dt(row.get("created_at")),
            }
            for row in db_rows
        ])

    offline_rows = mysql_all(
        f"""
        SELECT device_id, device_number, device_name, model_name, last_active
        FROM device
        WHERE NOT ({ONLINE_DEVICE_CONDITION})
        ORDER BY last_active ASC, device_id ASC
        LIMIT 20
        """
    )
    rows.extend([
        {
            "alertId": f"offline-{row.get('device_id')}",
            "level": "warning",
            "title": "设备离线",
            "deviceName": row.get("device_name") or row.get("device_number") or row.get("model_name") or "-",
            "status": "open",
            "createdAt": fmt_dt(row.get("last_active")),
        }
        for row in offline_rows
    ])

    task_rows = mysql_all(
        """
        SELECT t.task_id, t.task_no, t.device_id, t.target_version, t.status,
               t.fail_reason, t.updated_at, t.created_at,
               d.device_name, d.device_number, d.model_name
        FROM device_firmware_update_task t
        LEFT JOIN device d ON d.device_id = t.device_id
        WHERE COALESCE(t.status, '') IN ('failed', 'fail', 'error')
           OR COALESCE(t.fail_reason, '') NOT IN ('', '-')
        ORDER BY t.updated_at DESC, t.created_at DESC, t.task_id DESC
        LIMIT 20
        """
    )
    rows.extend([
        {
            "alertId": f"firmware-{row.get('task_id')}",
            "level": "critical",
            "title": row.get("fail_reason") or f"固件升级失败：{row.get('target_version') or '-'}",
            "deviceName": row.get("device_name") or row.get("device_number") or row.get("model_name") or (f"device {row.get('device_id')}" if row.get("device_id") else "全部设备"),
            "status": "open",
            "createdAt": fmt_dt(row.get("updated_at") or row.get("created_at")),
        }
        for row in task_rows
    ])

    rows = sorted(
        rows,
        key=lambda item: (0 if item.get("level") == "critical" else 1, item.get("createdAt") or ""),
        reverse=False,
    )[:50]
    total = summary_counts.get("logAlerts", 0) + summary_counts.get("offlineDevices", 0) + summary_counts.get("failedFirmwareTasks", 0)
    return response_ok({"total": total or len(rows), "summary": summary_counts, "list": rows})



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

    write_admin_audit(
        "handle_feedback",
        "用户反馈",
        "处理用户反馈",
        feedback_id,
        "success",
        "",
        params={"status": status, "remark": remark},
    )
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
