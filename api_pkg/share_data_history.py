import secrets
from datetime import datetime, timedelta

from flask import request

from . import api_bp
from .common import body_json, get_song, history_rows, mysql_exec, ok, plain


@api_bp.post("/share/song-link")
def share_song_link():
    body = body_json()
    share_id = "share_" + secrets.token_hex(4)

    return ok(
        "share link created",
        {
            "shareId": share_id,
            "songId": body.get("songId", "song_001"),
            "roomId": body.get("roomId", "room_001"),
            "shareUrl": "https://api.musicplayer.cn/share/" + share_id,
            "expireAt": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@api_bp.post("/share/song-card")
def share_song_card():
    body = body_json()
    card_id = "card_" + secrets.token_hex(4)

    return ok(
        "share card created",
        {
            "cardId": card_id,
            "songId": body.get("songId", "song_001"),
            "roomId": body.get("roomId", "room_001"),
            "imageUrl": "https://cdn.musicplayer.cn/share/" + card_id + ".png",
            "previewUrl": "https://cdn.musicplayer.cn/share/preview/" + card_id + ".png",
            "expireAt": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@api_bp.get("/listening-data/summary")
def listening_data_summary():
    return plain(
        {
            "code": 200,
            "data": {
                "minutes": 428,
                "songCount": len(history_rows(limit=200)),
                "favoriteStyle": "华语流行",
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


@api_bp.get("/listening-data/weekly-report")
def weekly_report():
    return ok(
        "weekly report success",
        {
            "year": int(request.args.get("year") or datetime.now().year),
            "week": int(request.args.get("week") or datetime.now().isocalendar().week),
            "rank": "Top 12%",
            "minutes": 428,
            "compareLastWeek": "比上周多听 23%",
            "summaryText": "夜间播放明显增加。",
            "topArtist": {"artistName": "Luna Echo", "songCount": 12},
            "topPlaylist": {"playlistName": "夜间专注", "playCount": 18},
        },
    )


@api_bp.post("/listening-data/generate-card")
def generate_card():
    body = body_json()

    return ok(
        "summary card generated",
        {
            "imageUrl": "https://xxx.com/report/week19.png",
            "year": int(body.get("year", 2026)),
            "week": int(body.get("week", 19)),
            "cardType": body.get("cardType", "weekly"),
        },
    )


@api_bp.get("/play-history/list")
def play_history_list():
    return plain(
        {
            "code": 200,
            "data": {
                "list": history_rows(
                    source=request.args.get("source"),
                    keyword=request.args.get("keyword"),
                )
            },
        }
    )


@api_bp.delete("/play-history/clear-old")
def clear_old_history():
    days = int(body_json().get("days", 30) or 30)
    deleted = mysql_exec("DELETE FROM play_history WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)", (days,)) or 18

    return ok("old history cleared", {"days": days, "deletedCount": deleted})


@api_bp.delete("/play-history/delete")
def delete_history():
    history_id = str(body_json().get("historyId", "")).strip()

    if not history_id:
        return ok("historyId is required", {"field": "historyId"}, 400)

    mysql_exec("DELETE FROM play_history WHERE history_id=%s", (history_id,))

    return ok("play history deleted", {"historyId": history_id})
