"""MongoDB event-log collections defined in the 数据库交接 PDF.

Adds the nine analytics / log collections recommended by the handover doc:

    1. device_event_log         设备事件原始日志
    2. play_event_log           播放行为原始事件
    3. voice_command_log        语音指令记录
    4. device_status_snapshot   设备状态快照
    5. user_behavior_event      用户行为埋点
    6. listen_room_message      一起听房间消息扩展
    7. feedback_attachment      反馈附件 / 补充信息
    8. third_party_music_raw    第三方音乐平台原始响应
    9. device_config_snapshot   设备配置快照

Each helper accepts a dict, fills sensible defaults, ensures `_id` /
`created_at` and inserts the document. They are intentionally tolerant of
partial payloads so the gateway and worker can write whatever fields the
upstream simulator sends without failing.
"""

import os
import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


def _named_collection(env_name, default_name):
    # Imported lazily to avoid a circular import with storage_backends.
    from storage_backends import get_mongo_collection

    database = get_mongo_collection().database
    return database[os.environ.get(env_name, default_name)]


# ---------------------------------------------------------------------------
# Collection accessors
# ---------------------------------------------------------------------------

def get_device_event_log_collection():
    return _named_collection("MONGO_DEVICE_EVENT_LOG_COLLECTION", "device_event_log")


def get_play_event_log_collection():
    return _named_collection("MONGO_PLAY_EVENT_LOG_COLLECTION", "play_event_log")


def get_voice_command_log_collection():
    return _named_collection("MONGO_VOICE_COMMAND_LOG_COLLECTION", "voice_command_log")


def get_device_status_snapshot_collection():
    return _named_collection("MONGO_DEVICE_STATUS_SNAPSHOT_COLLECTION", "device_status_snapshot")


def get_user_behavior_event_collection():
    return _named_collection("MONGO_USER_BEHAVIOR_EVENT_COLLECTION", "user_behavior_event")


def get_listen_room_message_collection():
    return _named_collection("MONGO_LISTEN_ROOM_MESSAGE_COLLECTION", "listen_room_message")


def get_feedback_attachment_collection():
    return _named_collection("MONGO_FEEDBACK_ATTACHMENT_COLLECTION", "feedback_attachment")


def get_third_party_music_raw_collection():
    return _named_collection("MONGO_THIRD_PARTY_MUSIC_RAW_COLLECTION", "third_party_music_raw")


def get_device_config_snapshot_collection():
    return _named_collection("MONGO_DEVICE_CONFIG_SNAPSHOT_COLLECTION", "device_config_snapshot")


EVENT_LOG_COLLECTION_GETTERS = (
    get_device_event_log_collection,
    get_play_event_log_collection,
    get_voice_command_log_collection,
    get_device_status_snapshot_collection,
    get_user_behavior_event_collection,
    get_listen_room_message_collection,
    get_feedback_attachment_collection,
    get_third_party_music_raw_collection,
    get_device_config_snapshot_collection,
)


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def ensure_event_log_indexes():
    """Create the indexes recommended by the handover document."""

    from storage_backends import create_index_safely

    create_index_safely(get_device_event_log_collection(), [("device_id", 1), ("created_at", -1)])
    create_index_safely(get_device_event_log_collection(), [("device_sn", 1), ("created_at", -1)])
    create_index_safely(get_device_event_log_collection(), [("log_level", 1), ("created_at", -1)])
    create_index_safely(get_device_event_log_collection(), [("event_code", 1), ("created_at", -1)])

    create_index_safely(get_play_event_log_collection(), [("user_id", 1), ("created_at", -1)])
    create_index_safely(get_play_event_log_collection(), [("device_id", 1), ("created_at", -1)])
    create_index_safely(get_play_event_log_collection(), [("event_type", 1), ("created_at", -1)])
    create_index_safely(get_play_event_log_collection(), [("song.external_id", 1), ("created_at", -1)])

    create_index_safely(get_voice_command_log_collection(), [("user_id", 1), ("created_at", -1)])
    create_index_safely(get_voice_command_log_collection(), [("device_id", 1), ("created_at", -1)])
    create_index_safely(get_voice_command_log_collection(), [("nlu.intent", 1), ("created_at", -1)])
    create_index_safely(get_voice_command_log_collection(), "session_id")

    create_index_safely(get_device_status_snapshot_collection(), [("device_id", 1), ("reported_at", -1)])
    create_index_safely(get_device_status_snapshot_collection(), [("device_sn", 1), ("reported_at", -1)])

    create_index_safely(get_user_behavior_event_collection(), [("user_id", 1), ("created_at", -1)])
    create_index_safely(get_user_behavior_event_collection(), [("event_name", 1), ("created_at", -1)])
    create_index_safely(get_user_behavior_event_collection(), [("created_at", -1)])

    create_index_safely(get_listen_room_message_collection(), [("room_id", 1), ("created_at", -1)])
    create_index_safely(get_listen_room_message_collection(), [("user_id", 1), ("created_at", -1)])

    create_index_safely(get_feedback_attachment_collection(), "feedback_id")
    create_index_safely(get_feedback_attachment_collection(), [("user_id", 1), ("created_at", -1)])

    create_index_safely(get_third_party_music_raw_collection(),
                        [("platform", 1), ("api_name", 1), ("created_at", -1)])
    create_index_safely(get_third_party_music_raw_collection(), [("success", 1), ("created_at", -1)])

    create_index_safely(get_device_config_snapshot_collection(), [("device_id", 1), ("created_at", -1)])


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------

def _attach_default_meta(document):
    document.setdefault("created_at", _utcnow())
    return document


def insert_device_event_log(document):
    _attach_default_meta(document)
    document.setdefault("trace_id", f"trace_{uuid.uuid4().hex[:12]}")
    document.setdefault("log_type", "runtime")
    document.setdefault("log_level", "info")
    return get_device_event_log_collection().insert_one(document).inserted_id


def insert_play_event_log(document):
    _attach_default_meta(document)
    document.setdefault("event_type", "PLAY_START")
    return get_play_event_log_collection().insert_one(document).inserted_id


def insert_voice_command_log(document):
    _attach_default_meta(document)
    document.setdefault("session_id", f"voice_session_{uuid.uuid4().hex[:8]}")
    document.setdefault("request_id", f"req_{uuid.uuid4().hex[:8]}")
    return get_voice_command_log_collection().insert_one(document).inserted_id


def insert_device_status_snapshot(document):
    _attach_default_meta(document)
    document.setdefault("reported_at", document["created_at"])
    return get_device_status_snapshot_collection().insert_one(document).inserted_id


def insert_user_behavior_event(document):
    _attach_default_meta(document)
    document.setdefault("platform", "app")
    return get_user_behavior_event_collection().insert_one(document).inserted_id


def insert_listen_room_message(document):
    _attach_default_meta(document)
    document.setdefault("message_type", "text")
    return get_listen_room_message_collection().insert_one(document).inserted_id


def insert_feedback_attachment(document):
    _attach_default_meta(document)
    document.setdefault("attachments", [])
    return get_feedback_attachment_collection().insert_one(document).inserted_id


def insert_third_party_music_raw(document):
    _attach_default_meta(document)
    document.setdefault("success", True)
    return get_third_party_music_raw_collection().insert_one(document).inserted_id


def insert_device_config_snapshot(document):
    _attach_default_meta(document)
    return get_device_config_snapshot_collection().insert_one(document).inserted_id


__all__ = [
    "ensure_event_log_indexes",
    "EVENT_LOG_COLLECTION_GETTERS",
    "get_device_event_log_collection",
    "get_play_event_log_collection",
    "get_voice_command_log_collection",
    "get_device_status_snapshot_collection",
    "get_user_behavior_event_collection",
    "get_listen_room_message_collection",
    "get_feedback_attachment_collection",
    "get_third_party_music_raw_collection",
    "get_device_config_snapshot_collection",
    "insert_device_event_log",
    "insert_play_event_log",
    "insert_voice_command_log",
    "insert_device_status_snapshot",
    "insert_user_behavior_event",
    "insert_listen_room_message",
    "insert_feedback_attachment",
    "insert_third_party_music_raw",
    "insert_device_config_snapshot",
]
