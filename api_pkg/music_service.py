from . import api_bp
from .common import body_json, load_state, ok


SERVICE_NAMES = {"qq": "QQ 音乐", "netease": "网易云音乐"}


@api_bp.post("/music-service/bind")
def music_bind():
    service = str(body_json().get("service", "qq"))

    if service not in SERVICE_NAMES:
        return ok("unsupported music service", {"service": service}, 404)

    return ok("music service bound", {"service": service, "bound": True, "accountName": "Music User"})


@api_bp.get("/music-service/list")
def music_list():
    return ok("music service list success", {"services": list(load_state()["music_services"].values())})


@api_bp.get("/music-service/sync-progress")
def music_sync():
    from flask import request

    service = request.args.get("service") or "qq"

    return ok(
        "sync progress success",
        {
            "service": service,
            "status": "syncing",
            "progress": 68,
            "currentTask": "Syncing favorite songs",
            "totalSongs": 1200,
            "syncedSongs": 780,
        },
    )


@api_bp.post("/music-service/permissions")
def music_permissions():
    body = body_json()

    return ok(
        "permissions updated",
        {
            "service": body.get("service", "qq"),
            "permissions": body.get("permissions") or {"readPlaylist": True, "syncHistory": True, "personalRecommend": True},
        },
    )


@api_bp.post("/music-service/unbind")
def music_unbind():
    return ok("music service unbound", {"service": body_json().get("service", "qq"), "unbound": True})
