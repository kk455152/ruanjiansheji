from datetime import date, datetime

from flask import Blueprint, request, jsonify

from db import get_mysql_conn
from auth_guard import require_auth

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


def format_value(value):
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value.strftime("%Y-%m-%d")
    return value


def format_row(row):
    if not row:
        return None

    return {
        "stat_date": format_value(row.get("stat_date")),
        "total_play_count": row.get("total_play_count"),
        "unique_song_count": row.get("unique_song_count"),
        "unique_user_count": row.get("unique_user_count"),
        "unique_device_count": row.get("unique_device_count"),
        "total_play_duration_seconds": row.get("total_play_duration_seconds"),
        "avg_play_duration_seconds": str(row.get("avg_play_duration_seconds")),
        "hottest_song_external_id": row.get("hottest_song_external_id"),
        "hottest_song_name": row.get("hottest_song_name"),
        "hottest_artist": row.get("hottest_artist"),
        "hottest_play_count": row.get("hottest_play_count"),
        "generated_at": format_value(row.get("generated_at")),
        "updated_at": format_value(row.get("updated_at")),
    }


@stats_bp.route("/daily", methods=["GET"])
@require_auth
def daily_stats():
    stat_date = request.args.get("date", "").strip()

    conn = get_mysql_conn()

    try:
        with conn.cursor() as cursor:
            if stat_date:
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
                    FROM Daily_Stats
                    WHERE stat_date = %s
                    LIMIT 1
                    """,
                    (stat_date,)
                )

                row = cursor.fetchone()

                if not row:
                    return jsonify({
                        "code": 404,
                        "msg": "未找到日报统计数据",
                        "error_details": "该日期暂无统计数据"
                    }), 404

                return jsonify({
                    "code": 200,
                    "msg": "获取日报统计成功",
                    "data": format_row(row)
                }), 200

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
                FROM Daily_Stats
                ORDER BY stat_date DESC
                LIMIT 7
                """
            )

            rows = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "获取日报统计成功",
            "data": [format_row(row) for row in rows]
        }), 200

    except Exception as e:
        return jsonify({
            "code": 400,
            "msg": "获取日报统计失败",
            "error_details": str(e)
        }), 400

    finally:
        conn.close()
