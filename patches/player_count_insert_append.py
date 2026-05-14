# === C_COUNT_INSERT_START ===
# C 组联调验收记录：
# 不改变原接口返回逻辑，只在接口成功后额外写入 MongoDB 记录，
# 让数据库中的记录数量发生真实变化，方便观察台和截图验证。
@api_bp.after_app_request
def c_count_insert_after_request(response):
    try:
        from flask import request
        from datetime import datetime
        from db import mongo_db
        import json

        if response.status_code < 200 or response.status_code >= 300:
            return response

        path = request.path or ""

        # 实际访问路径是 /api/player/xxx，
        # player.py 里路由写的是 /player/xxx，所以这里用 endswith 最稳。
        if not (
            path.endswith("/player/volume")
            or path.endswith("/player/play-song")
            or path.endswith("/player/add-next")
        ):
            return response

        body = request.get_json(silent=True) or {}

        try:
            resp_json = json.loads(response.get_data(as_text=True) or "{}")
        except Exception:
            resp_json = {}

        resp_data = resp_json.get("data") if isinstance(resp_json.get("data"), dict) else {}

        device_id = (
            body.get("deviceId")
            or body.get("device_id")
            or resp_data.get("deviceId")
            or "dev_001"
        )
        source = body.get("source") or resp_data.get("source") or "netease"
        test_tag = body.get("testTag") or body.get("test_tag") or ""

        now = datetime.now()

        if path.endswith("/player/volume"):
            volume = body.get("volume")
            if volume is None:
                volume = resp_data.get("volume")

            mongo_db["operation_logs"].insert_one({
                "device_id": device_id,
                "action": "VOLUME_CHANGE",
                "volume": volume,
                "source": source,
                "test_tag": test_tag,
                "created_at": now,
                "from_api": path,
            })

            mongo_db["device_runtime"].update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "device_id": device_id,
                        "volume": volume,
                        "metrics": {"volume": volume},
                        "source": source,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )

        elif path.endswith("/player/play-song"):
            song_id = (
                body.get("songId")
                or body.get("song_id")
                or resp_data.get("songId")
                or "song_demo_001"
            )
            song_name = resp_data.get("songName") or body.get("songName") or song_id
            artist = resp_data.get("artist") or body.get("artist") or ""

            mongo_db["play_logs"].insert_one({
                "device_id": device_id,
                "song_id": song_id,
                "song_name": song_name,
                "artist": artist,
                "source": source,
                "platform": source,
                "test_tag": test_tag,
                "played_at": now,
                "created_at": now,
                "from_api": path,
            })

            mongo_db["player_state"].update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "device_id": device_id,
                        "song_id": song_id,
                        "song_name": song_name,
                        "artist": artist,
                        "source": source,
                        "is_playing": True,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )

        elif path.endswith("/player/add-next"):
            song_id = (
                body.get("songId")
                or body.get("song_id")
                or resp_data.get("songId")
                or "song_demo_next"
            )
            song_name = resp_data.get("songName") or body.get("songName") or song_id
            artist = resp_data.get("artist") or body.get("artist") or ""

            queue_item = {
                "song_id": song_id,
                "song_name": song_name,
                "artist": artist,
                "source": source,
                "test_tag": test_tag,
                "created_at": now,
                "position": resp_data.get("queuePosition") or 1,
            }

            mongo_db["play_queue"].insert_one({
                "device_id": device_id,
                "song_id": song_id,
                "song_name": song_name,
                "artist": artist,
                "source": source,
                "queue": [queue_item],
                "test_tag": test_tag,
                "created_at": now,
                "updated_at": now,
                "from_api": path,
            })

    except Exception as exc:
        try:
            print("c_count_insert_after_request failed:", exc)
        except Exception:
            pass

    return response
# === C_COUNT_INSERT_END ===
