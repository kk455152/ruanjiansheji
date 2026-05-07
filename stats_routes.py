from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request, jsonify

from db import get_mysql_conn
from auth_guard import require_auth

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


def convert_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, Decimal):
        return float(value)
    return value


@stats_bp.route("/daily", methods=["GET"])
@require_auth
def daily_stats():
    date_str = request.args.get("date")

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        stat_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "code": 400,
            "msg": "查询失败",
            "error_details": "日期格式错误，请使用 YYYY-MM-DD 格式"
        }), 400

    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    stat_date,
                    total_play_count,
                    unique_song_count,
                    unique_user_count,
                    unique_device_count,
                    total_play_duration_seconds,
                    avg_play_duration_seconds,
                    hottest_song_external_id,
                    hottest_song_name,
                    hottest_artist,
                    hottest_play_count,
                    generated_at,
                    updated_at
                FROM daily_stats
                WHERE stat_date = %s
                LIMIT 1
                """,
                (stat_date,)
            )

            row = cursor.fetchone()

        if not row:
            return jsonify({
                "code": 404,
                "msg": "暂无数据",
                "error_details": "该日期暂无日报统计数据"
            }), 404

        row = {k: convert_value(v) for k, v in row.items()}

        return jsonify({
            "code": 200,
            "msg": "获取每日统计成功",
            "data": row
        }), 200

    finally:
        conn.close()
