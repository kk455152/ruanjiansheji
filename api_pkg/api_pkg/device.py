from datetime import datetime

from flask import jsonify, request

from . import api_bp
from .common import (
    body_json,
    current_user_id,
    device_list,
    get_device,
    mysql_exec,
    mysql_one,
    next_id,
    ok,
    plain,
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
    device_id = request_device_id(body)
    enabled = 1 if bool(body.get("enabled", True)) else 0

    ensure_api_device_tables()
    mysql_exec(
        """
        INSERT INTO api_device_settings
        (device_id, power_save_enabled, updated_at)
        VALUES (%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
          power_save_enabled=VALUES(power_save_enabled),
          updated_at=VALUES(updated_at)
        """,
        (device_id, enabled),
    )

    return ok("省电模式设置成功", {"deviceId": device_id, "powerSaveEnabled": bool(enabled)})

@api_bp.post("/device/battery-notice")
def battery_notice():
    body = body_json()
    device_id = request_device_id(body)
    low_enabled = 1 if bool(body.get("lowBatteryEnabled", True)) else 0
    threshold = int(body.get("threshold", body.get("lowBatteryThreshold", 20)))
    full_notice = 1 if bool(body.get("fullChargeNotice", True)) else 0

    ensure_api_device_tables()
    mysql_exec(
        """
        INSERT INTO api_battery_notice_setting
        (device_id, low_battery_enabled, threshold, full_charge_notice, updated_at)
        VALUES (%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
          low_battery_enabled=VALUES(low_battery_enabled),
          threshold=VALUES(threshold),
          full_charge_notice=VALUES(full_charge_notice),
          updated_at=VALUES(updated_at)
        """,
        (device_id, low_enabled, threshold, full_notice),
    )

    return ok(
        "电量通知设置成功",
        {
            "deviceId": device_id,
            "lowBatteryEnabled": bool(low_enabled),
            "threshold": threshold,
            "fullChargeNotice": bool(full_notice),
        },
    )

@api_bp.post("/device/rename")
def device_rename():
    body = body_json()
    device_id = request_device_id(body)
    name = str(body.get("name", "")).strip()

    if not name:
        return ok("设备名称不能为空", {"field": "name"}, 400)

    ensure_api_device_tables()
    mysql_exec(
        """
        INSERT INTO api_device_settings
        (device_id, custom_device_name, updated_at)
        VALUES (%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
          custom_device_name=VALUES(custom_device_name),
          updated_at=VALUES(updated_at)
        """,
        (device_id, name),
    )

    return ok("设备名称修改成功", {"deviceId": device_id, "name": name})

@api_bp.post("/device/advanced-settings")
def advanced_settings():
    body = body_json()
    device_id = request_device_id(body)
    volume_limit = int(body.get("volumeLimit", 80))
    night_mode = 1 if bool(body.get("nightModeEnabled", True)) else 0
    night_start = str(body.get("nightStart") or body.get("nightModeStart") or "23:00")
    night_end = str(body.get("nightEnd") or body.get("nightModeEnd") or "07:00")
    auto_update = 1 if bool(body.get("autoFirmwareUpdate", True)) else 0

    ensure_api_device_tables()
    mysql_exec(
        """
        INSERT INTO api_device_settings
        (device_id, volume_limit, night_mode_enabled, night_start, night_end,
         auto_firmware_update, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
          volume_limit=VALUES(volume_limit),
          night_mode_enabled=VALUES(night_mode_enabled),
          night_start=VALUES(night_start),
          night_end=VALUES(night_end),
          auto_firmware_update=VALUES(auto_firmware_update),
          updated_at=VALUES(updated_at)
        """,
        (device_id, volume_limit, night_mode, night_start, night_end, auto_update),
    )

    return ok(
        "高级设置保存成功",
        {
            "deviceId": device_id,
            "volumeLimit": volume_limit,
            "nightModeEnabled": bool(night_mode),
            "nightStart": night_start,
            "nightEnd": night_end,
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

    rows = mysql_all_safe(
        f"""
        SELECT d.device_id, d.device_number, d.model_name, d.status
        FROM device d
        WHERE {where}
        ORDER BY d.last_active DESC
        LIMIT 20
        """,
        tuple(params),
    )

    if not rows:
        rows = [
            {"device_id": "dev_001", "device_number": "SHMINI-A1-0001", "model_name": "【兜底数据】SH-Mini A1", "status": 1},
        ]

    bound_ids = {str(x.get("device_id")) for x in device_list()}

    devices = [
        {
            "deviceId": str(row.get("device_id")),
            "deviceName": row.get("device_number") or "【兜底数据】声盒 Mini A1",
            "modelName": row.get("model_name") or "【兜底数据】SH-Mini A1",
            "signalStrength": -65,
            "online": bool(row.get("status")),
            "binded": str(row.get("device_id")) in bound_ids,
        }
        for row in rows
    ]

    return ok("搜索成功", {"total": len(devices), "list": devices})



def ensure_api_device_tables():
    mysql_exec("""
    CREATE TABLE IF NOT EXISTS api_device_settings (
      device_id VARCHAR(64) PRIMARY KEY,
      custom_device_name VARCHAR(255) DEFAULT NULL,
      power_save_enabled TINYINT(1) NOT NULL DEFAULT 0,
      volume_limit INT NOT NULL DEFAULT 80,
      night_mode_enabled TINYINT(1) NOT NULL DEFAULT 1,
      night_start VARCHAR(16) NOT NULL DEFAULT '23:00',
      night_end VARCHAR(16) NOT NULL DEFAULT '07:00',
      auto_firmware_update TINYINT(1) NOT NULL DEFAULT 1,
      updated_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    mysql_exec("""
    CREATE TABLE IF NOT EXISTS api_battery_notice_setting (
      device_id VARCHAR(64) PRIMARY KEY,
      low_battery_enabled TINYINT(1) NOT NULL DEFAULT 1,
      threshold INT NOT NULL DEFAULT 20,
      full_charge_notice TINYINT(1) NOT NULL DEFAULT 1,
      updated_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    mysql_exec("""
    CREATE TABLE IF NOT EXISTS api_device_unbind_log (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      user_id BIGINT DEFAULT NULL,
      device_id VARCHAR(64) NOT NULL,
      created_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def request_device_id(body=None):
    body = body or {}
    raw = str(body.get("deviceId") or "").strip()
    if raw:
        return raw
    try:
        return str(get_device()["deviceId"])
    except Exception:
        return "dev_001"


def mysql_all_safe(sql, params=()):
    from .common import mysql_all

    return mysql_all(sql, params)


@api_bp.post("/device/bind")
def device_bind():
    body = body_json()
    device_sn = str(body.get("deviceSn") or "").strip()

    if not device_sn:
        return ok("设备序列号不能为空", {"field": "deviceSn"}, 400)

    task_id = next_id("device_bind_task", "task_id")
    device = mysql_one("SELECT device_id, model_name FROM device WHERE device_number=%s LIMIT 1", (device_sn,))
    device_id = device.get("device_id") if device else None
    device_name = device.get("model_name") if device else "【兜底数据】声盒 Mini A1"

    mysql_exec(
        """
        INSERT INTO device_bind_task
        (task_id, user_id, device_sn, wifi_name, wifi_password, progress, current_step,
         status, error_message, device_id, created_at, updated_at, finished_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),NULL)
        """,
        (
            task_id,
            current_user_id(),
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
        row = mysql_one("SELECT * FROM device_bind_task WHERE task_id=%s LIMIT 1", (task_id,))

    if row:
        return plain(
            {
                "progress": int(row.get("progress") or 0),
                "steps": [
                    {"name": "发现【兜底数据】声盒 Mini A1", "status": "done" if int(row.get("progress") or 0) >= 20 else "doing"},
                    {"name": "写入 Wi-Fi 信息", "status": "done" if int(row.get("progress") or 0) >= 70 else "doing"},
                    {"name": "绑定到微信账号", "status": "done" if row.get("status") == "success" else "waiting"},
                ],
            }
        )

    return plain(
        {
            "progress": 70,
            "steps": [
                {"name": "发现【兜底数据】声盒 Mini A1", "status": "done"},
                {"name": "写入 Wi-Fi 信息", "status": "doing"},
                {"name": "绑定到微信账号", "status": "waiting"},
            ],
        }
    )


@api_bp.post("/device/unbind")
def device_unbind():
    body = body_json()
    device_id = request_device_id(body)

    ensure_api_device_tables()
    mysql_exec(
        """
        INSERT INTO api_device_unbind_log
        (user_id, device_id, created_at)
        VALUES (%s,%s,NOW())
        """,
        (current_user_id(), device_id),
    )

    return ok("设备解绑成功", {"deviceId": device_id, "unbound": True})