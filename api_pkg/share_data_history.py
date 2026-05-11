from datetime import datetime, timedelta

from flask import request

from . import api_bp
from .common import (
    body_json,
    current_user_id,
    get_song,
    history_rows,
    mysql_exec,
    mysql_one,
    next_id,
    ok,
    plain,
)


@api_bp.post("/share/song-link")
def share_song_link():
    body = body_json()
    share_id = next_id("share_record", "share_id")
    song_id = str(body.get("songId") or get_song()["songId"])
    room_id = body.get("roomId")
    expire_at = datetime.now() + timedelta(days=7)
    share_url = "https://api.musicplayer.cn/share/" + str(share_id)

    mysql_exec(
        """
        INSERT INTO share_record
        (share_id, user_id, song_id, room_id, share_type, share_url, image_url, expire_at, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """,
        (share_id, current_user_id(), song_id, int(room_id) if str(room_id).isdigit() else None, "link", share_url, None, expire_at),
    )

    return ok(
        "分享链接生成成功",
        {
            "shareId": str(share_id),
            "songId": song_id,
            "roomId": room_id or "room_001",
            "shareUrl": share_url,
            "expireAt": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@api_bp.post("/share/song-card")
def share_song_card():
    body = body_json()
    song_id = str(body.get("songId") or get_song()["songId"])
    room_id = body.get("roomId")

    if not song_id:
        return ok("歌曲 ID 不能为空", {"field": "songId"}, 400)

    share_id = next_id("share_record", "share_id")
    expire_at = datetime.now() + timedelta(days=7)
    image_url = f"https://cdn.musicplayer.cn/share/card_{share_id}.png"

    mysql_exec(
        """
        INSERT INTO share_record
        (share_id, user_id, song_id, room_id, share_type, share_url, image_url, expire_at, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """,
        (share_id, current_user_id(), song_id, int(room_id) if str(room_id).isdigit() else None, "card", None, image_url, expire_at),
    )

    return ok(
        "分享卡片生成成功",
        {
            "cardId": str(share_id),
            "songId": song_id,
            "roomId": room_id or "room_001",
            "imageUrl": image_url,
            "previewUrl": image_url,
            "expireAt": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@api_bp.get("/listening-data/summary")
def listening_data_summary():
    user_id = current_user_id()
    row = mysql_one(
        """
        SELECT *
        FROM Daily_Stats
        WHERE user_id=%s
        ORDER BY stat_date DESC
        LIMIT 1
        """,
        (user_id,),
    )

    if row:
        return plain(
            {
                "code": 200,
                "data": {
                    "minutes": int((row.get("total_play_duration_seconds") or 0) / 60),
                    "songCount": int(row.get("unique_song_count") or 0),
                    "favoriteStyle": "【兜底数据】华语流行",
                    "activeTime": "21:00-23:00",
                    "topPercent": "Top 12%",
                },
            }
        )

    return plain(
        {
            "code": 200,
            "data": {
                "minutes": 428,
                "songCount": len(history_rows(user_id=user_id, limit=200)),
                "favoriteStyle": "【兜底数据】华语流行",
                "activeTime": "21:00-23:00",
                "topPercent": "Top 12%",
            },
        }
    )


@api_bp.get("/song-info")
def song_info():
    song = get_song(request.args.get("songId") or "1491830535")

    return plain(
        {
            "code": 200,
            "data": {
                "songId": song["songId"],
                "name": song["name"],
                "album": song["album"],
                "artistText": song["artistText"],
                "artists": song["artists"],
                "coverUrl": song["coverUrl"],
                "durationMs": song["durationMs"],
                "durationSeconds": song["durationSeconds"],
                "source": song["source"],
            },
        }
    )


@api_bp.get("/play-history/list")
def play_history_list():
    return plain(
        {
            "code": 200,
            "data": {
                "list": history_rows(
                    user_id=current_user_id(),
                    source=request.args.get("source"),
                    keyword=request.args.get("keyword"),
                    limit=int(request.args.get("pageSize") or 50),
                )
            },
        }
    )


@api_bp.delete("/play-history/clear-old")
def clear_old_history():
    body = body_json()
    days = int(body.get("days", 30) or 30)

    deleted = mysql_exec(
        """
        DELETE FROM play_history
        WHERE user_id=%s AND COALESCE(played_at, created_at) < DATE_SUB(NOW(), INTERVAL %s DAY)
        """,
        (current_user_id(), days),
    )

    return ok(f"{days} 天前播放历史清理成功", {"days": days, "deletedCount": int(deleted or 0)})


@api_bp.delete("/play-history/delete")
def delete_history():
    history_id = str(body_json().get("historyId", "")).strip()

    if not history_id:
        return ok("历史记录 ID 不能为空", {"field": "historyId"}, 400)

    mysql_exec("DELETE FROM play_history WHERE user_id=%s AND history_id=%s", (current_user_id(), history_id))

    return ok("播放历史删除成功", {"historyId": history_id})


@api_bp.get("/listening-data/weekly-report")
def weekly_report():
    year = int(request.args.get("year") or datetime.now().year)
    week = int(request.args.get("week") or datetime.now().isocalendar().week)

    if week < 1 or week > 53:
        return ok("请求参数错误", {"field": "week", "reason": "week 必须是 1-53 之间的整数"}, 400)

    row = mysql_one(
        """
        SELECT *
        FROM Daily_Stats
        WHERE user_id=%s
        ORDER BY stat_date DESC
        LIMIT 1
        """,
        (current_user_id(),),
    )

    minutes = int((row.get("total_play_duration_seconds") or 0) / 60) if row else 428
    top_artist = row.get("hottest_artist") if row else "【兜底数据】Luna Echo"
    top_count = int(row.get("hottest_play_count") or 12) if row else 12

    return ok(
        "获取个人听歌总结成功",
        {
            "year": year,
            "week": week,
            "rank": "Top 12%",
            "minutes": minutes,
            "compareLastWeek": "【兜底数据】比上周多听 23%",
            "summaryText": "【兜底数据】夜间播放和轻音乐占比明显上升。",
            "topArtist": {"artistName": top_artist, "songCount": top_count},
            "topPlaylist": {"playlistName": "【兜底数据】夜间专注", "playCount": 18},
        },
    )


@api_bp.post("/listening-data/generate-card")
def generate_card():
    body = body_json()

    return ok(
        "总结长图生成成功",
        {
            "imageUrl": "https://xxx.com/report/week19.png",
            "year": int(body.get("year", 2026)),
            "week": int(body.get("week", 19)),
            "cardType": body.get("cardType", "weekly"),
        },
    )
