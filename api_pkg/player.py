from datetime import datetime

from . import api_bp
from .common import body_json, cache_song, get_device, get_song, load_state, mongo_update, ok, save_state


@api_bp.post("/player/control")
def player_control():
    body = body_json()
    action = str(body.get("action", "")).strip().lower()

    if action not in ("play", "pause", "previous", "next"):
        return ok("无效的播放控制动作", {"action": action}, 400)

    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song = get_song()
    is_playing = action != "pause"

    mongo_update(
        "player_state",
        {"device_id": device_id},
        {
            "$set": {
                "device_id": device_id,
                "song_id": song["songId"],
                "song_name": song["songName"],
                "artist": song["artist"],
                "source": body.get("source") or song["source"],
                "is_playing": is_playing,
                "last_action": action,
                "updated_at": datetime.now(),
            }
        },
    )

    mongo_update(
        "device_commands",
        {"device_id": device_id, "command_type": "player_control", "created_at": datetime.now()},
        {"$set": {"device_id": device_id, "action": action, "payload": body, "created_at": datetime.now()}},
        upsert=False,
    )

    return ok(
        "播放控制成功",
        {
            "deviceId": device_id,
            "action": action,
            "isPlaying": is_playing,
            "currentSong": {"songId": song["songId"], "songName": song["songName"], "artist": song["artist"]},
        },
    )


@api_bp.post("/player/volume")
def player_volume():
    body = body_json()

    try:
        volume = max(0, min(100, int(body.get("volume", 60))))
    except Exception:
        return ok("音量必须是 0-100 的整数", {"field": "volume"}, 400)

    device_id = str(body.get("deviceId") or get_device()["deviceId"])

    mongo_update(
        "device_runtime",
        {"device_id": device_id},
        {"$set": {"device_id": device_id, "volume": volume, "metrics.volume": volume, "updated_at": datetime.now()}},
    )

    return ok("音量设置成功", {"deviceId": device_id, "volume": volume, "isMuted": volume == 0})


@api_bp.post("/player/play-song")
def play_song():
    body = body_json()
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    requested_name = str(body.get("songName") or body.get("keyword") or "").strip()
    requested_artist = str(body.get("artist") or "").strip()
    requested_source = str(body.get("source") or "netease").strip()
    song = get_song(song_id, keyword=requested_name or None)

    if requested_name:
        song = {
            "songId": song_id or song["songId"],
            "name": requested_name,
            "songName": requested_name,
            "album": song.get("album") or "",
            "artist": requested_artist or song.get("artist") or "",
            "artistText": requested_artist or song.get("artistText") or "",
            "artists": song.get("artists") or ([requested_artist] if requested_artist else []),
            "coverUrl": str(body.get("coverUrl") or song.get("coverUrl") or ""),
            "durationMs": int(song.get("durationMs") or 0),
            "durationSeconds": int(song.get("durationSeconds") or 0),
            "source": requested_source or song.get("source") or "netease",
        }
        cache_song(song, provider="miniprogram_play_song", keyword=requested_name)

    mongo_update(
        "player_state",
        {"device_id": device_id},
        {
            "$set": {
                "device_id": device_id,
                "song_id": song_id,
                "song_name": song["songName"],
                "artist": song["artist"],
                "source": song["source"],
                "cover_url": song["coverUrl"],
                "is_playing": True,
                "updated_at": datetime.now(),
            }
        },
    )

    return ok(
        "歌曲播放成功",
        {
            "deviceId": device_id,
            "songId": song_id,
            "songName": song["songName"],
            "artist": song["artist"],
            "source": song["source"],
            "isPlaying": True,
            "playTime": 0,
        },
    )


@api_bp.post("/player/add-next")
def add_next():
    body = body_json()
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    song = get_song(song_id)

    state = load_state()
    queue = state.setdefault("queue", [])
    if song_id in [str(item.get("songId")) for item in queue]:
        return ok("该歌曲已在下一首播放队列中", {"deviceId": device_id, "songId": song_id, "queuePosition": 1}, 409)

    item = {
        "deviceId": device_id,
        "songId": song_id,
        "songName": song["songName"],
        "artist": song["artist"],
        "queuePosition": 1,
    }
    queue.insert(0, item)
    save_state(state)

    mongo_update(
        "play_queue",
        {"device_id": device_id},
        {
            "$push": {
                "queue": {
                    "$each": [
                        {
                            "song_id": song_id,
                            "song_name": song["songName"],
                            "artist": song["artist"],
                            "source": song["source"],
                            "position": 1,
                            "created_at": datetime.now(),
                        }
                    ],
                    "$position": 0,
                }
            },
            "$set": {"device_id": device_id, "updated_at": datetime.now()},
        },
    )

    return ok("已加入下一首播放", item)
