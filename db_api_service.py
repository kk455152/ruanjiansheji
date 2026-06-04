# db_api_service.py
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request

from db_config import get_mysql_connection


db_api = Blueprint("db_api", __name__, url_prefix="/api/db")


# =========================================================
# 表结构配置：严格按照当前 smart_speaker 数据库真实存在的表
# 不包含 operation_log，因为当前 MySQL 中没有该表
# 不包含 users / user_preferences，因为它们不在 PowerDesigner 设计图主表范围内
# =========================================================

TABLE_CONFIG = {
    "user": {
        "table": "user",
        "pk": ["user_id"],
        "columns": [
            "user_id",
            "username",
            "password_hash",
            "phone",
            "created_at",
        ],
        "insert_columns": [
            "username",
            "password_hash",
            "phone",
            "created_at",
        ],
        "update_columns": [
            "username",
            "password_hash",
            "phone",
        ],
    },

    "device": {
        "table": "device",
        "pk": ["device_id"],
        "columns": [
            "device_id",
            "device_number",
            "model_name",
            "status",
            "firmware_version",
            "last_active",
        ],
        "insert_columns": [
            "device_number",
            "model_name",
            "status",
            "firmware_version",
            "last_active",
        ],
        "update_columns": [
            "device_number",
            "model_name",
            "status",
            "firmware_version",
            "last_active",
        ],
    },

    "auth_token": {
        "table": "auth_token",
        "pk": ["auth_id"],
        "columns": [
            "auth_id",
            "user_id",
            "platform_type",
            "access_token",
            "refresh_token",
            "expires_at",
        ],
        "insert_columns": [
            "user_id",
            "platform_type",
            "access_token",
            "refresh_token",
            "expires_at",
        ],
        "update_columns": [
            "user_id",
            "platform_type",
            "access_token",
            "refresh_token",
            "expires_at",
        ],
    },

    "media_mapping": {
        "table": "media_mapping",
        "pk": ["mapping_id"],
        "columns": [
            "mapping_id",
            "user_id",
            "song_title",
            "artist",
            "platform",
            "external_id",
            "cover_url",
        ],
        "insert_columns": [
            "user_id",
            "song_title",
            "artist",
            "platform",
            "external_id",
            "cover_url",
        ],
        "update_columns": [
            "user_id",
            "song_title",
            "artist",
            "platform",
            "external_id",
            "cover_url",
        ],
    },

    "action_dict": {
        "table": "action_dict",
        "pk": ["action_id"],
        "columns": [
            "action_id",
            "action_code",
            "action_name",
            "category",
        ],
        # action_id 在当前真实表中不是 auto_increment，所以新增时需要允许传 action_id
        "insert_columns": [
            "action_id",
            "action_code",
            "action_name",
            "category",
        ],
        "update_columns": [
            "action_code",
            "action_name",
            "category",
        ],
    },

    "play_history": {
        "table": "play_history",
        "pk": ["history_id"],
        "columns": [
            "history_id",
            "device_id",
            "user_id",
            "mapping_id",
            "play_duration",
            "created_at",
            "style",
        ],
        "insert_columns": [
            "device_id",
            "user_id",
            "mapping_id",
            "play_duration",
            "created_at",
            "style",
        ],
        "update_columns": [
            "device_id",
            "user_id",
            "mapping_id",
            "play_duration",
            "created_at",
            "style",
        ],
    },

    "friendship": {
        "table": "friendship",
        # 当前真实表字段顺序是 user_id_2、user_id_1，但接口统一按 user_id_1、user_id_2 传参
        "pk": ["user_id_1", "user_id_2"],
        "columns": [
            "user_id_1",
            "user_id_2",
        ],
        "insert_columns": [
            "user_id_1",
            "user_id_2",
        ],
        # friendship 只有联合主键，没有业务字段可修改
        "update_columns": [],
    },

    "user_device_binding": {
        "table": "user_device_binding",
        "pk": ["user_id", "device_id"],
        "columns": [
            "user_id",
            "device_id",
            "custom_device_name",
            "is_primary",
        ],
        "insert_columns": [
            "user_id",
            "device_id",
            "custom_device_name",
            "is_primary",
        ],
        "update_columns": [
            "custom_device_name",
            "is_primary",
        ],
    },

    "user_feedback": {
        "table": "user_feedback",
        "pk": ["feedback_id"],
        "columns": [
            "feedback_id",
            "user_id",
            "content",
        ],
        "insert_columns": [
            "user_id",
            "content",
        ],
        "update_columns": [
            "user_id",
            "content",
        ],
    },

    "daily_stats": {
        "table": "daily_stats",
        "pk": ["stat_date"],
        "columns": [
            "stat_date",
            "total_play_count",
            "unique_song_count",
            "unique_user_count",
            "active_user_count",
            "online_device_count",
            "platform_wechat_count",
            "platform_qq_count",
            "unique_device_count",
            "total_play_duration_seconds",
            "avg_play_duration_seconds",
            "hottest_song_external_id",
            "hottest_song_name",
            "hottest_artist",
            "hottest_play_count",
            "new_user_count",
            "new_device_count",
            "total_sales_amount",
            "generated_at",
            "updated_at",
        ],
        "insert_columns": [
            "stat_date",
            "total_play_count",
            "unique_song_count",
            "unique_user_count",
            "active_user_count",
            "online_device_count",
            "platform_wechat_count",
            "platform_qq_count",
            "unique_device_count",
            "total_play_duration_seconds",
            "avg_play_duration_seconds",
            "hottest_song_external_id",
            "hottest_song_name",
            "hottest_artist",
            "hottest_play_count",
            "new_user_count",
            "new_device_count",
            "total_sales_amount",
            "generated_at",
            "updated_at",
        ],
        "update_columns": [
            "total_play_count",
            "unique_song_count",
            "unique_user_count",
            "active_user_count",
            "online_device_count",
            "platform_wechat_count",
            "platform_qq_count",
            "unique_device_count",
            "total_play_duration_seconds",
            "avg_play_duration_seconds",
            "hottest_song_external_id",
            "hottest_song_name",
            "hottest_artist",
            "hottest_play_count",
            "new_user_count",
            "new_device_count",
            "total_sales_amount",
            "generated_at",
            "updated_at",
        ],
    },

    "admin_user": {
        "table": "admin_user",
        "pk": ["admin_id"],
        "columns": [
            "admin_id", "username", "password_hash", "role", "created_at", "updated_at",
            "last_login_at", "status", "real_name", "job_no", "position", "phone",
            "email", "wechat_open_id", "avatar", "is_super_admin",
        ],
        "insert_columns": [
            "username", "password_hash", "role", "status", "real_name", "job_no",
            "position", "phone", "email", "wechat_open_id", "avatar", "is_super_admin",
        ],
        "update_columns": [
            "password_hash", "role", "status", "real_name", "job_no", "position",
            "phone", "email", "wechat_open_id", "avatar", "is_super_admin",
        ],
    },

    "user_profile": {
        "table": "user_profile",
        "pk": ["profile_id"],
        "columns": [
            "profile_id", "user_id", "nickname", "email", "gender", "age", "age_range",
            "province_code", "province_name", "city_code", "city_name", "active_level",
            "value_level", "bound_platforms", "user_status", "created_at", "updated_at",
        ],
        "insert_columns": [
            "user_id", "nickname", "email", "gender", "age", "age_range", "province_code",
            "province_name", "city_code", "city_name", "active_level", "value_level",
            "bound_platforms", "user_status",
        ],
        "update_columns": [
            "nickname", "email", "gender", "age", "age_range", "province_code",
            "province_name", "city_code", "city_name", "active_level", "value_level",
            "bound_platforms", "user_status",
        ],
    },

    "region_stats_daily": {
        "table": "region_stats_daily",
        "pk": ["id"],
        "columns": [
            "id", "stat_date", "region_level", "region_name", "user_count",
            "active_user_count", "device_count", "order_count", "sales_amount",
            "created_at", "updated_at", "region_code",
        ],
        "insert_columns": [
            "stat_date", "region_level", "region_name", "user_count", "active_user_count",
            "device_count", "order_count", "sales_amount", "region_code",
        ],
        "update_columns": [
            "stat_date", "region_level", "region_name", "user_count", "active_user_count",
            "device_count", "order_count", "sales_amount", "region_code",
        ],
    },

    "sales_order": {
        "table": "sales_order",
        "pk": ["order_id"],
        "columns": [
            "order_id", "order_no", "user_id", "device_id", "order_amount", "pay_amount",
            "order_status", "pay_status", "province_code", "province_name", "city_code",
            "city_name", "paid_at", "created_at", "updated_at",
        ],
        "insert_columns": [
            "order_no", "user_id", "device_id", "order_amount", "pay_amount",
            "order_status", "pay_status", "province_code", "province_name",
            "city_code", "city_name", "paid_at",
        ],
        "update_columns": [
            "user_id", "device_id", "order_amount", "pay_amount", "order_status",
            "pay_status", "province_code", "province_name", "city_code", "city_name",
            "paid_at",
        ],
    },

    "hot_ranking_daily": {
        "table": "hot_ranking_daily",
        "pk": ["ranking_id"],
        "columns": [
            "ranking_id", "ranking_date", "ranking_type", "scope_type", "scope_code",
            "rank_no", "target_id", "target_name", "target_category", "metric_value",
            "metric_unit", "created_at",
        ],
        "insert_columns": [
            "ranking_date", "ranking_type", "scope_type", "scope_code", "rank_no",
            "target_id", "target_name", "target_category", "metric_value", "metric_unit",
        ],
        "update_columns": [
            "ranking_date", "ranking_type", "scope_type", "scope_code", "rank_no",
            "target_id", "target_name", "target_category", "metric_value", "metric_unit",
        ],
    },

    "user_value_segment_daily": {
        "table": "user_value_segment_daily",
        "pk": ["id"],
        "columns": [
            "id", "stat_date", "segment_code", "segment_name", "user_count",
            "active_user_count", "avg_play_count", "avg_pay_amount", "retention_rate",
            "created_at", "updated_at",
        ],
        "insert_columns": [
            "stat_date", "segment_code", "segment_name", "user_count", "active_user_count",
            "avg_play_count", "avg_pay_amount", "retention_rate",
        ],
        "update_columns": [
            "stat_date", "segment_code", "segment_name", "user_count", "active_user_count",
            "avg_play_count", "avg_pay_amount", "retention_rate",
        ],
    },

    "device_log": {
        "table": "device_log",
        "pk": ["log_id"],
        "columns": [
            "log_id", "device_id", "device_sn", "device_name", "device_type",
            "device_model", "log_type", "log_level", "title", "content", "event_code",
            "trace_id", "task_id", "firmware_version", "online_status", "ip_address",
            "network_type", "location", "request_url", "request_method", "request_id",
            "response_code", "response_message", "admin_id", "operator_name",
            "operator_type", "created_at", "updated_at",
        ],
        "insert_columns": [
            "device_id", "device_sn", "device_name", "device_type", "device_model",
            "log_type", "log_level", "title", "content", "event_code", "trace_id",
            "task_id", "firmware_version", "online_status", "ip_address", "network_type",
            "location", "request_url", "request_method", "request_id", "response_code",
            "response_message", "admin_id", "operator_name", "operator_type",
        ],
        "update_columns": [
            "device_sn", "device_name", "device_type", "device_model", "log_type",
            "log_level", "title", "content", "event_code", "trace_id", "task_id",
            "firmware_version", "online_status", "ip_address", "network_type",
            "location", "request_url", "request_method", "request_id", "response_code",
            "response_message", "admin_id", "operator_name", "operator_type",
        ],
    },

    "device_firmware": {
        "table": "device_firmware",
        "pk": ["firmware_id"],
        "columns": [
            "firmware_id", "model_name", "device_type", "hardware_version", "version",
            "version_code", "file_url", "file_md5", "file_size", "description",
            "force_update", "status", "created_at", "updated_at",
        ],
        "insert_columns": [
            "model_name", "device_type", "hardware_version", "version", "version_code",
            "file_url", "file_md5", "file_size", "description", "force_update", "status",
        ],
        "update_columns": [
            "model_name", "device_type", "hardware_version", "version", "version_code",
            "file_url", "file_md5", "file_size", "description", "force_update", "status",
        ],
    },

    "device_firmware_release": {
        "table": "device_firmware_release",
        "pk": ["release_id"],
        "columns": [
            "release_id", "release_no", "firmware_id", "target_model_name",
            "target_device_type", "target_hardware_version", "release_scope",
            "total_device_count", "success_device_count", "fail_device_count", "status",
            "admin_id", "operator_name", "scheduled_at", "started_at", "finished_at",
            "created_at", "updated_at",
        ],
        "insert_columns": [
            "release_no", "firmware_id", "target_model_name", "target_device_type",
            "target_hardware_version", "release_scope", "total_device_count",
            "success_device_count", "fail_device_count", "status", "admin_id",
            "operator_name", "scheduled_at", "started_at", "finished_at",
        ],
        "update_columns": [
            "firmware_id", "target_model_name", "target_device_type",
            "target_hardware_version", "release_scope", "total_device_count",
            "success_device_count", "fail_device_count", "status", "admin_id",
            "operator_name", "scheduled_at", "started_at", "finished_at",
        ],
    },

    "device_firmware_update_task": {
        "table": "device_firmware_update_task",
        "pk": ["task_id"],
        "columns": [
            "task_id", "task_no", "device_id", "firmware_id", "release_device_id",
            "current_version", "target_version", "status", "progress", "fail_reason",
            "admin_id", "operator_name", "started_at", "finished_at", "created_at",
            "updated_at",
        ],
        "insert_columns": [
            "task_no", "device_id", "firmware_id", "release_device_id", "current_version",
            "target_version", "status", "progress", "fail_reason", "admin_id",
            "operator_name", "started_at", "finished_at",
        ],
        "update_columns": [
            "firmware_id", "release_device_id", "current_version", "target_version",
            "status", "progress", "fail_reason", "admin_id", "operator_name",
            "started_at", "finished_at",
        ],
    },

    "system_config": {
        "table": "system_config",
        "pk": ["config_id"],
        "columns": [
            "config_id", "config_key", "config_value", "config_type", "config_group",
            "config_name", "description", "editable", "updated_by", "created_at",
            "updated_at",
        ],
        "insert_columns": [
            "config_key", "config_value", "config_type", "config_group", "config_name",
            "description", "editable", "updated_by",
        ],
        "update_columns": [
            "config_value", "config_type", "config_group", "config_name", "description",
            "editable", "updated_by",
        ],
    },

    "admin_operation_log": {
        "table": "admin_operation_log",
        "pk": ["log_id"],
        "columns": [
            "log_id", "admin_id", "action", "module", "operation_name", "path",
            "request_method", "ip_address", "user_agent", "params", "result_status",
            "error_message", "created_at",
        ],
        "insert_columns": [
            "admin_id", "action", "module", "operation_name", "path", "request_method",
            "ip_address", "user_agent", "params", "result_status", "error_message",
        ],
        "update_columns": [
            "admin_id", "action", "module", "operation_name", "path", "request_method",
            "ip_address", "user_agent", "params", "result_status", "error_message",
        ],
    },
}


# =========================================================
# 通用响应与工具函数
# =========================================================

def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_row(row):
    if row is None:
        return None
    return {key: serialize_value(value) for key, value in row.items()}


def serialize_rows(rows):
    return [serialize_row(row) for row in rows]


def success(data=None, message="success"):
    return jsonify({
        "status": "success",
        "message": message,
        "data": data,
    })


def error(message="error", code=400):
    return jsonify({
        "status": "error",
        "message": message,
    }), code


def get_config_or_error(table_key):
    config = TABLE_CONFIG.get(table_key)
    if not config:
        return None, error(f"不支持的数据表: {table_key}", 404)
    return config, None


def quote_identifier(name):
    return f"`{name}`"


def build_where_by_pk(config, values):
    pk_columns = config["pk"]
    if len(pk_columns) != len(values):
        raise ValueError("主键参数数量不匹配")

    where_sql = " AND ".join(
        f"{quote_identifier(column)} = %s"
        for column in pk_columns
    )
    return where_sql, values


def get_composite_pk_values_from_query(config):
    values = []
    missing = []

    for pk_column in config["pk"]:
        value = request.args.get(pk_column)
        if value is None:
            missing.append(pk_column)
        else:
            values.append(value)

    if missing:
        return None, f"缺少主键参数: {', '.join(missing)}"

    return values, None


def pick_allowed_fields(body, allowed_columns):
    return {
        key: body[key]
        for key in allowed_columns
        if key in body
    }


# =========================================================
# 健康检查
# GET /api/db/health
# =========================================================

@db_api.route("/health", methods=["GET"])
def health_check():
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()

        return success({
            "mysql": "connected",
            "result": serialize_row(row),
        })
    except Exception as exc:
        return error(f"MySQL 连接失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 查询所有当前接口支持的表
# GET /api/db/tables
# =========================================================

@db_api.route("/tables", methods=["GET"])
def list_supported_tables():
    return success([
        {
            "key": key,
            "table": config["table"],
            "pk": config["pk"],
            "columns": config["columns"],
            "insertColumns": config["insert_columns"],
            "updateColumns": config["update_columns"],
        }
        for key, config in TABLE_CONFIG.items()
    ])


@db_api.route("/<table_key>/schema", methods=["GET"])
def table_schema(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err
    return success({
        "key": table_key,
        "table": config["table"],
        "pk": config["pk"],
        "columns": config["columns"],
        "insertColumns": config["insert_columns"],
        "updateColumns": config["update_columns"],
    })


# =========================================================
# 通用列表查询
# GET /api/db/user
# GET /api/db/device
# GET /api/db/play_history?user_id=1
# =========================================================

@db_api.route("/<table_key>", methods=["GET"])
def list_records(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    table = config["table"]
    columns = config["columns"]

    limit = request.args.get("limit", "100")
    offset = request.args.get("offset", "0")

    try:
        limit = min(max(int(limit), 1), 500)
        offset = max(int(offset), 0)
    except ValueError:
        return error("limit 和 offset 必须是整数", 400)

    where_parts = []
    params = []

    for column in columns:
        if column in request.args:
            where_parts.append(f"{quote_identifier(column)} = %s")
            params.append(request.args.get(column))

    where_sql = ""
    if where_parts:
        where_sql = " WHERE " + " AND ".join(where_parts)

    pk_order = ", ".join(quote_identifier(column) for column in config["pk"])
    column_sql = ", ".join(quote_identifier(column) for column in columns)

    sql = (
        f"SELECT {column_sql} "
        f"FROM {quote_identifier(table)} "
        f"{where_sql} "
        f"ORDER BY {pk_order} DESC "
        f"LIMIT %s OFFSET %s"
    )

    params.extend([limit, offset])

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            count_sql = (
                f"SELECT COUNT(*) AS total "
                f"FROM {quote_identifier(table)} "
                f"{where_sql}"
            )
            cursor.execute(count_sql, params[:-2])
            count_row = cursor.fetchone() or {}

        return success({
            "total": int(count_row.get("total") or 0),
            "limit": limit,
            "offset": offset,
            "list": serialize_rows(rows),
            "schema": {
                "key": table_key,
                "table": table,
                "pk": config["pk"],
                "columns": columns,
                "insertColumns": config["insert_columns"],
                "updateColumns": config["update_columns"],
            },
        })
    except Exception as exc:
        return error(f"查询失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 通用新增
# POST /api/db/user
# POST /api/db/device
# POST /api/db/play_history
# =========================================================

@db_api.route("/<table_key>", methods=["POST"])
def create_record(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("请求体必须是 JSON 对象", 400)

    table = config["table"]
    insert_columns = config["insert_columns"]

    data = pick_allowed_fields(body, insert_columns)

    if not data:
        return error("没有可新增的字段", 400)

    columns = list(data.keys())
    values = [data[column] for column in columns]

    column_sql = ", ".join(quote_identifier(column) for column in columns)
    placeholder_sql = ", ".join(["%s"] * len(columns))

    sql = (
        f"INSERT INTO {quote_identifier(table)} "
        f"({column_sql}) VALUES ({placeholder_sql})"
    )

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, values)
            new_id = cursor.lastrowid

        conn.commit()

        return success({
            "id": new_id,
            "inserted": data,
        }, "新增成功")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"新增失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 单主键表：查询单条
# GET /api/db/user/1
# GET /api/db/device/1
# GET /api/db/Daily_Stats/2026-04-29
# =========================================================

@db_api.route("/<table_key>/<path:pk_value>", methods=["GET"])
def get_record(table_key, pk_value):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    if len(config["pk"]) != 1:
        return error(
            f"{table_key} 是联合主键表，请使用 detail 接口访问",
            400,
        )

    table = config["table"]
    columns = config["columns"]
    pk_column = config["pk"][0]

    column_sql = ", ".join(quote_identifier(column) for column in columns)

    sql = (
        f"SELECT {column_sql} "
        f"FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(pk_column)} = %s"
    )

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (pk_value,))
            row = cursor.fetchone()

        if not row:
            return error("数据不存在", 404)

        return success(serialize_row(row))
    except Exception as exc:
        return error(f"查询失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 单主键表：修改
# PUT /api/db/user/1
# PUT /api/db/device/1
# PUT /api/db/Daily_Stats/2026-04-29
# =========================================================

@db_api.route("/<table_key>/<path:pk_value>", methods=["PUT", "PATCH"])
def update_record(table_key, pk_value):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    if len(config["pk"]) != 1:
        return error(
            f"{table_key} 是联合主键表，请使用 detail 接口修改",
            400,
        )

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("请求体必须是 JSON 对象", 400)

    table = config["table"]
    pk_column = config["pk"][0]
    update_columns = config["update_columns"]

    data = pick_allowed_fields(body, update_columns)

    if not data:
        return error("没有可修改的字段", 400)

    set_sql = ", ".join(
        f"{quote_identifier(column)} = %s"
        for column in data.keys()
    )

    sql = (
        f"UPDATE {quote_identifier(table)} "
        f"SET {set_sql} "
        f"WHERE {quote_identifier(pk_column)} = %s"
    )

    params = list(data.values()) + [pk_value]

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在或内容未变化", 404)

        conn.commit()
        return success(data, "修改成功")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"修改失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 单主键表：删除
# DELETE /api/db/user/1
# DELETE /api/db/device/1
# DELETE /api/db/Daily_Stats/2026-04-29
# =========================================================

@db_api.route("/<table_key>/<path:pk_value>", methods=["DELETE"])
def delete_record(table_key, pk_value):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    if len(config["pk"]) != 1:
        return error(
            f"{table_key} 是联合主键表，请使用 detail 接口删除",
            400,
        )

    table = config["table"]
    pk_column = config["pk"][0]

    sql = (
        f"DELETE FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(pk_column)} = %s"
    )

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (pk_value,))

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在", 404)

        conn.commit()
        return success(None, "删除成功")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"删除失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 联合主键表：friendship
# GET    /api/db/friendship/detail?user_id_1=1&user_id_2=2
# DELETE /api/db/friendship/detail?user_id_1=1&user_id_2=2
# =========================================================

@db_api.route("/friendship/detail", methods=["GET"])
def get_friendship_detail():
    return get_composite_record("friendship")


@db_api.route("/friendship/detail", methods=["PUT", "PATCH"])
def update_friendship_detail():
    return error("friendship 表只有两个主键字段，没有可修改字段，如需变更请删除后重新新增", 400)


@db_api.route("/friendship/detail", methods=["DELETE"])
def delete_friendship_detail():
    return delete_composite_record("friendship")


# =========================================================
# 联合主键表：user_device_binding
# GET    /api/db/user_device_binding/detail?user_id=1&device_id=1
# PUT    /api/db/user_device_binding/detail?user_id=1&device_id=1
# DELETE /api/db/user_device_binding/detail?user_id=1&device_id=1
# =========================================================

@db_api.route("/user_device_binding/detail", methods=["GET"])
def get_user_device_binding_detail():
    return get_composite_record("user_device_binding")


@db_api.route("/user_device_binding/detail", methods=["PUT", "PATCH"])
def update_user_device_binding_detail():
    return update_composite_record("user_device_binding")


@db_api.route("/user_device_binding/detail", methods=["DELETE"])
def delete_user_device_binding_detail():
    return delete_composite_record("user_device_binding")


# =========================================================
# 联合主键通用查询
# =========================================================

def get_composite_record(table_key):
    config = TABLE_CONFIG[table_key]

    pk_values, err_msg = get_composite_pk_values_from_query(config)
    if err_msg:
        return error(err_msg, 400)

    table = config["table"]
    columns = config["columns"]

    where_sql, params = build_where_by_pk(config, pk_values)
    column_sql = ", ".join(quote_identifier(column) for column in columns)

    sql = (
        f"SELECT {column_sql} "
        f"FROM {quote_identifier(table)} "
        f"WHERE {where_sql}"
    )

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        if not row:
            return error("数据不存在", 404)

        return success(serialize_row(row))
    except Exception as exc:
        return error(f"查询失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 联合主键通用修改
# =========================================================

def update_composite_record(table_key):
    config = TABLE_CONFIG[table_key]

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("请求体必须是 JSON 对象", 400)

    pk_values, err_msg = get_composite_pk_values_from_query(config)
    if err_msg:
        return error(err_msg, 400)

    table = config["table"]
    update_columns = config["update_columns"]

    data = pick_allowed_fields(body, update_columns)
    if not data:
        return error("没有可修改的字段", 400)

    set_sql = ", ".join(
        f"{quote_identifier(column)} = %s"
        for column in data.keys()
    )

    where_sql, where_params = build_where_by_pk(config, pk_values)

    sql = (
        f"UPDATE {quote_identifier(table)} "
        f"SET {set_sql} "
        f"WHERE {where_sql}"
    )

    params = list(data.values()) + where_params

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在或内容未变化", 404)

        conn.commit()
        return success(data, "修改成功")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"修改失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


# =========================================================
# 联合主键通用删除
# =========================================================

def delete_composite_record(table_key):
    config = TABLE_CONFIG[table_key]

    pk_values, err_msg = get_composite_pk_values_from_query(config)
    if err_msg:
        return error(err_msg, 400)

    table = config["table"]
    where_sql, params = build_where_by_pk(config, pk_values)

    sql = (
        f"DELETE FROM {quote_identifier(table)} "
        f"WHERE {where_sql}"
    )

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在", 404)

        conn.commit()
        return success(None, "删除成功")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"删除失败: {exc}", 500)
    finally:
        if conn:
            conn.close()
