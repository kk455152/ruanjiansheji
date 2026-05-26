"""Smoke test for the 9 MongoDB event-log collections defined in 数据库交接.pdf.

Steps:
    1. Connect to the project's MongoDB (cloud, falls back to local).
    2. For each helper insert one minimal document.
    3. Read it back and assert key fields are present.
    4. Print a per-collection PASS / FAIL summary.

Run with:
    python tests/test_mongo_event_logs.py
"""

import os
import sys
import time
import uuid
from datetime import datetime, timezone

# Ensure project root on path so storage_backends imports cleanly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mongo_event_logs import (  # noqa: E402  (import after sys.path setup)
    ensure_event_log_indexes,
    get_device_event_log_collection,
    get_play_event_log_collection,
    get_voice_command_log_collection,
    get_device_status_snapshot_collection,
    get_user_behavior_event_collection,
    get_listen_room_message_collection,
    get_feedback_attachment_collection,
    get_third_party_music_raw_collection,
    get_device_config_snapshot_collection,
    insert_device_event_log,
    insert_play_event_log,
    insert_voice_command_log,
    insert_device_status_snapshot,
    insert_user_behavior_event,
    insert_listen_room_message,
    insert_feedback_attachment,
    insert_third_party_music_raw,
    insert_device_config_snapshot,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _run_case(name, getter, inserter, document, key_field, key_value):
    started = time.time()
    try:
        inserted_id = inserter(document)
        coll = getter()
        fetched = coll.find_one({"_id": inserted_id})
        assert fetched is not None, f"{name}: insert succeeded but find_one returned None"
        if key_field is not None:
            assert fetched.get(key_field) == key_value, (
                f"{name}: expected {key_field}={key_value!r}, got {fetched.get(key_field)!r}"
            )
        cleanup_id = coll.delete_one({"_id": inserted_id}).deleted_count
        elapsed_ms = int((time.time() - started) * 1000)
        return True, f"PASS {name} (cleanup={cleanup_id}, {elapsed_ms} ms)"
    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return False, f"FAIL {name} ({elapsed_ms} ms): {exc!r}"


def main():
    smoke_marker = f"smoke_{uuid.uuid4().hex[:8]}"
    print(f"[setup] smoke_marker={smoke_marker}")

    print("[setup] ensuring event-log indexes...")
    ensure_event_log_indexes()

    cases = [
        (
            "device_event_log",
            get_device_event_log_collection,
            insert_device_event_log,
            {
                "device_id": 99001,
                "device_sn": f"SPK_{smoke_marker}",
                "device_type": "smart_speaker",
                "model_name": "S1",
                "log_level": "info",
                "event_code": "DEVICE_ONLINE",
                "message": "smoke test online",
                "raw_payload": {"battery": 87, "wifi_rssi": -55},
            },
            "event_code",
            "DEVICE_ONLINE",
        ),
        (
            "play_event_log",
            get_play_event_log_collection,
            insert_play_event_log,
            {
                "user_id": 99001,
                "device_id": 99001,
                "event_type": "PLAY_START",
                "source_platform": "qq_music",
                "song": {
                    "external_id": f"qq_{smoke_marker}",
                    "title": "晴天",
                    "artist": "周杰伦",
                    "album": "叶惠美",
                    "duration_seconds": 269,
                },
                "play_context": {"volume": 45, "play_mode": "single"},
            },
            "event_type",
            "PLAY_START",
        ),
        (
            "voice_command_log",
            get_voice_command_log_collection,
            insert_voice_command_log,
            {
                "user_id": 99001,
                "device_id": 99001,
                "asr_text": "播放周杰伦的晴天",
                "nlu": {
                    "intent": "PLAY_MUSIC",
                    "confidence": 0.96,
                    "slots": {"artist": "周杰伦", "song": "晴天"},
                },
                "result": {"success": True, "action": "play_music"},
            },
            "asr_text",
            "播放周杰伦的晴天",
        ),
        (
            "device_status_snapshot",
            get_device_status_snapshot_collection,
            insert_device_status_snapshot,
            {
                "device_id": 99001,
                "device_sn": f"SPK_{smoke_marker}",
                "status": {
                    "online": True,
                    "battery": 86,
                    "charging": False,
                    "volume": 40,
                    "wifi_rssi": -58,
                },
                "hardware": {"cpu_usage": 23.5, "memory_usage": 61.2},
            },
            "device_id",
            99001,
        ),
        (
            "user_behavior_event",
            get_user_behavior_event_collection,
            insert_user_behavior_event,
            {
                "user_id": 99001,
                "platform": "app",
                "event_name": "CLICK_BIND_DEVICE",
                "page": "device_bind_page",
                "device_id": 99001,
                "properties": {"button_name": "开始绑定", "network_type": "wifi"},
            },
            "event_name",
            "CLICK_BIND_DEVICE",
        ),
        (
            "listen_room_message",
            get_listen_room_message_collection,
            insert_listen_room_message,
            {
                "room_id": 99001,
                "user_id": 99001,
                "message_type": "text",
                "content": "这首歌真好听",
                "extra": {"nickname": "小明"},
            },
            "content",
            "这首歌真好听",
        ),
        (
            "feedback_attachment",
            get_feedback_attachment_collection,
            insert_feedback_attachment,
            {
                "feedback_id": 50001,
                "user_id": 99001,
                "attachments": [
                    {
                        "type": "image",
                        "url": "https://oss.example.com/feedback/1.png",
                        "name": "screenshot.png",
                        "size": 204800,
                    }
                ],
                "extra_context": {"app_version": "1.2.0", "os": "Android14"},
            },
            "feedback_id",
            50001,
        ),
        (
            "third_party_music_raw",
            get_third_party_music_raw_collection,
            insert_third_party_music_raw,
            {
                "platform": "qq_music",
                "api_name": "search_song",
                "request": {"keyword": "周杰伦晴天", "user_id": 99001},
                "response": {"code": 0, "data": {}},
                "success": True,
                "cost_ms": 120,
            },
            "platform",
            "qq_music",
        ),
        (
            "device_config_snapshot",
            get_device_config_snapshot_collection,
            insert_device_config_snapshot,
            {
                "device_id": 99001,
                "changed_by": {"type": "user", "user_id": 99001},
                "before": {"volume_limit": 80, "night_mode_enabled": False},
                "after": {
                    "volume_limit": 60,
                    "night_mode_enabled": True,
                    "night_start": "22:00",
                    "night_end": "07:00",
                },
            },
            "device_id",
            99001,
        ),
    ]

    pass_count = 0
    fail_count = 0
    for case in cases:
        ok, message = _run_case(*case)
        print(message)
        if ok:
            pass_count += 1
        else:
            fail_count += 1

    print(f"\n[summary] passed={pass_count} failed={fail_count} total={len(cases)}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
