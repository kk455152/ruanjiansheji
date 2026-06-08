# db_api_service.py
from datetime import date, datetime
from decimal import Decimal
import time

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

    "user_activity_daily": {
        "table": "user_activity_daily",
        "pk": ["id"],
        "columns": [
            "id", "stat_date", "user_id", "play_count", "play_duration",
            "active_count", "is_active", "created_at", "last_active_at", "updated_at",
        ],
        "insert_columns": [
            "stat_date", "user_id", "play_count", "play_duration", "active_count",
            "is_active", "last_active_at",
        ],
        "update_columns": [
            "stat_date", "user_id", "play_count", "play_duration", "active_count",
            "is_active", "last_active_at",
        ],
    },

    "analytics_metric_daily": {
        "table": "analytics_metric_daily",
        "pk": ["metric_id"],
        "columns": [
            "metric_id", "metric_date", "scope_type", "scope_code", "metric_code",
            "metric_name", "metric_value", "metric_unit", "compare_value",
            "growth_rate", "created_at", "updated_at",
        ],
        "insert_columns": [
            "metric_date", "scope_type", "scope_code", "metric_code", "metric_name",
            "metric_value", "metric_unit", "compare_value", "growth_rate",
        ],
        "update_columns": [
            "metric_date", "scope_type", "scope_code", "metric_code", "metric_name",
            "metric_value", "metric_unit", "compare_value", "growth_rate",
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

FRONT_DATA_CATALOG = [
    {"group": "总览卡片", "title": "总用户", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/user-count", "table": "user", "fields": ["user_id", "created_at", "status"], "operation": "增加用户：在 user 表新增一行。减少用户：删除 user 行。新增用户数由 created_at=今天 的行数决定。"},
    {"group": "总览卡片", "title": "新增用户", "frontend": "数据总览 / 总用户提示", "api": "/api/admin/super/overview/user-count", "table": "user", "fields": ["created_at"], "operation": "把 user.created_at 改成今天会增加今日新增；改成历史日期会减少今日新增。"},
    {"group": "总览卡片", "title": "设备数 / 在线率", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/device-count", "table": "device", "fields": ["device_id", "status", "online_status", "created_at"], "operation": "设备数由 device 行数决定；在线设备由 status=1 决定。新增一台设备就新增一行，降低在线率就把部分设备 status 改为 0。"},
    {"group": "总览卡片", "title": "销售额 / 订单数", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/sales-amount", "table": "sales_order", "fields": ["pay_amount", "pay_status", "created_at"], "operation": "销售额统计 pay_status 为 paid/success/finished 的 pay_amount 总和；新增订单或调高 pay_amount 会增加，改成 pending/closed 会减少统计。"},
    {"group": "总览卡片", "title": "活跃度 / 活跃用户", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/activity-rate", "table": "user_profile", "fields": ["active_level", "user_id"], "operation": "活跃用户由 active_level='high' 的画像数量决定；把用户画像 active_level 改为 high 增加，改为 medium/low 减少。"},
    {"group": "趋势分析", "title": "用户/设备/销售趋势柱状图", "frontend": "趋势分析 / state.trend.list", "api": "/api/admin/super/trend/growth", "table": "daily_stats", "fields": ["stat_date", "new_user_count", "new_device_count", "total_sales_amount", "active_user_count"], "operation": "按 stat_date 找到对应日期行，用户趋势改 new_user_count，设备趋势改 new_device_count，销售趋势改 total_sales_amount。"},
    {"group": "地区热力", "title": "地区销售热力", "frontend": "地区热力 / 销售热力", "api": "/api/admin/super/region/sales-heatmap", "table": "region_stats_daily", "fields": ["stat_date", "region_name", "sales_amount", "order_count"], "operation": "修改最新 stat_date 下某地区 sales_amount/order_count；新增地区就新增一行并填写唯一 region_code。"},
    {"group": "地区热力", "title": "地区用户热力", "frontend": "地区热力 / 用户热力", "api": "/api/admin/super/region/user-heatmap", "table": "region_stats_daily", "fields": ["stat_date", "region_name", "user_count", "active_user_count"], "operation": "修改最新 stat_date 下 user_count/active_user_count；数值越大条形越长。"},
    {"group": "用户画像", "title": "年龄占比", "frontend": "用户画像 / 年龄分布饼图", "api": "/api/admin/super/user-profile/age-distribution", "table": "user_profile", "fields": ["age", "age_range"], "operation": "占比由 age_range 分组计数决定；要提高某年龄段占比，就新增/修改更多用户画像的 age_range 为该段。"},
    {"group": "用户画像", "title": "地区占比", "frontend": "用户画像 / 地区分布饼图", "api": "/api/admin/super/user-profile/region-distribution", "table": "user_profile", "fields": ["province_code", "province_name", "city_name"], "operation": "占比由 province_name 分组计数决定；修改用户画像省份即可调整地区占比。"},
    {"group": "用户画像", "title": "活跃分层占比", "frontend": "用户画像 / 活跃分层饼图", "api": "/api/admin/super/user-profile/activity-distribution", "table": "user_profile", "fields": ["active_level"], "operation": "占比由 active_level 分组计数决定；常用值 high/medium/low。"},
    {"group": "用户画像", "title": "绑定软件占比", "frontend": "用户画像 / 绑定软件饼图", "api": "/api/admin/super/user-profile/music-service-distribution", "table": "user_profile", "fields": ["bound_platforms"], "operation": "占比由 bound_platforms 分组计数决定；填写 qq、netease、wechat 或逗号组合。"},
    {"group": "用户价值", "title": "普通用户 / 高活用户环图", "frontend": "用户价值 / valueDonut", "api": "/api/admin/super/user-value/*", "table": "user_profile", "fields": ["active_level", "value_level"], "operation": "高活用户是 active_level='high' 的数量；普通用户是总画像数减高活用户数。"},
    {"group": "用户分群", "title": "分群人数 / 留存 / 均值", "frontend": "用户分群 / segmentPie 和表格", "api": "/api/admin/market/segments", "table": "user_value_segment_daily", "fields": ["stat_date", "segment_name", "user_count", "active_user_count", "avg_play_count", "avg_pay_amount", "retention_rate"], "operation": "修改最新 stat_date 下的分群行；新增分群需新增唯一 segment_code。"},
    {"group": "热歌排行", "title": "热歌播放量 / 名次", "frontend": "热歌排行 / state.songs", "api": "/api/admin/market/top-songs", "table": "hot_ranking_daily", "fields": ["ranking_date", "rank_no", "target_name", "target_category", "metric_value"], "operation": "修改最新 ranking_date 下 ranking_type='song' 的 target_name、target_category 和 metric_value；保存后系统会按 metric_value 从高到低自动重排名次。"},
    {"group": "留存", "title": "购买后 1/7/30 日留存", "frontend": "趋势分析 / 市场角色留存趋势", "api": "/api/admin/market/retention/device-purchase", "table": "sales_order", "fields": ["user_id", "pay_status", "created_at"], "operation": "购买人数来自已支付订单的 user_id；留存人数来自 play_history 中购买后对应日期范围内仍有播放的用户。"},
    {"group": "留存", "title": "播放留存来源", "frontend": "趋势分析 / 留存计算", "api": "/api/admin/market/retention/device-purchase", "table": "play_history", "fields": ["user_id", "created_at", "play_duration"], "operation": "给购买用户新增购买日后 1/7/30 天之后的播放记录，会提高对应留存计数。"},
    {"group": "运营管理", "title": "反馈总数 / 待处理数 / 评分", "frontend": "用户反馈", "api": "/api/admin/*/feedback/list", "table": "user_feedback", "fields": ["feedback_type", "status", "priority", "star_rating", "created_at"], "operation": "新增反馈行增加总数；status 改为 pending/open 会增加待处理，改为 processed/closed 会减少。"},
    {"group": "运营管理", "title": "设备列表 / 固件版本 / 在线状态", "frontend": "设备管理", "api": "/api/admin/operator/device/list", "table": "device", "fields": ["device_number", "model_name", "status", "firmware_version", "last_active"], "operation": "新增设备行会增加设备列表；status=1 显示在线，firmware_version 影响固件版本展示。"},
    {"group": "运营管理", "title": "设备所属用户 / 房间", "frontend": "设备详情 / bound-user", "api": "/api/admin/operator/device/bound-user", "table": "user_device_binding", "fields": ["user_id", "device_id", "custom_device_name", "default_room", "bind_time"], "operation": "绑定关系决定设备详情里的用户、设备别名和房间；新增绑定或修改 custom_device_name/default_room 即可调整。"},
    {"group": "运营管理", "title": "设备日志数量 / 内容", "frontend": "设备日志", "api": "/api/admin/operator/device/logs", "table": "device_log", "fields": ["log_type", "log_level", "title", "content", "created_at"], "operation": "新增日志行增加列表；修改 log_level/title/content 改变前端展示。"},
    {"group": "小程序播放", "title": "播放历史 / 歌曲名 / 播放次数", "frontend": "小程序播放历史、后台热歌来源", "api": "/api/play-history 与 /api/admin/market/top-songs", "table": "play_history", "fields": ["device_id", "user_id", "mapping_id", "play_duration", "created_at", "style"], "operation": "新增播放记录会增加播放历史；每日任务会把播放记录聚合到 hot_ranking_daily 和 daily_stats。"},
    {"group": "小程序播放", "title": "歌曲标题 / 歌手 / 平台", "frontend": "小程序当前歌曲、热歌排行", "api": "/api/song-info 与 /api/admin/market/top-songs", "table": "media_mapping", "fields": ["song_title", "artist", "platform", "external_id", "cover_url"], "operation": "修改 media_mapping 可改变歌曲名、歌手、平台和封面；play_history.mapping_id 关联到这张表。"},
    {"group": "日报任务", "title": "每日自动汇总时间", "frontend": "所有日报型图表", "api": "/api/db/daily-stats/run", "table": "daily_stats", "fields": ["generated_at", "updated_at"], "operation": "点击维护页的“运行每日汇总”会用当前真实时间刷新 generated_at/updated_at，并同步刷新所有日报表。"},
]


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
    insertable = set(create_columns(config))
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
        "insertColumns": create_columns(config),
        "updateColumns": config["update_columns"],
        "columnMeta": column_meta(table_key, config),
    }


def create_columns(config):
    explicit = set(config["insert_columns"])
    pk = set(config["pk"])
    columns = []
    for column in config["columns"]:
        if len(pk) == 1 and column in pk and column not in explicit:
            continue
        columns.append(column)
    return columns


def quote_identifier(name):
    return f"`{name}`"


def build_insert_statement(table, data):
    columns = list(data.keys())
    values = [data[column] for column in columns]
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    placeholder_sql = ", ".join(["%s"] * len(columns))
    sql = (
        f"INSERT INTO {quote_identifier(table)} "
        f"({column_sql}) VALUES ({placeholder_sql})"
    )
    return columns, values, sql


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


def age_range_for_age(age):
    try:
        value = int(age)
    except (TypeError, ValueError):
        return None
    if value < 18:
        return "18-"
    if value <= 25:
        return "18-25"
    if value <= 35:
        return "26-35"
    if value <= 45:
        return "36-45"
    return "46+"


def normalize_record(table_key, data):
    normalized = dict(data or {})
    if table_key == "user_profile" and normalized.get("age") not in (None, ""):
        fixed_range = age_range_for_age(normalized.get("age"))
        if fixed_range:
            normalized["age_range"] = fixed_range
    return normalized


UNIQUE_SAMPLE_FIELDS = {
    "user": ["username", "phone", "email"],
    "device": ["device_number"],
    "action_dict": ["action_code"],
    "admin_user": ["username", "job_no", "phone", "email", "wechat_open_id"],
    "auth_token": ["access_token", "refresh_token"],
    "media_mapping": ["external_id"],
    "sales_order": ["order_no"],
    "user_feedback": ["feedback_no"],
    "device_firmware_release": ["release_no"],
    "device_firmware_update_task": ["task_no"],
    "system_config": ["config_key"],
}


def unique_sample_suffix():
    return datetime.now().strftime("%m%d%H%M%S") + str(int(time.time() * 1000))[-3:]


def uniquify_sample_record(table_key, data):
    sample = dict(data or {})
    suffix = unique_sample_suffix()
    for field in UNIQUE_SAMPLE_FIELDS.get(table_key, []):
        value = sample.get(field)
        if value in (None, ""):
            continue
        text = str(value)
        if field == "email" and "@" in text:
            name, domain = text.split("@", 1)
            sample[field] = f"{name}+{suffix}@{domain}"
        elif field == "phone":
            sample[field] = f"139{suffix[-8:]}"[:11]
        else:
            sample[field] = f"{text}-{suffix}"[:250]
    return normalize_record(table_key, sample)


def reorder_hot_ranking(cursor, ranking_date, ranking_type="song", scope_type="global", scope_code="global"):
    if not ranking_date:
        return
    cursor.execute(
        """
        SELECT ranking_id
        FROM hot_ranking_daily
        WHERE ranking_date=%s AND ranking_type=%s AND scope_type=%s AND scope_code=%s
        ORDER BY metric_value DESC, rank_no ASC, target_name ASC, ranking_id ASC
        """,
        (ranking_date, ranking_type, scope_type, scope_code),
    )
    rows = cursor.fetchall() or []
    if not rows:
        return
    ids = [row["ranking_id"] for row in rows]
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"UPDATE hot_ranking_daily SET rank_no = -ranking_id WHERE ranking_id IN ({placeholders})",
        ids,
    )
    for index, ranking_id in enumerate(ids, start=1):
        cursor.execute(
            "UPDATE hot_ranking_daily SET rank_no=%s WHERE ranking_id=%s",
            (index, ranking_id),
        )


def hot_ranking_group(record):
    if not record:
        return None
    ranking_date = record.get("ranking_date")
    if isinstance(ranking_date, (datetime, date)):
        ranking_date = ranking_date.isoformat()
    return (
        ranking_date,
        record.get("ranking_type") or "song",
        record.get("scope_type") or "global",
        record.get("scope_code") or "global",
    )


def fetch_hot_ranking_group(cursor, ranking_id):
    cursor.execute(
        """
        SELECT ranking_date, ranking_type, scope_type, scope_code
        FROM hot_ranking_daily
        WHERE ranking_id=%s
        """,
        (ranking_id,),
    )
    return hot_ranking_group(cursor.fetchone())


def next_hot_rank_no(cursor, group):
    if not group or not group[0]:
        return 1
    cursor.execute(
        """
        SELECT COALESCE(MAX(rank_no), 0) + 1 AS next_rank
        FROM hot_ranking_daily
        WHERE ranking_date=%s AND ranking_type=%s AND scope_type=%s AND scope_code=%s
        """,
        group,
    )
    row = cursor.fetchone() or {}
    return int(row.get("next_rank") or 1)


def temporary_hot_rank_no(pk_value):
    try:
        value = abs(int(pk_value))
    except (TypeError, ValueError):
        value = int(time.time() * 1000)
    return -max(value, 1)


def prepare_hot_ranking_create(cursor, data):
    if not data.get("ranking_date"):
        data["ranking_date"] = date.today().isoformat()
    data["ranking_type"] = data.get("ranking_type") or "song"
    data["scope_type"] = data.get("scope_type") or "global"
    data["scope_code"] = data.get("scope_code") or "global"
    data["metric_unit"] = data.get("metric_unit") or "plays"
    data["rank_no"] = next_hot_rank_no(cursor, hot_ranking_group(data))


def reorder_hot_ranking_groups(cursor, *groups):
    seen = set()
    for group in groups:
        if not group or not group[0] or group in seen:
            continue
        seen.add(group)
        reorder_hot_ranking(cursor, *group)


def parse_mongo_id(value):
    if ObjectId is not None:
        try:
            return ObjectId(value)
        except Exception:
            pass
    return value



# 新增草稿里的时间列需要重置为“当前时间”，否则复制旧记录会把历史时间一起带入，
# 导致维护页新增的数据时间不是现在。date 列填当前日期，datetime 列填当前时间戳。
DATE_COLUMN_NAMES = {"stat_date", "ranking_date", "metric_date"}
# not null 且无默认值的时间列：sample 时必须给当前时间，否则新增会因缺值失败
EXTRA_DATETIME_COLUMNS = {"last_active", "bind_time", "generated_at"}


def is_date_column(name):
    return name in DATE_COLUMN_NAMES or name.endswith("_date")


def is_datetime_column(name):
    return name in EXTRA_DATETIME_COLUMNS or name.endswith("_at")


def reset_sample_timestamps(data):
    """把新增草稿中的时间列重置为当前时间，保证新增数据时间是现在。"""
    if not data:
        return data
    now = datetime.now()
    now_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
    now_date = now.strftime("%Y-%m-%d")
    for key in list(data.keys()):
        if is_date_column(key):
            data[key] = now_date
        elif is_datetime_column(key):
            data[key] = now_datetime
    return data


def existing_record_seed(cursor, config):
    columns = create_columns(config)
    if not columns:
        return {}
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    cursor.execute(
        f"SELECT {column_sql} FROM {quote_identifier(config['table'])} "
        "ORDER BY RAND() LIMIT 1"
    )
    row = cursor.fetchone() or {}
    return {column: row.get(column) for column in columns if column in row}


def build_sample_record(cursor, config):
    # 复制一条真实记录做草稿，但时间列重置为当前时间，避免带入历史时间
    return reset_sample_timestamps(existing_record_seed(cursor, config))


def sample_mongo_document_from_collection(collection):
    doc = collection.find_one(sort=[("_id", -1)])
    if not doc:
        return {}
    doc = dict(doc)
    doc.pop("_id", None)
    # MongoDB 文档里的时间字段同样重置为当前时间
    return reset_sample_timestamps(doc)

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


def scalar_value(cursor, sql, params=(), default=0):
    cursor.execute(sql, params)
    row = cursor.fetchone() or {}
    value = next(iter(row.values()), default)
    return value if value is not None else default


def front_catalog_snapshot():
    snapshot = {}
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            user_count = scalar_value(cursor, "SELECT COUNT(*) AS c FROM `user`")
            new_user_count = scalar_value(cursor, "SELECT COUNT(*) AS c FROM `user` WHERE DATE(created_at)=CURDATE()")
            device_count = scalar_value(cursor, "SELECT COUNT(*) AS c FROM device")
            online_device_count = scalar_value(cursor, "SELECT COUNT(*) AS c FROM device WHERE COALESCE(status, 0)=1")
            sales_amount = scalar_value(cursor, "SELECT COALESCE(SUM(pay_amount),0) AS c FROM sales_order WHERE pay_status IN ('paid','success','finished')")
            order_count = scalar_value(cursor, "SELECT COUNT(*) AS c FROM sales_order WHERE pay_status IN ('paid','success','finished')")
            high_active = scalar_value(cursor, "SELECT COUNT(*) AS c FROM user_profile WHERE active_level='high'")
            profile_total = scalar_value(cursor, "SELECT COUNT(*) AS c FROM user_profile")
            age_bad = scalar_value(
                cursor,
                """
                SELECT COUNT(*) AS c
                FROM user_profile
                WHERE age IS NOT NULL
                  AND COALESCE(age_range, '') <> CASE
                    WHEN age < 18 THEN '18-'
                    WHEN age <= 25 THEN '18-25'
                    WHEN age <= 35 THEN '26-35'
                    WHEN age <= 45 THEN '36-45'
                    ELSE '46+'
                  END
                """,
            )
            cursor.execute(
                """
                SELECT COALESCE(age_range, 'unknown') AS label, COUNT(*) AS count_value
                FROM user_profile
                GROUP BY COALESCE(age_range, 'unknown')
                ORDER BY count_value DESC
                LIMIT 4
                """
            )
            age_rows = cursor.fetchall() or []
            cursor.execute(
                """
                SELECT target_name, metric_value
                FROM hot_ranking_daily
                WHERE ranking_type='song'
                  AND ranking_date=(SELECT MAX(ranking_date) FROM hot_ranking_daily WHERE ranking_type='song')
                ORDER BY metric_value DESC, rank_no ASC, target_name ASC
                LIMIT 1
                """
            )
            top_song = cursor.fetchone() or {}
            cursor.execute(
                """
                SELECT segment_name, user_count
                FROM user_value_segment_daily
                WHERE stat_date=(SELECT MAX(stat_date) FROM user_value_segment_daily)
                ORDER BY user_count DESC
                LIMIT 1
                """
            )
            top_segment = cursor.fetchone() or {}
            snapshot.update({
                "user": f"{int(user_count or 0)} 人，今日新增 {int(new_user_count or 0)}",
                "device": f"{int(device_count or 0)} 台，在线 {int(online_device_count or 0)}",
                "sales_order": f"{float(sales_amount or 0):.2f} 元，{int(order_count or 0)} 笔已支付订单",
                "activity": f"{int(high_active or 0)} 个高活画像 / 共 {int(profile_total or 0)} 个画像",
                "daily_stats": "最新日报趋势来自 daily_stats，改完基础表后请点“运行每日汇总”",
                "region_stats_daily": "地区热力读取最新 stat_date 的地区行",
                "user_profile_age": "；".join(f"{row.get('label')}: {int(row.get('count_value') or 0)}" for row in age_rows) or "暂无年龄分布",
                "user_profile_age_bad": f"{int(age_bad or 0)} 条年龄段不一致",
                "user_profile": f"{int(profile_total or 0)} 个画像，{int(age_bad or 0)} 条年龄段不一致",
                "user_value_segment_daily": f"最大分群：{top_segment.get('segment_name') or '-'} {int(top_segment.get('user_count') or 0)} 人",
                "hot_ranking_daily": f"当前第 1：{top_song.get('target_name') or '-'}，播放 {int(top_song.get('metric_value') or 0)}",
                "user_feedback": f"{int(scalar_value(cursor, 'SELECT COUNT(*) AS c FROM user_feedback') or 0)} 条反馈",
                "device_log": f"{int(scalar_value(cursor, 'SELECT COUNT(*) AS c FROM device_log') or 0)} 条日志",
                "play_history": f"{int(scalar_value(cursor, 'SELECT COUNT(*) AS c FROM play_history') or 0)} 条播放记录",
                "media_mapping": f"{int(scalar_value(cursor, 'SELECT COUNT(*) AS c FROM media_mapping') or 0)} 首歌曲映射",
            })
    except Exception as exc:
        snapshot["error"] = f"当前值读取失败：{exc}"
    finally:
        if conn:
            conn.close()
    return snapshot


def attach_catalog_current_values(items):
    snapshot = front_catalog_snapshot()
    enriched = []
    for item in items:
        copy = dict(item)
        table = copy.get("table")
        title = copy.get("title") or ""
        if title == "年龄占比":
            copy["current"] = snapshot.get("user_profile_age")
            copy["warning"] = snapshot.get("user_profile_age_bad")
        elif title in ("普通用户 / 高活用户环图", "活跃度 / 活跃用户"):
            copy["current"] = snapshot.get("activity")
        else:
            copy["current"] = snapshot.get(table) or snapshot.get("error") or "暂无当前值"
        enriched.append(copy)
    return enriched


@db_api.route("/maintenance/fix-logical-data", methods=["POST"])
def fix_logical_data():
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_profile
                SET age_range = CASE
                    WHEN age IS NULL THEN age_range
                    WHEN age < 18 THEN '18-'
                    WHEN age <= 25 THEN '18-25'
                    WHEN age <= 35 THEN '26-35'
                    WHEN age <= 45 THEN '36-45'
                    ELSE '46+'
                END,
                updated_at = NOW()
                WHERE age IS NOT NULL
                  AND COALESCE(age_range, '') <> CASE
                    WHEN age < 18 THEN '18-'
                    WHEN age <= 25 THEN '18-25'
                    WHEN age <= 35 THEN '26-35'
                    WHEN age <= 45 THEN '36-45'
                    ELSE '46+'
                  END
                """
            )
            fixed_age_ranges = cursor.rowcount
        conn.commit()
        return success({"fixedAgeRanges": fixed_age_ranges}, "逻辑数据修复完成")
    except Exception as exc:
        if conn:
            conn.rollback()
        return error(f"逻辑数据修复失败: {exc}", 500)
    finally:
        if conn:
            conn.close()


@db_api.route("/front-data-catalog", methods=["GET"])
def front_data_catalog():
    items = attach_catalog_current_values(FRONT_DATA_CATALOG)
    return success({
        "total": len(items),
        "list": items,
    })


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
    return error("mock data generation is disabled; use the create form for real data", 400)


@db_api.route("/mongo/<collection_name>/sample", methods=["GET"])
def sample_mongo_document(collection_name):
    collection, err = mongo_collection_or_error(collection_name)
    if err:
        return err
    return success(json_safe(sample_mongo_document_from_collection(collection)), "real sample loaded")


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

    if table_key == "hot_ranking_daily":
        order_sql = "`ranking_date` DESC, `metric_value` DESC, `rank_no` ASC, `target_name` ASC, `ranking_id` ASC"
    else:
        pk_order = ", ".join(quote_identifier(column) for column in config["pk"])
        order_sql = f"{pk_order} DESC"
    column_sql = ", ".join(quote_identifier(column) for column in columns)

    sql = (
        f"SELECT {column_sql} "
        f"FROM {quote_identifier(table)} "
        f"{where_sql} "
        f"ORDER BY {order_sql} "
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
    insert_columns = create_columns(config)

    data = normalize_record(table_key, pick_allowed_fields(body, insert_columns))

    if not data:
        return error("没有可新增的字段", 400)

    columns, values, sql = build_insert_statement(table, data)
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
            if table_key == "hot_ranking_daily":
                prepare_hot_ranking_create(cursor, data)
                columns, values, sql = build_insert_statement(table, data)
            cursor.execute(sql, values)
            new_id = cursor.lastrowid
            if table_key == "hot_ranking_daily":
                reorder_hot_ranking_groups(cursor, hot_ranking_group(data))

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
    return error("mock data generation is disabled; use the create form for real data", 400)


@db_api.route("/<table_key>/sample", methods=["GET"])
def sample_record(table_key):
    config, err = get_config_or_error(table_key)
    if err:
        return err

    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            data = uniquify_sample_record(table_key, build_sample_record(cursor, config))
        return success(serialize_row(data), "real sample loaded")
    except Exception as exc:
        return error(f"real sample load failed: {exc}", 500)
    finally:
        if conn:
            conn.close()


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

    data = normalize_record(table_key, pick_allowed_fields(body, update_columns))

    if not data:
        return error("没有可修改的字段", 400)

    if table_key == "hot_ranking_daily":
        data["rank_no"] = temporary_hot_rank_no(pk_value)

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
            old_hot_group = fetch_hot_ranking_group(cursor, pk_value) if table_key == "hot_ranking_daily" else None
            cursor.execute(sql, params)

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在或内容未变化", 404)

            if table_key == "hot_ranking_daily":
                new_hot_group = fetch_hot_ranking_group(cursor, pk_value)
                reorder_hot_ranking_groups(cursor, old_hot_group, new_hot_group)

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
            old_hot_group = fetch_hot_ranking_group(cursor, pk_value) if table_key == "hot_ranking_daily" else None
            cursor.execute(sql, (pk_value,))

            if cursor.rowcount == 0:
                conn.rollback()
                return error("数据不存在", 404)

            if table_key == "hot_ranking_daily":
                reorder_hot_ranking_groups(cursor, old_hot_group)

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
