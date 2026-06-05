# db_api_service.py
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request

from db_config import get_mysql_connection
from api_pkg.common import json_safe, mongo_db

try:
    from bson import ObjectId
except Exception:
    ObjectId = None


db_api = Blueprint("db_api", __name__, url_prefix="/api/db")

TABLE_LABELS = {
    "user": "小程序用户",
    "device": "智能音箱设备",
    "auth_token": "用户登录令牌",
    "media_mapping": "歌曲映射",
    "action_dict": "操作字典",
    "play_history": "播放历史",
    "friendship": "好友关系",
    "user_device_binding": "用户设备绑定",
    "user_feedback": "用户反馈",
    "daily_stats": "每日运营统计",
    "admin_user": "后台管理员账号",
    "user_profile": "用户画像",
    "region_stats_daily": "地区统计日报",
    "sales_order": "销售订单",
    "hot_ranking_daily": "热度排行榜",
    "user_value_segment_daily": "用户分群日报",
    "device_log": "设备日志",
    "device_firmware": "设备固件包",
    "device_firmware_release": "固件发布批次",
    "device_firmware_update_task": "固件升级任务",
    "system_config": "系统配置",
    "admin_operation_log": "后台操作日志",
}

FIELD_COMMENTS = {
    "id": ("ID", "系统自增主键。"),
    "user_id": ("用户ID", "关联 user 表的小程序用户主键。"),
    "username": ("用户名", "登录名或业务用户账号，需唯一。"),
    "password_hash": ("密码", "当前按要求直接存明文密码，方便维护页查看和修改。"),
    "phone": ("手机号", "用户或管理员联系电话。"),
    "created_at": ("创建时间", "记录创建时间，格式 YYYY-MM-DD HH:MM:SS。"),
    "updated_at": ("更新时间", "记录最后更新时间。"),
    "nickname": ("昵称", "用户展示昵称。"),
    "avatar": ("头像", "头像图片地址，可为空。"),
    "email": ("邮箱", "邮箱地址。"),
    "status": ("状态", "业务状态，例如 1/0、active、paid、success。"),
    "last_login_at": ("最后登录时间", "账号最近一次登录时间，可为空。"),
    "admin_id": ("管理员ID", "关联 admin_user 表的后台管理员主键。"),
    "role": ("角色编码", "super_admin、market_admin、operator_admin、boss。"),
    "real_name": ("真实姓名", "后台管理员姓名。"),
    "job_no": ("工号", "后台管理员工号。"),
    "position": ("岗位", "后台管理员岗位名称。"),
    "wechat_open_id": ("微信OpenID", "微信快捷登录绑定标识，可为空。"),
    "is_super_admin": ("是否超级管理员", "1 表示超级管理员，0 表示普通管理员。"),
    "device_id": ("设备ID", "关联 device 表的设备主键。"),
    "device_number": ("设备编号", "设备唯一 SN/编号，如 SHMINI-A1-0001。"),
    "device_sn": ("设备SN", "对外展示的设备序列号。"),
    "model_name": ("设备型号", "设备型号，如 SH-Mini A1。"),
    "device_model": ("设备型号", "日志中记录的设备型号。"),
    "device_name": ("设备名称", "设备展示名称，如客厅音箱。"),
    "device_type": ("设备类型", "音箱填 speaker；真实表为必填字段。"),
    "firmware_version": ("固件版本", "设备当前固件版本。"),
    "last_active": ("最后活跃时间", "设备最后一次心跳或活跃时间。"),
    "online_status": ("在线状态", "online 或 offline。"),
    "ip_address": ("IP地址", "设备或操作来源 IP。"),
    "hardware_version": ("硬件版本", "设备硬件版本，默认 default。"),
    "location": ("位置", "设备所在房间或地区。"),
    "auth_id": ("授权ID", "音乐平台授权记录主键。"),
    "platform_type": ("平台类型", "第三方平台类型，如 qq、netease、wechat_mini。"),
    "access_token": ("访问令牌", "登录或第三方平台访问令牌。"),
    "refresh_token": ("刷新令牌", "用于刷新 access_token 的令牌。"),
    "expires_at": ("过期时间", "令牌过期时间。"),
    "mapping_id": ("歌曲映射ID", "media_mapping 表主键。"),
    "song_title": ("歌曲名", "歌曲标题。"),
    "artist": ("歌手", "歌手或艺术家名称。"),
    "platform": ("音乐平台", "歌曲来源平台，如 qq、netease。"),
    "external_id": ("外部歌曲ID", "第三方音乐平台歌曲 ID。"),
    "cover_url": ("封面地址", "歌曲封面图片 URL。"),
    "action_id": ("操作ID", "操作字典主键。"),
    "action_code": ("操作编码", "机器可读的操作编码。"),
    "action_name": ("操作名称", "人可读的操作名称。"),
    "category": ("分类", "操作分类。"),
    "history_id": ("历史ID", "播放历史主键。"),
    "play_duration": ("播放时长", "播放时长，单位秒。"),
    "style": ("音乐风格", "歌曲或播放记录风格，如 pop、rock。"),
    "user_id_1": ("用户1", "好友关系中的第一个用户 ID。"),
    "user_id_2": ("用户2", "好友关系中的第二个用户 ID。"),
    "binding_id": ("绑定ID", "用户设备绑定表自增主键。"),
    "custom_device_name": ("自定义设备名", "用户给设备设置的显示名称。"),
    "is_primary": ("是否主设备", "1 表示主设备，0 表示非主设备。"),
    "default_room": ("默认房间", "设备所在默认房间。"),
    "current_network": ("当前网络", "设备当前连接的 Wi-Fi 名称。"),
    "bind_time": ("绑定时间", "用户绑定设备的时间。"),
    "feedback_id": ("反馈ID", "用户反馈主键。"),
    "feedback_no": ("反馈编号", "业务反馈编号。"),
    "feedback_type": ("反馈类型", "bug、suggestion、praise。"),
    "title": ("标题", "反馈、日志或任务标题。"),
    "content": ("内容", "反馈正文或日志内容。"),
    "contact": ("联系方式", "用户反馈时留下的联系方式。"),
    "device_info": ("设备信息", "反馈关联设备信息，通常为文本或 JSON。"),
    "priority": ("优先级", "low、normal、high。"),
    "star_rating": ("评分", "用户评分，1 到 5。"),
    "rating_tags": ("评分标签", "用户评价标签，多个值可用逗号分隔。"),
    "handler_name": ("处理人", "反馈或任务处理人名称。"),
    "reply_content": ("回复内容", "管理员给用户的处理回复。"),
    "handled_at": ("处理时间", "反馈处理完成时间。"),
    "closed_at": ("关闭时间", "反馈关闭时间。"),
    "stat_date": ("统计日期", "日报统计日期。"),
    "total_play_count": ("总播放次数", "当天总播放次数。"),
    "unique_song_count": ("去重歌曲数", "当天播放过的不同歌曲数量。"),
    "unique_user_count": ("去重用户数", "当天活跃用户数。"),
    "active_user_count": ("活跃用户数", "当天活跃用户数量。"),
    "online_device_count": ("在线设备数", "当天在线设备数量。"),
    "platform_wechat_count": ("微信用户数", "微信来源用户数量。"),
    "platform_qq_count": ("QQ音乐用户数", "QQ 音乐来源用户数量。"),
    "unique_device_count": ("去重设备数", "当天活跃设备数。"),
    "total_play_duration_seconds": ("总播放秒数", "当天累计播放时长，单位秒。"),
    "avg_play_duration_seconds": ("平均播放秒数", "平均单次播放时长，单位秒。"),
    "hottest_song_external_id": ("热门歌曲ID", "当天最热门歌曲的外部 ID。"),
    "hottest_song_name": ("热门歌曲", "当天最热门歌曲名称。"),
    "hottest_artist": ("热门歌手", "当天最热门歌曲歌手。"),
    "hottest_play_count": ("热门播放次数", "当天热门歌曲播放次数。"),
    "new_user_count": ("新增用户数", "当天新增用户数量。"),
    "new_device_count": ("新增设备数", "当天新增设备数量。"),
    "total_sales_amount": ("总销售额", "当天销售额汇总。"),
    "generated_at": ("生成时间", "统计数据生成时间。"),
    "profile_id": ("画像ID", "用户画像表主键。"),
    "gender": ("性别", "male、female、unknown。"),
    "age": ("年龄", "用户年龄。"),
    "age_range": ("年龄段", "如 18-25、26-35。"),
    "province_code": ("省份编码", "省级行政区编码。"),
    "province_name": ("省份", "省级行政区名称。"),
    "city_code": ("城市编码", "城市行政区编码。"),
    "city_name": ("城市", "城市名称。"),
    "active_level": ("活跃等级", "high、medium、low。"),
    "value_level": ("价值等级", "high、normal、low。"),
    "bound_platforms": ("绑定平台", "用户绑定的音乐平台列表。"),
    "user_status": ("用户状态", "用户画像中的业务状态。"),
    "region_code": ("地区编码", "地区行政区编码。"),
    "region_level": ("地区层级", "province 或 city。"),
    "region_name": ("地区名称", "地区展示名称。"),
    "user_count": ("用户数", "统计范围内用户数量。"),
    "device_count": ("设备数", "统计范围内设备数量。"),
    "order_count": ("订单数", "统计范围内订单数量。"),
    "sales_amount": ("销售额", "统计范围内销售金额。"),
    "order_id": ("订单ID", "销售订单主键。"),
    "order_no": ("订单号", "业务订单编号，需唯一。"),
    "order_amount": ("订单金额", "订单原始金额。"),
    "pay_amount": ("实付金额", "用户实际支付金额。"),
    "order_status": ("订单状态", "pending、finished、closed。"),
    "pay_status": ("支付状态", "paid、success、finished。"),
    "paid_at": ("支付时间", "订单支付完成时间。"),
    "ranking_id": ("排行ID", "热度排行表主键。"),
    "ranking_date": ("排行日期", "排行榜统计日期。"),
    "ranking_type": ("排行类型", "song、artist。"),
    "scope_type": ("范围类型", "global、province。"),
    "scope_code": ("范围编码", "排行范围编码。"),
    "rank_no": ("名次", "排行榜名次。"),
    "target_id": ("目标ID", "排行对象 ID。"),
    "target_name": ("目标名称", "排行对象名称。"),
    "target_category": ("目标分类", "排行对象分类，例如歌手名。"),
    "metric_value": ("指标值", "排行指标数值。"),
    "metric_unit": ("指标单位", "指标单位，如 plays。"),
    "segment_code": ("分群编码", "用户分群编码。"),
    "segment_name": ("分群名称", "用户分群名称。"),
    "avg_play_count": ("平均播放次数", "分群用户平均播放次数。"),
    "avg_pay_amount": ("平均支付金额", "分群用户平均支付金额。"),
    "retention_rate": ("留存率", "分群留存率，0 到 1。"),
    "log_id": ("日志ID", "日志表主键。"),
    "log_type": ("日志类型", "online、offline、firmware。"),
    "log_level": ("日志级别", "info、warning、error。"),
    "event_code": ("事件编码", "设备事件编码。"),
    "trace_id": ("链路ID", "排查问题用的链路追踪 ID。"),
    "task_id": ("任务ID", "关联任务编号或任务主键。"),
    "network_type": ("网络类型", "wifi、4g。"),
    "request_url": ("请求地址", "日志关联请求 URL。"),
    "request_method": ("请求方法", "GET、POST、PUT、DELETE。"),
    "request_id": ("请求ID", "请求追踪 ID。"),
    "response_code": ("响应码", "接口响应状态码。"),
    "response_message": ("响应消息", "接口响应说明。"),
    "operator_name": ("操作人", "执行操作的人。"),
    "operator_type": ("操作人类型", "admin、system、user。"),
    "firmware_id": ("固件ID", "固件包主键。"),
    "version": ("版本号", "固件版本号。"),
    "version_code": ("版本序号", "用于比较升级顺序的数字版本。"),
    "file_url": ("文件地址", "固件包下载地址。"),
    "file_md5": ("文件MD5", "固件包校验值。"),
    "file_size": ("文件大小", "固件包大小，单位字节。"),
    "description": ("说明", "配置、固件或字段说明。"),
    "force_update": ("强制升级", "1 表示强制升级，0 表示可选升级。"),
    "release_id": ("发布ID", "固件发布批次主键。"),
    "release_no": ("发布编号", "固件发布批次编号。"),
    "target_model_name": ("目标型号", "发布目标设备型号。"),
    "target_device_type": ("目标设备类型", "发布目标设备类型。"),
    "target_hardware_version": ("目标硬件版本", "发布目标硬件版本。"),
    "release_scope": ("发布范围", "gray、all。"),
    "total_device_count": ("目标设备数", "本批次目标设备数量。"),
    "success_device_count": ("成功设备数", "本批次升级成功设备数量。"),
    "fail_device_count": ("失败设备数", "本批次升级失败设备数量。"),
    "scheduled_at": ("计划时间", "任务计划执行时间。"),
    "started_at": ("开始时间", "任务开始时间。"),
    "finished_at": ("完成时间", "任务完成时间。"),
    "task_no": ("任务编号", "固件升级任务编号。"),
    "release_device_id": ("发布设备ID", "关联发布设备明细 ID，可为空。"),
    "current_version": ("当前版本", "升级前版本。"),
    "target_version": ("目标版本", "计划升级到的版本。"),
    "progress": ("进度", "任务进度，0 到 100。"),
    "fail_reason": ("失败原因", "任务失败原因，可为空。"),
    "config_id": ("配置ID", "系统配置主键。"),
    "config_key": ("配置键", "系统配置英文键。"),
    "config_value": ("配置值", "系统配置值。"),
    "config_type": ("配置类型", "string、number、boolean、json。"),
    "config_group": ("配置分组", "配置所属分组。"),
    "config_name": ("配置名称", "配置中文名称。"),
    "editable": ("可编辑", "1 表示维护页可编辑，0 表示不可编辑。"),
    "updated_by": ("更新人", "最后更新该配置的管理员 ID。"),
    "action": ("动作", "后台操作动作编码。"),
    "module": ("模块", "后台模块编码。"),
    "operation_name": ("操作名称", "后台操作中文名称。"),
    "path": ("接口路径", "被访问的接口路径。"),
    "user_agent": ("浏览器信息", "请求来源 User-Agent。"),
    "params": ("请求参数", "操作请求参数，通常为 JSON 文本。"),
    "result_status": ("结果状态", "success、failed。"),
    "error_message": ("错误信息", "失败时记录错误说明。"),
}


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
            "nickname",
            "avatar",
            "email",
            "status",
            "last_login_at",
            "updated_at",
        ],
        "insert_columns": [
            "username",
            "password_hash",
            "phone",
            "created_at",
            "nickname",
            "avatar",
            "email",
            "status",
            "last_login_at",
        ],
        "update_columns": [
            "username",
            "password_hash",
            "phone",
            "nickname",
            "avatar",
            "email",
            "status",
            "last_login_at",
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
            "created_at",
            "device_name",
            "device_type",
            "online_status",
            "ip_address",
            "hardware_version",
            "location",
            "updated_at",
        ],
        "insert_columns": [
            "device_number",
            "model_name",
            "status",
            "firmware_version",
            "last_active",
            "device_name",
            "device_type",
            "online_status",
            "ip_address",
            "hardware_version",
            "location",
        ],
        "update_columns": [
            "device_number",
            "model_name",
            "status",
            "firmware_version",
            "last_active",
            "device_name",
            "device_type",
            "online_status",
            "ip_address",
            "hardware_version",
            "location",
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
            "binding_id",
            "user_id",
            "device_id",
            "custom_device_name",
            "is_primary",
            "default_room",
            "current_network",
            "bind_time",
        ],
        "insert_columns": [
            "user_id",
            "device_id",
            "custom_device_name",
            "is_primary",
            "default_room",
            "current_network",
            "bind_time",
        ],
        "update_columns": [
            "custom_device_name",
            "is_primary",
            "default_room",
            "current_network",
            "bind_time",
        ],
    },

    "user_feedback": {
        "table": "user_feedback",
        "pk": ["feedback_id"],
        "columns": [
            "feedback_id",
            "user_id",
            "content",
            "feedback_no",
            "feedback_type",
            "title",
            "contact",
            "device_info",
            "status",
            "priority",
            "star_rating",
            "rating_tags",
            "admin_id",
            "handler_name",
            "reply_content",
            "handled_at",
            "closed_at",
            "created_at",
            "updated_at",
        ],
        "insert_columns": [
            "user_id",
            "content",
            "feedback_no",
            "feedback_type",
            "title",
            "contact",
            "device_info",
            "status",
            "priority",
            "star_rating",
            "rating_tags",
            "admin_id",
            "handler_name",
            "reply_content",
            "handled_at",
            "closed_at",
        ],
        "update_columns": [
            "user_id",
            "content",
            "feedback_no",
            "feedback_type",
            "title",
            "contact",
            "device_info",
            "status",
            "priority",
            "star_rating",
            "rating_tags",
            "admin_id",
            "handler_name",
            "reply_content",
            "handled_at",
            "closed_at",
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


def column_meta(table_key, config):
    pk = set(config["pk"])
    insertable = set(config["insert_columns"])
    updatable = set(config["update_columns"])
    meta = []
    for column in config["columns"]:
        label, comment = FIELD_COMMENTS.get(column, (column, "请按接口文档和实际业务含义填写。"))
        meta.append({
            "name": column,
            "label": label,
            "comment": comment,
            "isPk": column in pk,
            "canInsert": column in insertable,
            "canUpdate": column in updatable,
        })
    return meta


def schema_payload(table_key, config):
    return {
        "key": table_key,
        "table": config["table"],
        "label": TABLE_LABELS.get(table_key, table_key),
        "pk": config["pk"],
        "columns": config["columns"],
        "insertColumns": config["insert_columns"],
        "updateColumns": config["update_columns"],
        "columnMeta": column_meta(table_key, config),
    }


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


def parse_mongo_id(value):
    if ObjectId is not None:
        try:
            return ObjectId(value)
        except Exception:
            pass
    return value


def random_suffix():
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def random_datetime(days_back=30):
    value = datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return value.strftime("%Y-%m-%d %H:%M:%S")


def random_date(days_back=60):
    return (date.today() - timedelta(days=random.randint(0, days_back))).isoformat()


def fetch_random_id(cursor, table_name, column_name):
    cursor.execute(
        f"SELECT {quote_identifier(column_name)} AS value "
        f"FROM {quote_identifier(table_name)} "
        f"ORDER BY RAND() LIMIT 1"
    )
    row = cursor.fetchone() or {}
    return row.get("value")


def next_numeric_id(cursor, table_name, column_name):
    cursor.execute(
        f"SELECT COALESCE(MAX({quote_identifier(column_name)}), 0) + 1 AS value "
        f"FROM {quote_identifier(table_name)}"
    )
    row = cursor.fetchone() or {}
    return int(row.get("value") or 1)


REFERENCE_COLUMNS = {
    "user_id": ("user", "user_id"),
    "user_id_1": ("user", "user_id"),
    "user_id_2": ("user", "user_id"),
    "device_id": ("device", "device_id"),
    "mapping_id": ("media_mapping", "mapping_id"),
    "admin_id": ("admin_user", "admin_id"),
    "updated_by": ("admin_user", "admin_id"),
    "firmware_id": ("device_firmware", "firmware_id"),
    "release_device_id": ("device_firmware_release_device", "id"),
}


def random_choice(values):
    return random.choice(values)


def mock_value_for_column(cursor, table_key, config, column, used_values):
    suffix = random_suffix()
    table_name = config["table"]

    if column == "user_id_2":
        value = fetch_random_id(cursor, "user", "user_id")
        if value == used_values.get("user_id_1"):
            cursor.execute(
                "SELECT user_id AS value FROM `user` WHERE user_id <> %s ORDER BY RAND() LIMIT 1",
                (used_values.get("user_id_1"),),
            )
            value = (cursor.fetchone() or {}).get("value")
        return value or used_values.get("user_id_1")

    if column in config["pk"] or column.endswith("_id") and column in config["insert_columns"]:
        if column in REFERENCE_COLUMNS:
            ref_table, ref_column = REFERENCE_COLUMNS[column]
            value = fetch_random_id(cursor, ref_table, ref_column)
            if value is not None:
                return value
        if column in config["pk"] or table_key == "action_dict":
            return next_numeric_id(cursor, table_name, column)

    if "date" in column and not column.endswith("_at"):
        if table_key == "daily_stats" and column == "stat_date":
            for _ in range(20):
                value = random_date(365)
                cursor.execute("SELECT 1 FROM daily_stats WHERE stat_date = %s LIMIT 1", (value,))
                if not cursor.fetchone():
                    return value
        return random_date()

    if column.endswith("_at") or column in {"created_at", "updated_at", "last_active", "bind_time"}:
        return random_datetime()

    if column in {"username"}:
        return f"mock_user_{suffix}"
    if column in {"password_hash"}:
        return f"mock_pwd_{random.randint(100000, 999999)}"
    if column in {"phone", "contact"}:
        return f"13{random.randint(100000000, 999999999)}"
    if column == "email":
        return f"mock_{suffix}@example.com"
    if column in {"nickname", "real_name", "operator_name", "handler_name"}:
        return random_choice(["模拟用户", "测试管理员", "数据维护员"]) + str(random.randint(1, 99))
    if column == "avatar":
        return f"https://example.com/avatar/{suffix}.png"
    if column in {"status", "order_status", "pay_status", "result_status"}:
        return random_choice(["active", "enabled", "success", "finished", "pending"])
    if column in {"role"}:
        return random_choice(["operator_admin", "market_admin"])
    if column in {"is_super_admin", "is_primary", "editable", "force_update"}:
        return random.randint(0, 1)
    if column in {"device_number", "device_sn"}:
        return f"SHMINI-A1-{random.randint(1000, 9999)}"
    if column in {"model_name", "device_model", "target_model_name"}:
        return random_choice(["SH-Mini A1", "SH-Home Pro", "SH-Lite"])
    if column in {"device_name", "custom_device_name"}:
        return random_choice(["客厅音箱", "卧室音箱", "书房音箱"]) + str(random.randint(1, 20))
    if column in {"device_type", "target_device_type"}:
        return "speaker"
    if column in {"firmware_version", "current_version", "target_version", "version"}:
        return f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
    if column == "version_code":
        return random.randint(100, 999)
    if column == "hardware_version" or column == "target_hardware_version":
        return f"HW-{random.randint(1, 3)}"
    if column == "online_status":
        return random_choice(["online", "offline"])
    if column == "ip_address":
        return f"192.168.{random.randint(0, 10)}.{random.randint(2, 254)}"
    if column in {"location", "province_name", "city_name", "region_name"}:
        return random_choice(["北京", "上海", "广州", "深圳", "杭州"])
    if column in {"province_code", "city_code", "region_code", "scope_code"}:
        return str(random.randint(100000, 999999))
    if column in {"song_title", "hottest_song_name", "target_name"}:
        return random_choice(["晴天", "稻香", "夜曲", "七里香", "青花瓷"])
    if column in {"artist", "hottest_artist", "target_category"}:
        return random_choice(["周杰伦", "陈奕迅", "林俊杰", "邓紫棋"])
    if column in {"platform", "platform_type", "source"}:
        return random_choice(["netease", "qq", "wechat_mini"])
    if column in {"external_id", "hottest_song_external_id", "target_id"}:
        return f"song_{suffix}"
    if column == "cover_url":
        return f"https://example.com/covers/{suffix}.jpg"
    if column in {"action_code", "event_code"}:
        return f"mock_action_{suffix}"
    if column in {"action_name", "operation_name"}:
        return random_choice(["播放歌曲", "设备上线", "数据维护"])
    if column in {"category", "config_group"}:
        return random_choice(["music", "device", "system"])
    if column == "style":
        return random_choice(["pop", "rock", "classic", "jazz"])
    if column in {"content", "description", "reply_content", "error_message", "params"}:
        return f"随机模拟数据 {suffix}"
    if column in {"feedback_no", "order_no", "release_no", "task_no", "request_id", "trace_id"}:
        return f"MOCK-{suffix}"
    if column == "feedback_type":
        return random_choice(["bug", "suggestion", "praise"])
    if column == "priority":
        return random_choice(["low", "normal", "high"])
    if column == "rating_tags":
        return random_choice(["音质好,响应快", "连接稳定", "界面清晰"])
    if column == "title":
        return random_choice(["模拟反馈", "模拟日志", "模拟任务"])
    if column == "device_info":
        return '{"source":"mock"}'
    if column == "gender":
        return random_choice(["male", "female", "unknown"])
    if column == "age":
        return random.randint(18, 60)
    if column == "age_range":
        return random_choice(["18-25", "26-35", "36-45", "46-60"])
    if column in {"active_level", "value_level"}:
        return random_choice(["high", "medium", "low", "normal"])
    if column == "bound_platforms":
        return random_choice(["netease,qq", "wechat_mini", "qq"])
    if column in {"region_level"}:
        return random_choice(["province", "city"])
    if column in {"ranking_type"}:
        return random_choice(["song", "artist"])
    if column in {"scope_type"}:
        return random_choice(["global", "province"])
    if column == "metric_unit":
        return "plays"
    if column == "segment_code":
        return f"seg_{random.randint(1, 9)}"
    if column == "segment_name":
        return random_choice(["高活跃用户", "普通用户", "低活跃用户"])
    if column in {"log_type"}:
        return random_choice(["online", "offline", "firmware"])
    if column in {"log_level"}:
        return random_choice(["info", "warning", "error"])
    if column == "network_type":
        return random_choice(["wifi", "4g"])
    if column == "request_url" or column == "path":
        return "/api/mock"
    if column == "request_method":
        return random_choice(["GET", "POST", "PUT"])
    if column == "response_message":
        return "success"
    if column == "operator_type":
        return random_choice(["admin", "system", "user"])
    if column == "file_url":
        return f"https://example.com/firmware/{suffix}.bin"
    if column == "file_md5":
        return uuid.uuid4().hex
    if column == "config_key":
        return f"mock.config.{suffix}"
    if column == "config_value":
        return str(random.randint(1, 100))
    if column == "config_type":
        return random_choice(["string", "number", "boolean"])
    if column == "config_name":
        return "模拟配置"
    if column == "module":
        return random_choice(["device", "user", "database"])
    if column == "action":
        return random_choice(["create", "update", "delete"])
    if column == "user_agent":
        return "MockAgent/1.0"
    if column in {"play_duration", "total_play_count", "unique_song_count", "unique_user_count",
                  "active_user_count", "online_device_count", "platform_wechat_count",
                  "platform_qq_count", "unique_device_count", "hottest_play_count",
                  "new_user_count", "new_device_count", "user_count", "device_count",
                  "order_count", "rank_no", "metric_value", "progress", "response_code",
                  "total_device_count", "success_device_count", "fail_device_count"}:
        return random.randint(1, 500)
    if column in {"total_play_duration_seconds", "file_size"}:
        return random.randint(1000, 5000000)
    if column in {"avg_play_duration_seconds", "total_sales_amount", "sales_amount",
                  "order_amount", "pay_amount", "avg_play_count", "avg_pay_amount",
                  "retention_rate"}:
        return round(random.uniform(1, 999), 2)

    return f"mock_{suffix}"


def build_mock_record(cursor, table_key, config):
    data = existing_record_seed(cursor, config)
    for column in config["insert_columns"]:
        if column not in data or data[column] is None:
            data[column] = mock_value_for_column(cursor, table_key, config, column, data)
    normalize_mock_record(cursor, table_key, data)
    return data


def existing_record_seed(cursor, config):
    columns = config["insert_columns"]
    if not columns:
        return {}
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    cursor.execute(
        f"SELECT {column_sql} FROM {quote_identifier(config['table'])} "
        "ORDER BY RAND() LIMIT 1"
    )
    row = cursor.fetchone() or {}
    return {column: row.get(column) for column in columns if column in row}


def normalize_mock_record(cursor, table_key, data):
    suffix = random_suffix()

    if table_key == "user":
        data.update({
            "username": f"user_mock_{suffix}@smart-speaker.local",
            "password_hash": uuid.uuid4().hex,
            "phone": None,
            "nickname": None,
            "avatar": None,
            "email": None,
            "status": None,
            "last_login_at": None,
        })
        return

    if table_key == "device":
        next_id = next_numeric_id(cursor, "device", "device_id")
        room = random_choice(["客厅", "卧室", "书房", "厨房", "阅读角", "健身房"])
        model = random_choice(["SH-Mini A1", "SH-Family Max", "SH-Lite"])
        data.update({
            "device_number": f"SHSPEAKER-{next_id:05d}",
            "model_name": model,
            "status": 1,
            "firmware_version": random_choice(["1.0.5", "1.1.0", "1.2.0"]),
            "last_active": random_datetime(7),
            "device_name": f"{room}音箱 {next_id % 1000}",
            "device_type": "speaker",
            "online_status": random_choice(["online", "offline"]),
            "ip_address": f"10.{random.randint(1, 30)}.{random.randint(1, 30)}.{random.randint(2, 240)}",
            "hardware_version": random_choice(["hw-1.0", "hw-2.0", "hw-2.1"]),
            "location": room,
        })
        return

    if table_key == "sales_order":
        next_id = next_numeric_id(cursor, "sales_order", "order_id")
        amount = random_choice([899, 999, 1299, 1599, 1999])
        paid = random.random() >= 0.15
        regions = [
            ("110000", "Beijing", "110100", "Beijing City"),
            ("310000", "Shanghai", "310100", "Shanghai City"),
            ("440000", "Guangdong", "440100", "Guangzhou City"),
            ("330000", "Zhejiang", "330100", "Hangzhou City"),
            ("500000", "Chongqing", "500100", "Chongqing City"),
        ]
        province_code, province_name, city_code, city_name = random_choice(regions)
        data.update({
            "order_no": f"ORD202606{next_id:06d}",
            "order_amount": amount,
            "pay_amount": amount if paid else 0,
            "order_status": "finished" if paid else "pending",
            "pay_status": random_choice(["paid", "success", "finished"]) if paid else "unpaid",
            "province_code": province_code,
            "province_name": province_name,
            "city_code": city_code,
            "city_name": city_name,
            "paid_at": random_datetime(30) if paid else None,
        })
        return

    if table_key == "daily_stats":
        total_devices = count_table(cursor, "device")
        total_users = count_table(cursor, "user")
        active_users = random.randint(20, max(20, min(total_users or 120, 80)))
        active_devices = random.randint(10, max(10, min(total_devices or 180, 60)))
        total_plays = random.randint(active_users, active_users * 3)
        duration = total_plays * random.randint(160, 260)
        hottest_song, hottest_artist = random_choice([
            ("稻香", "周杰伦"),
            ("晴天", "周杰伦"),
            ("夜曲", "周杰伦"),
            ("红豆", "王菲"),
            ("可惜没如果", "林俊杰"),
        ])
        data.update({
            "stat_date": date.today().isoformat(),
            "total_play_count": total_plays,
            "unique_song_count": random.randint(8, min(20, total_plays)),
            "unique_user_count": active_users,
            "active_user_count": active_users,
            "online_device_count": random.randint(active_devices, max(active_devices, min(total_devices or 180, 180))),
            "platform_wechat_count": active_users // 3,
            "platform_qq_count": active_users // 3,
            "unique_device_count": active_devices,
            "total_play_duration_seconds": duration,
            "avg_play_duration_seconds": round(duration / max(total_plays, 1), 2),
            "hottest_song_external_id": f"song_{random.randint(30001, 30020)}",
            "hottest_song_name": hottest_song,
            "hottest_artist": hottest_artist,
            "hottest_play_count": random.randint(5, max(5, min(total_plays, 30))),
            "new_user_count": random.randint(0, min(10, active_users)),
            "new_device_count": random.randint(0, min(5, active_devices)),
            "total_sales_amount": random_choice([0, 899, 1299, 2598, 3998, 5997]),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return

    if table_key == "hot_ranking_daily":
        cursor.execute(
            "SELECT COALESCE(MAX(rank_no), 0) + 1 AS value "
            "FROM hot_ranking_daily WHERE ranking_date = CURDATE() AND ranking_type = 'song'"
        )
        next_rank = int((cursor.fetchone() or {}).get("value") or 1)
        if next_rank > 10:
            next_rank = random.randint(1, 10)
        song_name, artist = random_choice([
            ("稻香", "周杰伦"),
            ("晴天", "周杰伦"),
            ("夜曲", "周杰伦"),
            ("红豆", "王菲"),
            ("可惜没如果", "林俊杰"),
            ("孤勇者", "陈奕迅"),
            ("光年之外", "邓紫棋"),
            ("一路向北", "周杰伦"),
        ])
        data.update({
            "ranking_date": date.today().isoformat(),
            "ranking_type": "song",
            "scope_type": "global",
            "scope_code": "all",
            "rank_no": next_rank,
            "target_id": f"song_{random.randint(30001, 39999)}",
            "target_name": song_name,
            "target_category": artist,
            "metric_value": random.randint(400, 1200),
            "metric_unit": "plays",
        })
        return

    if table_key == "region_stats_daily":
        users = random.randint(40, 120)
        devices = random.randint(max(20, users - 20), users + 40)
        orders = random.randint(0, min(devices, 18))
        data.update({
            "stat_date": date.today().isoformat(),
            "region_level": "city",
            "user_count": users,
            "active_user_count": random.randint(10, users),
            "device_count": devices,
            "order_count": orders,
            "sales_amount": orders * random_choice([899, 1299, 1999]),
        })
        return

    if table_key == "user_value_segment_daily":
        users = random.randint(20, 90)
        segment_code, segment_name = random_choice([
            ("high_value", "High Value"),
            ("normal", "Normal"),
            ("low_activity", "Low Activity"),
        ])
        data.update({
            "stat_date": date.today().isoformat(),
            "segment_code": segment_code,
            "segment_name": segment_name,
            "user_count": users,
            "active_user_count": random.randint(0, users),
            "avg_play_count": round(random.uniform(3, 40), 2),
            "avg_pay_amount": round(random.uniform(100, 1800), 2),
            "retention_rate": round(random.uniform(0.2, 0.9), 4),
        })
        return

    if table_key == "user_profile":
        active_level = random_choice(["high", "normal", "silent"])
        value_level = "high" if active_level == "high" else random_choice(["normal", "low"])
        data.update({
            "gender": random_choice(["male", "female", "unknown"]),
            "age": random.randint(18, 55),
            "age_range": random_choice(["18-25", "26-35", "36-45", "46+"]),
            "province_name": random_choice(["Beijing", "Shanghai", "Guangdong", "Zhejiang", "Chongqing"]),
            "city_name": random_choice(["Beijing City", "Shanghai City", "Guangzhou City", "Hangzhou City", "Chongqing City"]),
            "active_level": active_level,
            "value_level": value_level,
            "bound_platforms": random_choice(["qq", "netease", "qq,netease"]),
            "user_status": random_choice(["active", "normal"]),
        })
        return

    if table_key == "play_history":
        data.update({
            "play_duration": random.randint(30, 260),
            "style": random_choice(["normal", "ambient", "podcast", "pop"]),
            "created_at": random_datetime(30),
        })
        return

    if table_key == "user_feedback":
        next_id = next_numeric_id(cursor, "user_feedback", "feedback_id")
        feedback_type = random_choice(["bug", "suggestion", "praise"])
        data.update({
            "feedback_no": f"FB202606{next_id:06d}",
            "feedback_type": feedback_type,
            "title": random_choice(["配网到最后一步失败", "希望增加睡眠定时入口", "蓝牙重连后音量偏大"]),
            "content": random_choice([
                "家里 5G Wi-Fi 可以搜到，但输入密码后一直停在 90%。",
                "晚上听播客时希望更容易设置 30 分钟自动关闭。",
                "蓝牙断开后重新连接，音箱音量会突然变大。",
            ]),
            "contact": f"138****{random.randint(1000, 9999)}",
            "device_info": f"SHSPEAKER-{random.randint(1, 180):05d} / 微信小程序 1.2.5",
            "status": random_choice(["open", "processing", "processed"]),
            "priority": "high" if feedback_type == "bug" else "normal",
            "star_rating": random.randint(2, 5),
            "rating_tags": random_choice(["配网,Wi-Fi", "播放器,定时", "蓝牙,音量"]),
        })


def count_table(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) AS value FROM {quote_identifier(table_name)}")
    row = cursor.fetchone() or {}
    return int(row.get("value") or 0)


def build_mock_mongo_document(collection_name):
    now_text = random_datetime()
    suffix = random_suffix()
    samples = {
        "device_runtime": {
            "device_id": random.randint(10000, 99999),
            "deviceId": str(random.randint(10000, 99999)),
            "device_number": f"SHMINI-A1-{random.randint(1000, 9999)}",
            "online": random.choice([True, False]),
            "battery": random.randint(10, 100),
            "volume": random.randint(0, 100),
            "signalStrength": random.randint(-90, -35),
            "networkType": random.choice(["wifi", "4g"]),
        },
        "player_state": {
            "device_id": random.randint(10000, 99999),
            "isPlaying": random.choice([True, False]),
            "songId": f"song_{suffix}",
            "songName": random.choice(["晴天", "稻香", "夜曲", "七里香"]),
            "artist": random.choice(["周杰伦", "陈奕迅", "林俊杰"]),
            "source": random.choice(["netease", "qq"]),
            "playTime": random.randint(0, 240),
        },
        "play_queue": {
            "device_id": random.randint(10000, 99999),
            "queue": [
                {"songId": f"song_{suffix}", "songName": random.choice(["晴天", "稻香"]), "artist": "周杰伦"}
            ],
        },
        "operation_logs": {
            "requestId": f"REQ{suffix}",
            "device_id": random.randint(10000, 99999),
            "action": random.choice(["play", "pause", "volume"]),
            "source": "mock",
            "result": random.choice(["success", "failed"]),
        },
        "media_metadata": {
            "song_id": f"song_{suffix}",
            "external_id": f"song_{suffix}",
            "name": random.choice(["晴天", "稻香", "夜曲", "七里香"]),
            "artist": random.choice(["周杰伦", "陈奕迅", "林俊杰"]),
            "cover_url": f"https://example.com/covers/{suffix}.jpg",
            "duration": random.randint(160, 280),
        },
    }
    document = dict(samples.get(collection_name, {"name": f"mock_{suffix}", "value": random.randint(1, 1000)}))
    document["mock"] = True
    document["created_at"] = now_text
    document["updated_at"] = now_text
    return document


def mongo_collection_or_error(collection_name):
    db = mongo_db()
    if db is None:
        return None, error("MongoDB 连接失败", 500)
    if collection_name not in db.list_collection_names():
        return None, error(f"不支持的 MongoDB 集合: {collection_name}", 404)
    return db[collection_name], None


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
        schema_payload(key, config)
        for key, config in TABLE_CONFIG.items()
    ])


@db_api.route("/mysql/tables", methods=["GET"])
def list_mysql_tables():
    return list_supported_tables()


@db_api.route("/mongo/collections", methods=["GET"])
def list_mongo_collections():
    db = mongo_db()
    if db is None:
        return error("MongoDB 连接失败", 500)

    result = []
    for name in sorted(db.list_collection_names()):
        try:
            count = db[name].count_documents({})
        except Exception:
            count = 0
        result.append({"name": name, "count": count})
    return success({"database": db.name, "collections": result})


@db_api.route("/mongo/<collection_name>", methods=["GET"])
def list_mongo_documents(collection_name):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err

    try:
        limit = min(max(int(request.args.get("limit", "100")), 1), 500)
        offset = max(int(request.args.get("offset", "0")), 0)
    except ValueError:
        return error("limit 和 offset 必须是整数", 400)

    docs = list(collection.find({}).sort("_id", -1).skip(offset).limit(limit))
    total = collection.count_documents({})
    keys = []
    seen = set()
    for doc in docs:
        for key in doc.keys():
            if key not in seen:
                seen.add(key)
                keys.append(key)

    return success({
        "collection": collection_name,
        "total": total,
        "limit": limit,
        "offset": offset,
        "columns": keys,
        "list": json_safe(docs),
    })


@db_api.route("/mongo/<collection_name>", methods=["POST"])
def create_mongo_document(collection_name):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("请求体必须是 JSON 对象", 400)
    body.pop("_id", None)
    result = collection.insert_one(body)
    return success({"id": str(result.inserted_id)}, "新增成功")


@db_api.route("/mongo/<collection_name>/mock", methods=["POST"])
def create_mock_mongo_document(collection_name):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    body = build_mock_mongo_document(collection_name)
    result = collection.insert_one(body)
    return success({
        "id": str(result.inserted_id),
        "inserted": json_safe(body),
    }, "随机模拟数据已新增")


@db_api.route("/mongo/<collection_name>/sample", methods=["GET"])
def sample_mongo_document(collection_name):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    return success(build_mock_mongo_document(collection_name), "随机模拟数据已生成")


@db_api.route("/mongo/<collection_name>/<doc_id>", methods=["PUT", "PATCH"])
def update_mongo_document(collection_name, doc_id):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("请求体必须是 JSON 对象", 400)
    body.pop("_id", None)
    result = collection.update_one({"_id": parse_mongo_id(doc_id)}, {"$set": body})
    if result.matched_count == 0:
        return error("记录不存在", 404)
    return success({"matched": result.matched_count, "modified": result.modified_count}, "更新成功")


@db_api.route("/mongo/<collection_name>/<doc_id>", methods=["DELETE"])
def delete_mongo_document(collection_name, doc_id):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    result = collection.delete_one({"_id": parse_mongo_id(doc_id)})
    if result.deleted_count == 0:
        return error("记录不存在", 404)
    return success({"deleted": result.deleted_count}, "删除成功")


@db_api.route("/<table_key>/schema", methods=["GET"])
def table_schema(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err
    return success(schema_payload(table_key, config))


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
            "schema": schema_payload(table_key, config),
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
    if table_key == "daily_stats" and "stat_date" in columns:
        update_columns = [column for column in columns if column != "stat_date"]
        if update_columns:
            update_sql = ", ".join(
                f"{quote_identifier(column)} = VALUES({quote_identifier(column)})"
                for column in update_columns
            )
            sql = f"{sql} ON DUPLICATE KEY UPDATE {update_sql}"

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


@db_api.route("/<table_key>/mock", methods=["POST"])
def create_mock_record(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    table = config["table"]
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            data = build_mock_record(cursor, table_key, config)

            if not data:
                return error("当前表没有可新增字段", 400)

            columns = list(data.keys())
            values = [data[column] for column in columns]
            column_sql = ", ".join(quote_identifier(column) for column in columns)
            placeholder_sql = ", ".join(["%s"] * len(columns))
            sql = (
                f"INSERT INTO {quote_identifier(table)} "
                f"({column_sql}) VALUES ({placeholder_sql})"
            )
            cursor.execute(sql, values)
            new_id = cursor.lastrowid

        conn.commit()
        return success({
            "id": new_id,
            "inserted": serialize_row(data),
        }, "随机模拟数据已新增")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"随机新增失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


@db_api.route("/<table_key>/sample", methods=["GET"])
def sample_record(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            data = build_mock_record(cursor, table_key, config)
        return success(serialize_row(data), "随机模拟数据已生成")
    except Exception as exc:
        return error(f"随机数据生成失败: {exc}", 500)
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
