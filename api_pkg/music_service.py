from flask import request

from . import api_bp
from .common import body_json, current_user_id, load_state, mysql_exec, mysql_one, mysql_all, next_id, ok


SERVICE_NAMES = {"qq": "QQ 音乐", "netease": "网易云音乐"}


@api_bp.post("/music-service/bind")
def music_bind():
    body = body_json()
    service = str(body.get("service", "qq"))

    if service not in SERVICE_NAMES:
        return ok("不支持的音乐平台", {"service": service}, 404)

    user_id = current_user_id()
    row = mysql_one("SELECT binding_id FROM music_service_binding WHERE user_id=%s AND service=%s LIMIT 1", (user_id, service))

    if row:
        mysql_exec(
            """
            UPDATE music_service_binding
            SET account_name=%s, access_token=%s, sync_status=%s, updated_at=NOW()
            WHERE user_id=%s AND service=%s
            """,
            (body.get("accountName") or "【兜底数据】用户昵称", body.get("authCode") or "", "syncing", user_id, service),
        )
    else:
        mysql_exec(
            """
            INSERT INTO music_service_binding
            (binding_id, user_id, service, account_name, access_token, refresh_token, expires_at,
             sync_status, bound_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,NULL,%s,NOW(),NOW())
            """,
            (next_id("music_service_binding", "binding_id"), user_id, service, body.get("accountName") or "【兜底数据】用户昵称", body.get("authCode") or "", "", "syncing"),
        )

    return ok("音乐服务绑定成功", {"service": service, "bound": True, "accountName": body.get("accountName") or "【兜底数据】用户昵称"})


@api_bp.get("/music-service/list")
def music_list():
    rows = mysql_all(
        """
        SELECT service, account_name, sync_status
        FROM music_service_binding
        WHERE user_id=%s
        ORDER BY updated_at DESC
        """,
        (current_user_id(),),
    )

    if rows:
        services = [
            {
                "service": row["service"],
                "serviceName": SERVICE_NAMES.get(row["service"], row["service"]),
                "bound": True,
                "accountName": row.get("account_name") or "【兜底数据】用户昵称",
                "syncStatus": row.get("sync_status") or "synced",
            }
            for row in rows
        ]
    else:
        services = list(load_state()["music_services"].values())

    return ok("获取已绑定音乐服务成功", {"services": services})


@api_bp.get("/music-service/sync-progress")
def music_sync():
    service = request.args.get("service") or "qq"
    row = mysql_one(
        """
        SELECT sync_status
        FROM music_service_binding
        WHERE user_id=%s AND service=%s
        LIMIT 1
        """,
        (current_user_id(), service),
    )

    status = row.get("sync_status") if row else "syncing"
    progress = 100 if status == "synced" else 68

    return ok(
        "获取同步进度成功",
        {
            "service": service,
            "status": status,
            "progress": progress,
            "currentTask": "【兜底数据】正在同步收藏歌曲",
            "totalSongs": 1200,
            "syncedSongs": 780,
        },
    )


@api_bp.post("/music-service/permissions")
def music_permissions():
    body = body_json()
    service = str(body.get("service", "qq"))
    permissions = body.get("permissions") or {"readPlaylist": True, "syncHistory": True, "personalRecommend": True}

    user_id = current_user_id()
    row = mysql_one("SELECT permission_id FROM music_service_permission WHERE user_id=%s AND service=%s LIMIT 1", (user_id, service))

    values = (
        1 if permissions.get("readPlaylist") else 0,
        1 if permissions.get("syncHistory") else 0,
        1 if permissions.get("personalRecommend") else 0,
    )

    if row:
        mysql_exec(
            """
            UPDATE music_service_permission
            SET read_playlist=%s, sync_history=%s, personal_recommend=%s, updated_at=NOW()
            WHERE user_id=%s AND service=%s
            """,
            (*values, user_id, service),
        )
    else:
        mysql_exec(
            """
            INSERT INTO music_service_permission
            (permission_id, user_id, service, read_playlist, sync_history, personal_recommend, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,NOW())
            """,
            (next_id("music_service_permission", "permission_id"), user_id, service, *values),
        )

    return ok("权限修改成功", {"service": service, "permissions": permissions})


@api_bp.post("/music-service/unbind")
def music_unbind():
    service = str(body_json().get("service", "qq"))

    mysql_exec(
        "DELETE FROM music_service_binding WHERE user_id=%s AND service=%s",
        (current_user_id(), service),
    )

    return ok("解绑成功", {"service": service, "unbound": True})
