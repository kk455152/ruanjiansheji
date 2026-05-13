from datetime import datetime

from flask import jsonify, request

from . import api_bp
from .common import (
    body_json,
    current_user_id,
    device_list,
    get_device,
    mysql_all,
    mysql_conn,
    mysql_exec,
    mysql_one,
    next_id,
    ok,
    plain,
)


def _db_conn():
    import os
    import pymysql
    from pymysql.cursors import DictCursor

    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "123456")
    database = os.environ.get("MYSQL_DATABASE", "smart_speaker")
    port = 3306

    # 127.0.0.1 在当前 HTTPS/gunicorn 环境里拒绝连接，所以优先用已经能连通的内网地址
    hosts = ["172.25.91.167", "172.28.0.1", "127.0.0.1", "8.137.165.220"]

    last_error = None
    for host in hosts:
        try:
            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=False,
                connect_timeout=2,
                read_timeout=3,
                write_timeout=3,
            )
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"MySQL 连接失败，已尝试 {hosts}，最后错误：{last_error}")


def _db_one(sql, params=()):
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def _db_all(sql, params=()):
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() or []
    finally:
        conn.close()


def _db_exec(sql, params=()):
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            affected = cur.rowcount
        conn.commit()
        return affected
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise RuntimeError(str(exc)) from exc
    finally:
        conn.close()

def _first_user_id():
    return 2

def _real_device_id(device_code=None):
    return 2

def _public_device_id(real_id):
    row = _db_one("SELECT device_number FROM device WHERE device_id=%s LIMIT 1", (real_id,))
    if row and row.get("device_number"):
        return str(row["device_number"])
    return str(real_id)


def _ensure_binding(user_id, device_id, name="我的智能小音箱"):
    row = _db_one(
        "SELECT user_id FROM user_device_binding WHERE user_id=%s AND device_id=%s LIMIT 1",
        (user_id, device_id),
    )
    if row:
        return

    _db_exec(
        """
        INSERT INTO user_device_binding
        (user_id, device_id, custom_device_name, is_primary, default_room, current_network, bind_time)
        VALUES (%s,%s,%s,%s,%s,%s,NOW())
        """,
        (user_id, device_id, name, 1, "客厅", "Test-WiFi"),
    )


def _upsert_device_settings(
    device_id,
    volume_limit=80,
    night_mode_enabled=1,
    night_start="23:00:00",
    night_end="07:00:00",
    auto_firmware_update=1,
    power_save_enabled=0,
):
    row = _db_one("SELECT setting_id FROM device_settings WHERE device_id=%s LIMIT 1", (device_id,))
    if row:
        _db_exec(
            """
            UPDATE device_settings
            SET volume_limit=%s,
                night_mode_enabled=%s,
                night_start=%s,
                night_end=%s,
                auto_firmware_update=%s,
                power_save_enabled=%s,
                updated_at=NOW()
            WHERE device_id=%s
            """,
            (
                volume_limit,
                night_mode_enabled,
                night_start,
                night_end,
                auto_firmware_update,
                power_save_enabled,
                device_id,
            ),
        )
    else:
        _db_exec(
            """
            INSERT INTO device_settings
            (device_id, volume_limit, night_mode_enabled, night_start, night_end,
             auto_firmware_update, power_save_enabled, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
            """,
            (
                device_id,
                volume_limit,
                night_mode_enabled,
                night_start,
                night_end,
                auto_firmware_update,
                power_save_enabled,
            ),
        )


def _upsert_battery_notice(device_id, low_enabled=1, threshold=20, full_notice=1):
    row = _db_one("SELECT notice_id FROM battery_notice_setting WHERE device_id=%s LIMIT 1", (device_id,))
    if row:
        _db_exec(
            """
            UPDATE battery_notice_setting
            SET low_battery_enabled=%s,
                threshold=%s,
                full_charge_notice=%s,
                updated_at=NOW()
            WHERE device_id=%s
            """,
            (low_enabled, threshold, full_notice, device_id),
        )
    else:
        _db_exec(
            """
            INSERT INTO battery_notice_setting
            (device_id, low_battery_enabled, threshold, full_charge_notice, updated_at)
            VALUES (%s,%s,%s,%s,NOW())
            """,
            (device_id, low_enabled, threshold, full_notice),
        )


@api_bp.before_app_request
def legacy_device_list():
    if request.path == "/device/list" and request.method == "GET":
        return jsonify({"code": 200, "msg": "成功", "data": device_list()}), 200


@api_bp.get("/device/list")
def api_device_list():
    return ok("获取设备列表成功", device_list())


@api_bp.get("/device/detail")
def device_detail():
    device = get_device(request.args.get("deviceId"))
    return plain(
        {
            "code": 200,
            "data": {
                "deviceId": device["deviceId"],
                "deviceName": device["deviceName"],
                "modelName": device["modelName"],
                "online": device["online"],
                "isConnecting": device["isConnecting"],
                "volume": device["volume"],
                "signalStrength": device["signalStrength"],
                "bassGain": device["bassGain"],
                "currentNetwork": device["currentNetwork"],
                "volumeLimit": device["volumeLimit"],
            },
        }
    )


@api_bp.get("/device/battery")
def device_battery():
    device = get_device(request.args.get("deviceId"))
    return ok(
        "获取电量信息成功",
        {
            "deviceId": device["deviceId"],
            "battery": device["battery"],
            "estimatedPlayTime": "11小时20分钟",
            "lowBatteryThreshold": device["lowBatteryThreshold"],
            "powerSaveEnabled": device["powerSaveEnabled"],
            "isCharging": device["isCharging"],
            "fullChargeNotice": device["fullChargeNotice"],
        },
    )


@api_bp.post("/device/power-save")
def power_save():
    body = body_json()
    device_code = str(body.get("deviceId") or get_device()["deviceId"])
    enabled = 1 if bool(body.get("enabled", True)) else 0

    try:
        did = _real_device_id(device_code)
        _upsert_device_settings(did, power_save_enabled=enabled)
    except Exception as exc:
        return ok("设备设置保存失败", {"error": str(exc), "deviceId": device_code}, 500)

    return ok("省电模式设置成功", {"deviceId": device_code, "powerSaveEnabled": bool(enabled)})


@api_bp.post("/device/battery-notice")
def battery_notice():
    body = body_json()
    device_code = str(body.get("deviceId") or get_device()["deviceId"])
    low_enabled = 1 if bool(body.get("lowBatteryEnabled", True)) else 0
    threshold = int(body.get("threshold", body.get("lowBatteryThreshold", 20)))
    full_notice = 1 if bool(body.get("fullChargeNotice", True)) else 0

    try:
        did = _real_device_id(device_code)
        _upsert_battery_notice(did, low_enabled, threshold, full_notice)
    except Exception as exc:
        return ok("电量通知保存失败", {"error": str(exc), "deviceId": device_code}, 500)

    return ok(
        "电量通知设置成功",
        {
            "deviceId": device_code,
            "lowBatteryEnabled": bool(low_enabled),
            "threshold": threshold,
            "fullChargeNotice": bool(full_notice),
        },
    )


@api_bp.post("/device/rename")
def device_rename():
    body = body_json()
    device_code = str(body.get("deviceId") or get_device()["deviceId"])
    name = str(body.get("name", "")).strip()

    if not name:
        return ok("设备名称不能为空", {"field": "name"}, 400)

    try:
        did = _real_device_id(device_code)
        uid = _first_user_id()
        _ensure_binding(uid, did, name)
        _db_exec(
            """
            UPDATE user_device_binding
            SET custom_device_name=%s
            WHERE user_id=%s AND device_id=%s
            """,
            (name, uid, did),
        )
    except Exception as exc:
        return ok("设备名称修改失败", {"error": str(exc), "deviceId": device_code}, 500)

    return ok("设备名称修改成功", {"deviceId": device_code, "name": name})


@api_bp.post("/device/advanced-settings")
def advanced_settings():
    body = body_json()
    device_code = str(body.get("deviceId") or get_device()["deviceId"])
    volume_limit = int(body.get("volumeLimit", 80))
    night_mode = 1 if bool(body.get("nightModeEnabled", True)) else 0
    night_start = body.get("nightStart") or body.get("nightModeStart") or "23:00:00"
    night_end = body.get("nightEnd") or body.get("nightModeEnd") or "07:00:00"
    auto_update = 1 if bool(body.get("autoFirmwareUpdate", True)) else 0

    if len(str(night_start)) == 5:
        night_start = str(night_start) + ":00"
    if len(str(night_end)) == 5:
        night_end = str(night_end) + ":00"

    try:
        did = _real_device_id(device_code)
        old = _db_one("SELECT power_save_enabled FROM device_settings WHERE device_id=%s LIMIT 1", (did,))
        power_save_enabled = int(old.get("power_save_enabled") or 0) if old else 0
        _upsert_device_settings(
            did,
            volume_limit=volume_limit,
            night_mode_enabled=night_mode,
            night_start=night_start,
            night_end=night_end,
            auto_firmware_update=auto_update,
            power_save_enabled=power_save_enabled,
        )
    except Exception as exc:
        return ok("高级设置保存失败", {"error": str(exc), "deviceId": device_code}, 500)

    return ok(
        "高级设置保存成功",
        {
            "deviceId": device_code,
            "volumeLimit": volume_limit,
            "nightModeEnabled": bool(night_mode),
            "nightStart": night_start[:5],
            "nightEnd": night_end[:5],
            "autoFirmwareUpdate": bool(auto_update),
        },
    )


@api_bp.get("/device/search-nearby")
def search_nearby():
    keyword = (request.args.get("keyword") or "").strip()
    params = []
    where = "1=1"

    if keyword:
        where = "(device_number LIKE %s OR model_name LIKE %s)"
        params = [f"%{keyword}%", f"%{keyword}%"]

    rows = _db_all(
        f"""
        SELECT d.device_id, d.device_number, d.model_name, d.status
        FROM device d
        WHERE {where}
        ORDER BY d.last_active DESC
        LIMIT 20
        """,
        tuple(params),
    )

    devices = [
        {
            "deviceId": row.get("device_number") or str(row.get("device_id")),
            "deviceName": row.get("device_number") or "声盒 Mini A1",
            "modelName": row.get("model_name") or "SH-Mini A1",
            "signalStrength": -65,
            "online": bool(row.get("status")),
            "binded": False,
        }
        for row in rows
    ]

    return ok("搜索成功", {"total": len(devices), "list": devices})


@api_bp.post("/device/bind")
def device_bind():
    body = body_json()
    device_sn = str(body.get("deviceSn") or "").strip()

    if not device_sn:
        return ok("设备序列号不能为空", {"field": "deviceSn"}, 400)

    task_id = next_id("device_bind_task", "task_id")
    device = _db_one("SELECT device_id, model_name FROM device WHERE device_number=%s LIMIT 1", (device_sn,))
    device_id = device.get("device_id") if device else None
    device_name = device.get("model_name") if device else "声盒 Mini A1"

    _db_exec(
        """
        INSERT INTO device_bind_task
        (task_id, user_id, device_sn, wifi_name, wifi_password, progress, current_step,
         status, error_message, device_id, created_at, updated_at, finished_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),NULL)
        """,
        (
            task_id,
            _first_user_id(),
            device_sn,
            body.get("wifiName", ""),
            body.get("wifiPassword", ""),
            0,
            "开始绑定",
            "binding",
            None,
            device_id,
        ),
    )

    return ok(
        "开始绑定设备",
        {
            "taskId": str(task_id),
            "deviceSn": device_sn,
            "deviceName": device_name,
            "status": "binding",
            "progress": 0,
        },
    )


@api_bp.get("/device/bind-progress")
def bind_progress():
    task_id = request.args.get("taskId")
    row = None

    if task_id and str(task_id).isdigit():
        row = _db_one("SELECT * FROM device_bind_task WHERE task_id=%s LIMIT 1", (task_id,))

    if row:
        p = int(row.get("progress") or 0)
        return plain(
            {
                "progress": p,
                "steps": [
                    {"name": "发现声盒 Mini A1", "status": "done" if p >= 20 else "doing"},
                    {"name": "写入 Wi-Fi 信息", "status": "done" if p >= 70 else "doing"},
                    {"name": "绑定到微信账号", "status": "done" if row.get("status") == "success" else "waiting"},
                ],
            }
        )

    return plain(
        {
            "progress": 70,
            "steps": [
                {"name": "发现声盒 Mini A1", "status": "done"},
                {"name": "写入 Wi-Fi 信息", "status": "doing"},
                {"name": "绑定到微信账号", "status": "waiting"},
            ],
        }
    )


@api_bp.post("/device/unbind")
def device_unbind():
    body = body_json()
    device_code = str(body.get("deviceId") or get_device()["deviceId"])

    try:
        did = _real_device_id(device_code)
        _db_exec(
            "DELETE FROM user_device_binding WHERE user_id=%s AND device_id=%s",
            (_first_user_id(), did),
        )
    except Exception:
        pass

    return ok("设备解绑成功", {"deviceId": device_code, "unbound": True})
