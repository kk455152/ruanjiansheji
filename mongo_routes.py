from bson import ObjectId
from flask import Blueprint, request, jsonify, g
from pymongo import DESCENDING

from db import get_mysql_conn, mongo_db
from auth_guard import require_auth

mongo_bp = Blueprint("mongo_api", __name__)


def mongo_to_json(doc):
    if isinstance(doc, list):
        return [mongo_to_json(x) for x in doc]

    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == "_id":
                continue
            result[k] = mongo_to_json(v)
        return result

    if isinstance(doc, ObjectId):
        return str(doc)

    return doc


def check_device_owner(user_id, device_id):
    """
    防止用户查别人的设备。
    注意：如果 MySQL device_id 是 int，而 MongoDB device_id 是字符串，要在这里兼容。
    """
    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT binding_id
                FROM user_device_binding
                WHERE user_id = %s AND device_id = %s
                LIMIT 1
                """,
                (user_id, device_id)
            )

            return cursor.fetchone() is not None

    finally:
        conn.close()


@mongo_bp.route("/device/metrics/latest", methods=["GET"])
@require_auth
def device_metrics_latest():
    device_id = request.args.get("device_id", "").strip()

    if not device_id:
        return jsonify({
            "code": 400,
            "msg": "查询失败",
            "error_details": "device_id 不能为空"
        }), 400

    # 如果你的 MongoDB 里 device_id 是字符串，但 MySQL 是数字，这里做兼容
    mysql_device_id = int(device_id) if device_id.isdigit() else device_id

    if not check_device_owner(g.user_id, mysql_device_id):
        return jsonify({
            "code": 403,
            "msg": "权限不足",
            "error_details": "该设备不属于当前登录用户"
        }), 403

    query_values = [device_id]

    if device_id.isdigit():
        query_values.append(int(device_id))

    doc = mongo_db.device_metrics.find_one(
        {"device_id": {"$in": query_values}},
        sort=[("updated_at", DESCENDING)]
    )

    if not doc:
        return jsonify({
            "code": 404,
            "msg": "暂无数据",
            "error_details": "该设备尚未上报任何实时指标，请检查硬件联网状态"
        }), 404

    doc = mongo_to_json(doc)

    return jsonify({
        "code": 200,
        "msg": "获取设备实时指标成功 [Source: MongoDB]",
        "data": {
            "device_id": doc.get("device_id"),
            "metrics": doc.get("metrics", {}),
            "last_api_path": doc.get("last_api_path"),
            "updated_at": doc.get("updated_at")
        }
    }), 200


@mongo_bp.route("/media/metadata/raw", methods=["GET"])
@require_auth
def media_metadata_raw():
    song_id = request.args.get("song_id", "").strip()

    if not song_id:
        return jsonify({
            "code": 400,
            "msg": "查询失败",
            "error_details": "song_id 不能为空"
        }), 400

    doc = mongo_db.media_metadata.find_one({"song_id": song_id})

    if not doc:
        doc = mongo_db.media_metadata.find_one({"external_id": song_id})

    if not doc:
        return jsonify({
            "code": 404,
            "msg": "未找到歌曲信息",
            "error_details": "该 song_id 尚未在 MongoDB 中建立索引。"
        }), 404

    doc = mongo_to_json(doc)

    duration_ms = doc.get("duration_ms")
    duration_seconds = doc.get("duration_seconds")

    if duration_seconds is None and isinstance(duration_ms, int):
        duration_seconds = duration_ms // 1000

    return jsonify({
        "code": 200,
        "msg": "获取媒体详情成功 [Source: MongoDB]",
        "data": {
            "song_id": doc.get("song_id") or doc.get("external_id"),
            "name": doc.get("name"),
            "artist_text": doc.get("artist_text"),
            "artists": doc.get("artists", []),
            "album": doc.get("album"),
            "cover_url": doc.get("cover_url"),
            "duration_ms": duration_ms,
            "duration_seconds": duration_seconds,
            "extra_info": doc.get("extra_info", {})
        }
    }), 200
