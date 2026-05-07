from datetime import datetime, date
from decimal import Decimal

from bson import ObjectId
from flask import Blueprint, request, jsonify, g

from db import get_mysql_conn, mongo_db
from auth_guard import require_auth

mongo_bp = Blueprint("mongo", __name__)


def json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value.strftime("%Y-%m-%d")

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict):
        return {key: json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    return value


def check_device_owner(user_id, device_id):
    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
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
            "msg": "请求参数有误",
            "error_details": "device_id 不能为空"
        }), 400

    try:
        mysql_device_id = int(device_id)
    except ValueError:
        return jsonify({
            "code": 400,
            "msg": "请求参数有误",
            "error_details": "device_id 必须是数字"
        }), 400

    if not check_device_owner(g.user_id, mysql_device_id):
        return jsonify({
            "code": 403,
            "msg": "禁止操作",
            "error_details": "当前用户无权查看该设备数据"
        }), 403

    doc = mongo_db.device_metrics.find_one(
        {
            "$or": [
                {"device_id": mysql_device_id},
                {"device_id": str(mysql_device_id)}
            ]
        },
        sort=[("created_at", -1), ("timestamp", -1), ("_id", -1)]
    )

    if not doc:
        return jsonify({
            "code": 404,
            "msg": "未找到设备实时指标",
            "error_details": "该设备暂无 MongoDB 实时指标数据"
        }), 404

    return jsonify({
        "code": 200,
        "msg": "获取设备实时指标成功",
        "data": json_safe(doc)
    }), 200


@mongo_bp.route("/media/metadata/raw", methods=["GET"])
@require_auth
def media_metadata_raw():
    song_id = request.args.get("song_id", "").strip()

    if not song_id:
        return jsonify({
            "code": 400,
            "msg": "请求参数有误",
            "error_details": "song_id 不能为空"
        }), 400

    doc = mongo_db.media_metadata.find_one({"song_id": song_id})

    if not doc:
        doc = mongo_db.media_metadata.find_one({"external_id": song_id})

    if not doc:
        doc = mongo_db.media_metadata.find_one({"id": song_id})

    if not doc:
        return jsonify({
            "code": 404,
            "msg": "未找到歌曲信息",
            "error_details": "该 song_id 暂未在 MongoDB 中建立索引。"
        }), 404

    return jsonify({
        "code": 200,
        "msg": "获取歌曲原始信息成功",
        "data": json_safe(doc)
    }), 200
