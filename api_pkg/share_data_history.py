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


def _listening_summary(user_id):
    summary = mysql_one(
        """
        SELECT
            COALESCE(SUM(play_duration), 0) AS total_seconds,
            COUNT(*) AS play_count,
            COUNT(DISTINCT mapping_id) AS song_count
        FROM play_history
        WHERE user_id=%s
        """,
        (user_id,),
    ) or {}
    style = mysql_one(
        """
        SELECT COALESCE(style, 'unknown') AS style_name, COUNT(*) AS count_value
        FROM play_history
        WHERE user_id=%s
        GROUP BY COALESCE(style, 'unknown')
        ORDER BY count_value DESC
        LIMIT 1
        """,
        (user_id,),
    ) or {}
    hour = mysql_one(
        """
        SELECT HOUR(created_at) AS hour_value, COUNT(*) AS count_value
        FROM play_history
        WHERE user_id=%s AND created_at IS NOT NULL
        GROUP BY HOUR(created_at)
        ORDER BY count_value DESC
        LIMIT 1
        """,
        (user_id,),
    ) or {}
    total_users = mysql_one("SELECT COUNT(*) AS count_value FROM `user`") or {}
    ahead_users = mysql_one(
        """
        SELECT COUNT(*) AS count_value
        FROM (
            SELECT user_id, COUNT(*) AS play_count
            FROM play_history
            GROUP BY user_id
            HAVING play_count > %s
        ) ranked_users
        """,
        (int(summary.get("play_count") or 0),),
    ) or {}

    total = max(int(total_users.get("count_value") or 1), 1)
    ahead = int(ahead_users.get("count_value") or 0)
    rank_percent = max(1, min(99, int(((ahead + 1) / total) * 100)))
    start_hour = int(hour.get("hour_value") or 21)
    end_hour = (start_hour + 2) % 24

    return {
        "minutes": int((summary.get("total_seconds") or 0) / 60),
        "songCount": int(summary.get("song_count") or 0),
        "favoriteStyle": str(style.get("style_name") or "unknown"),
        "activeTime": f"{start_hour:02d}:00-{end_hour:02d}:00",
        "topPercent": f"Top {rank_percent}%",
        "playCount": int(summary.get("play_count") or 0),
    }


def _weekly_report_data(user_id):
    summary = _listening_summary(user_id)
    artist = mysql_one(
        """
        SELECT mm.artist, COUNT(*) AS count_value
        FROM play_history ph
        LEFT JOIN media_mapping mm ON mm.mapping_id=ph.mapping_id
        WHERE ph.user_id=%s
        GROUP BY mm.artist
        ORDER BY count_value DESC
        LIMIT 1
        """,
        (user_id,),
    ) or {}
    style = mysql_one(
        """
        SELECT COALESCE(style, 'unknown') AS style_name, COUNT(*) AS count_value
        FROM play_history
        WHERE user_id=%s
        GROUP BY COALESCE(style, 'unknown')
        ORDER BY count_value DESC
        LIMIT 1
        """,
        (user_id,),
    ) or {}
    return {
        "summary": summary,
        "topArtist": {
            "artistName": artist.get("artist") or "Unknown Artist",
            "songCount": int(artist.get("count_value") or 0),
        },
        "topPlaylist": {
            "playlistName": str(style.get("style_name") or "unknown").title(),
            "playCount": int(style.get("count_value") or 0),
        },
    }


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
    summary = _listening_summary(user_id)
    return plain(
        {
            "code": 200,
            "data": {
                "minutes": summary["minutes"],
                "songCount": summary["songCount"],
                "favoriteStyle": summary["favoriteStyle"],
                "activeTime": summary["activeTime"],
                "topPercent": summary["topPercent"],
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

    report = _weekly_report_data(current_user_id())
    summary = report["summary"]

    return ok(
        "获取个人听歌总结成功",
        {
            "year": year,
            "week": week,
            "rank": summary["topPercent"],
            "minutes": summary["minutes"],
            "compareLastWeek": "Compared with last week: stable listening activity",
            "summaryText": f"{summary['favoriteStyle'].title()} was the most played style during {summary['activeTime']}.",
            "topArtist": report["topArtist"],
            "topPlaylist": report["topPlaylist"],
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
