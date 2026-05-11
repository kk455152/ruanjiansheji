from datetime import datetime

from . import api_bp
from .common import body_json, get_device, get_song, load_state, mongo_update, ok, save_state


@api_bp.post("/player/control")
def player_control():
    body = body_json()
    action = str(body.get("action", "")).lower()

    if action not in ("play", "pause", "previous", "next"):
        return ok("invalid player action", {"action": action}, 400)

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
                "updated_at": datetime.now(),
            }
        },
    )

    return ok(
        "player control success",
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
        return ok("invalid volume", {"field": "volume"}, 400)

    device_id = str(body.get("deviceId") or get_device()["deviceId"])

    mongo_update(
        "device_runtime",
        {"device_id": device_id},
        {"$set": {"device_id": device_id, "metrics.volume": volume, "updated_at": datetime.now()}},
    )

    return ok("volume set success", {"deviceId": device_id, "volume": volume, "isMuted": volume == 0})


@api_bp.post("/player/play-song")
def play_song():
    body = body_json()
    device_id = str(body.get("deviceId") or get_device()["deviceId"])
    song_id = str(body.get("songId") or get_song()["songId"])
    song = get_song(song_id)

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
                "is_playing": True,
                "updated_at": datetime.now(),
            }
        },
    )

    return ok(
        "song play success",
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

    state = load_state()
    if song_id in [str(item.get("songId")) for item in state.get("queue", [])]:
        return ok("song already queued next", {"deviceId": device_id, "songId": song_id, "queuePosition": 1}, 409)

    song = get_song(song_id)
    item = {
        "deviceId": device_id,
        "songId": song_id,
        "songName": song["songName"],
        "artist": song["artist"],
        "queuePosition": 1,
    }

    state.setdefault("queue", []).insert(0, item)
    save_state(state)

    mongo_update(
        "play_queue",
        {"device_id": device_id},
        {
            "$push": {
                "queue": {
                    "$each": [{"song_id": song_id, "song_name": song["songName"], "artist": song["artist"], "position": 1}],
                    "$position": 0,
                }
            },
            "$set": {"updated_at": datetime.now()},
        },
    )

    return ok("song queued next", item)
