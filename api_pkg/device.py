from flask import jsonify, request

from . import api_bp
from .common import body_json, device_list_data, get_device, ok, plain


@api_bp.before_app_request
def legacy_device_list():
    if request.path == "/device/list" and request.method == "GET":
        return jsonify({"code": 200, "msg": "success", "data": device_list_data()}), 200


@api_bp.get("/device/list")
def device_list():
    return ok("device list success", device_list_data())


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
        "battery info success",
        {
            "deviceId": device["deviceId"],
            "battery": device["battery"],
            "estimatedPlayTime": "11h20m",
            "lowBatteryThreshold": device["lowBatteryThreshold"],
            "powerSaveEnabled": device["powerSaveEnabled"],
            "isCharging": device["isCharging"],
            "fullChargeNotice": device["fullChargeNotice"],
        },
    )


@api_bp.post("/device/power-save")
def power_save():
    body = body_json()
    return ok("power save set", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "powerSaveEnabled": bool(body.get("enabled", True))})


@api_bp.post("/device/battery-notice")
def battery_notice():
    body = body_json()

    return ok(
        "battery notice set",
        {
            "deviceId": body.get("deviceId", get_device()["deviceId"]),
            "lowBatteryEnabled": bool(body.get("lowBatteryEnabled", True)),
            "threshold": int(body.get("threshold", 20)),
            "fullChargeNotice": bool(body.get("fullChargeNotice", True)),
        },
    )


@api_bp.post("/device/rename")
def device_rename():
    body = body_json()
    name = str(body.get("name", "")).strip()

    if not name:
        return ok("device name is required", {"field": "name"}, 400)

    return ok("device renamed", {"deviceId": body.get("deviceId", get_device()["deviceId"]), "name": name})


@api_bp.post("/device/advanced-settings")
def advanced_settings():
    body = body_json()

    return ok(
        "advanced settings saved",
        {
            "deviceId": body.get("deviceId", get_device()["deviceId"]),
            "volumeLimit": int(body.get("volumeLimit", 80)),
            "nightModeEnabled": bool(body.get("nightModeEnabled", True)),
            "nightStart": body.get("nightStart", "23:00"),
            "nightEnd": body.get("nightEnd", "07:00"),
            "autoFirmwareUpdate": bool(body.get("autoFirmwareUpdate", True)),
        },
    )


@api_bp.get("/device/search-nearby")
def search_nearby():
    keyword = (request.args.get("keyword") or "").lower()
    rows = [
        {
            "deviceId": "dev_001",
            "deviceName": "客厅音箱",
            "modelName": "SH-Mini A1",
            "signalStrength": -65,
            "online": True,
            "binded": False,
        }
    ]

    if keyword:
        rows = [row for row in rows if keyword in row["deviceName"].lower() or keyword in row["modelName"].lower()]

    return ok("nearby devices found", {"total": len(rows), "list": rows})


@api_bp.post("/device/bind")
def device_bind():
    body = body_json()
    sn = str(body.get("deviceSn") or "SHMINI-A1-0001")

    return ok(
        "device binding started",
        {
            "taskId": "bind_001",
            "deviceSn": sn,
            "deviceName": "Smart Speaker",
            "status": "binding",
            "progress": 0,
        },
    )


@api_bp.get("/device/bind-progress")
def bind_progress():
    return plain(
        {
            "progress": 70,
            "steps": [
                {"name": "Discover speaker", "status": "done"},
                {"name": "Write Wi-Fi", "status": "doing"},
                {"name": "Bind account", "status": "waiting"},
            ],
        }
    )


@api_bp.post("/device/unbind")
def device_unbind():
    return ok("device unbound", {"deviceId": body_json().get("deviceId", get_device()["deviceId"]), "unbound": True})
