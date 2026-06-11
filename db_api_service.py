# db_api_service.py
from datetime import date, datetime
from decimal import Decimal
import time
import uuid

from flask import Blueprint, jsonify, request

from db_config import get_mysql_connection
from api_pkg.common import json_safe, mongo_db

try:
    from bson import ObjectId
except Exception:
    ObjectId = None


db_api = Blueprint("db_api", __name__, url_prefix="/api/db")
ONLINE_DEVICE_VALUE_SQL = """
CASE
    WHEN LOWER(TRIM(COALESCE(online_status, ''))) IN ('online', 'true', '1', 'yes')
         OR TRIM(COALESCE(online_status, '')) = '在线' THEN 1
    WHEN LOWER(TRIM(COALESCE(online_status, ''))) IN ('offline', 'false', '0', 'no')
         OR TRIM(COALESCE(online_status, '')) = '离线' THEN 0
    ELSE CASE WHEN COALESCE(status, 0) = 1 THEN 1 ELSE 0 END
END
"""
ONLINE_DEVICE_CONDITION = f"({ONLINE_DEVICE_VALUE_SQL}) = 1"

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
    "admin_auth_token": "后台登录令牌",
    "admin_role": "后台角色",
    "admin_permission": "后台权限",
    "admin_user_role": "管理员角色关联",
    "admin_role_permission": "角色权限关联",
    "admin_data_scope": "后台数据范围",
    "admin_login_log": "后台登录日志",
    "security_event_log": "安全事件日志",
    "data_job_task": "数据任务记录",
    "high_risk_operation": "高风险操作",
    "system_backup_task": "系统备份任务",
    "system_upgrade_package": "系统升级包",
    "device_settings": "设备设置",
    "battery_notice_setting": "电量提醒设置",
    "device_bind_task": "设备绑定任务",
    "music_service_binding": "音乐服务绑定",
    "music_service_permission": "音乐服务权限",
    "listen_room": "一起听房间",
    "listen_room_member": "一起听成员",
    "listen_room_comment": "一起听评论",
    "share_record": "分享记录",
    "sales_order_item": "销售订单明细",
    "user_feedback_process_log": "反馈处理日志",
}

FIELD_COMMENTS = {
    "id": ("ID", "系统自增主键。"),
    "user_id": ("用户ID", "关联 user 表的小程序用户主键。"),
    "username": ("用户名", "演示数据使用不带数字尾号的中文姓名，唯一性由生成批次控制。"),
    "password_hash": ("密码", "当前按要求直接存明文密码，方便维护页查看和修改。"),
    "phone": ("手机号", "用户或管理员联系电话。"),
    "created_at": ("创建时间", "记录创建时间，格式 YYYY-MM-DD HH:MM:SS。"),
    "updated_at": ("更新时间", "记录最后更新时间。"),
    "nickname": ("昵称", "用户展示称呼，使用自然简称或音乐化昵称，不直接照抄用户名。"),
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
    "device_number": ("设备编号", "设备唯一 SN/编号，如 SPK-A1-0001。"),
    "device_sn": ("设备SN", "对外展示的设备序列号。"),
    "model_name": ("设备型号", "演示数据只使用 A1、A2、B1 三种型号，方便筛选和记忆。"),
    "device_model": ("设备型号", "日志中记录的设备型号。"),
    "device_name": ("设备名称", "设备展示名称，如客厅音箱。"),
    "device_type": ("设备类型", "音箱填 speaker；真实表为必填字段。"),
    "firmware_version": ("固件版本", "演示数据只使用 v1.0.0、v1.0.1、v1.1.0。"),
    "last_active": ("最后活跃时间", "设备最后一次心跳或活跃时间。"),
    "online_status": ("在线状态", "online 或 offline。"),
    "ip_address": ("IP地址", "设备或操作来源 IP。"),
    "hardware_version": ("硬件版本", "设备硬件版本，默认 default。"),
    "location": ("位置", "设备所在房间或地区。"),
    "auth_id": ("授权ID", "音乐平台授权记录主键。"),
    "platform_type": ("平台类型", "第三方平台类型，如 网易云音乐、QQ音乐。"),
    "access_token": ("访问令牌", "登录或第三方平台访问令牌。"),
    "refresh_token": ("刷新令牌", "用于刷新 access_token 的令牌。"),
    "expires_at": ("过期时间", "令牌过期时间。"),
    "mapping_id": ("歌曲映射ID", "media_mapping 表主键。"),
    "song_title": ("歌曲名", "歌曲标题。"),
    "artist": ("歌手", "歌手或艺术家名称。"),
    "platform": ("音乐平台", "歌曲来源平台，如 网易云音乐、QQ音乐。"),
    "external_id": ("外部歌曲ID", "第三方音乐平台歌曲 ID。"),
    "cover_url": ("封面地址", "歌曲封面图片 URL。"),
    "action_id": ("操作ID", "操作字典主键。"),
    "action_code": ("操作编码", "机器可读的操作编码。"),
    "action_name": ("操作名称", "人可读的操作名称。"),
    "category": ("分类", "操作分类。"),
    "history_id": ("历史ID", "播放历史主键。"),
    "play_duration": ("播放时长", "播放时长，单位秒。"),
    "style": ("音乐风格", "歌曲或播放记录风格，如 pop、rock。"),
    "source_platform": ("来源平台", "播放记录来源平台，如 网易云音乐、QQ音乐。"),
    "user_id_1": ("用户1", "好友关系中的第一个用户 ID。"),
    "user_id_2": ("用户2", "好友关系中的第二个用户 ID。"),
    "binding_id": ("绑定ID", "用户设备绑定表自增主键。"),
    "custom_device_name": ("自定义设备名", "用户给设备设置的显示名称，演示数据按房间和使用场景生成，如客厅 Mini、书桌音箱、床头音箱。"),
    "is_primary": ("是否主设备", "1 表示主设备，0 表示非主设备。"),
    "default_room": ("默认房间", "设备所在默认房间。"),
    "current_network": ("当前网络", "设备当前连接的真实风格 Wi-Fi SSID，使用英文/数字前缀和 4 位后缀，如 ChinaNet-5G-A8F2。"),
    "bind_time": ("绑定时间", "用户绑定设备的时间；解绑只删除这张绑定表的关系，不删除 device 设备本体。"),
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
    "platform_wechat_count": ("网易云音乐用户数", "历史字段名沿用 platform_wechat_count，当前统计绑定网易云音乐的画像数量。"),
    "platform_qq_count": ("QQ音乐用户数", "绑定 QQ 音乐的画像数量。"),
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
    "bound_platforms": ("绑定平台", "用户绑定的音乐平台列表，如 网易云音乐、QQ音乐。"),
    "user_status": ("用户状态", "用户画像中的业务状态。"),
    "region_code": ("地区编码", "地区行政区编码。"),
    "region_level": ("地区层级", "province 或 city。"),
    "region_name": ("地区名称", "地区展示名称。"),
    "user_count": ("用户数", "统计范围内用户数量。"),
    "device_count": ("设备数", "统计范围内设备数量。"),
    "order_count": ("订单数", "地区热力里为截至 stat_date 的累计已支付订单数；日报主表里为当天订单数。"),
    "sales_amount": ("销售额", "地区热力里为截至 stat_date 的累计已支付销售额，和累计用户分布保持同口径。"),
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
    "scope_type": ("范围类型", "platform 表示按音乐平台统计；历史 global 数据会在接口中兼容。"),
    "scope_code": ("范围编码", "音乐平台名称，如 网易云音乐、QQ音乐。"),
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
    "log_type": ("日志类型", "online、network、firmware、play、system 等设备事件类型。"),
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
    "config_key": ("配置键", "系统配置英文键；公告通常为 notice.时间戳 或 notice.daily.日期。"),
    "config_value": ("配置值", "系统配置值；系统公告标题也保存在这里。"),
    "config_type": ("配置类型", "string、number、boolean、json。"),
    "config_group": ("配置分组", "配置所属分组；公告使用 notice/notices/system_notice，运营建议使用 market_recommendation。"),
    "config_name": ("配置名称", "配置中文名称。"),
    "editable": ("可编辑", "1 表示维护页可编辑，0 表示不可编辑。"),
    "updated_by": ("更新人", "最后更新该配置的管理员 ID。"),
    "action": ("动作", "后台操作动作编码。"),
    "module": ("模块", "后台模块编码。"),
    "operation_name": ("操作内容", "审计日志中人可读的操作，例如登录系统、解绑设备、发布固件、处理反馈。"),
    "path": ("接口路径", "被访问的接口路径。"),
    "user_agent": ("浏览器信息", "请求来源 User-Agent。"),
    "params": ("请求参数", "操作请求参数，通常为 JSON 文本。"),
    "result_status": ("操作结果", "success 表示成功，failed/error 表示失败。"),
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
            "source_platform",
        ],
        "insert_columns": [
            "device_id",
            "user_id",
            "mapping_id",
            "play_duration",
            "created_at",
            "style",
            "source_platform",
        ],
        "update_columns": [
            "device_id",
            "user_id",
            "mapping_id",
            "play_duration",
            "created_at",
            "style",
            "source_platform",
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
    {"group": "总览卡片", "title": "设备数 / 在线率", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/device-count", "table": "device", "fields": ["device_id", "online_status", "status", "created_at"], "operation": "设备数由 device 行数决定；在线率优先看 online_status：online=在线、offline=离线；online_status 为空时才回退 status=1/0。"},
    {"group": "总览卡片", "title": "销售额 / 订单数", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/sales-amount", "table": "sales_order", "fields": ["pay_amount", "pay_status", "created_at"], "operation": "销售额统计 pay_status 为 paid/success/finished 的 pay_amount 总和；新增订单或调高 pay_amount 会增加，改成 pending/closed 会减少统计。"},
    {"group": "总览卡片", "title": "活跃度 / 活跃用户", "frontend": "数据总览 / metricCards", "api": "/api/admin/super/overview/activity-rate", "table": "user_profile", "fields": ["active_level", "user_id"], "operation": "活跃用户由 active_level='high' 的画像数量决定；把用户画像 active_level 改为 high 增加，改为 medium/low 减少。"},
    {"group": "趋势分析", "title": "用户/设备/销售趋势柱状图", "frontend": "趋势分析 / state.trend.list", "api": "/api/admin/super/trend/growth", "table": "daily_stats", "fields": ["stat_date", "new_user_count", "new_device_count", "total_sales_amount", "active_user_count"], "operation": "按 stat_date 找到对应日期行，用户趋势改 new_user_count，设备趋势改 new_device_count，销售趋势改 total_sales_amount。"},
    {"group": "地区热力", "title": "地区销售热力", "frontend": "地区热力 / 销售热力", "api": "/api/admin/super/region/sales-heatmap", "table": "region_stats_daily", "fields": ["stat_date", "region_name", "sales_amount", "order_count"], "operation": "销售热力读取最新 stat_date 的累计地区销售额，来自 sales_order 中截至该日的已支付订单；要调整就改 sales_order 的地区或金额后重跑每日汇总。"},
    {"group": "地区热力", "title": "地区用户热力", "frontend": "地区热力 / 用户热力", "api": "/api/admin/super/region/user-heatmap", "table": "region_stats_daily", "fields": ["stat_date", "region_name", "user_count", "active_user_count"], "operation": "用户热力读取最新 stat_date 的累计地区用户数，来自 user_profile.province_name；要调整就改用户画像地区后重跑每日汇总。"},
    {"group": "用户画像", "title": "年龄占比", "frontend": "用户画像 / 年龄分布饼图", "api": "/api/admin/super/user-profile/age-distribution", "table": "user_profile", "fields": ["age", "age_range"], "operation": "占比由 age_range 分组计数决定；要提高某年龄段占比，就新增/修改更多用户画像的 age_range 为该段。"},
    {"group": "用户画像", "title": "地区占比", "frontend": "用户画像 / 地区分布饼图", "api": "/api/admin/super/user-profile/region-distribution", "table": "user_profile", "fields": ["province_code", "province_name", "city_name"], "operation": "占比由 province_name 分组计数决定；修改用户画像省份即可调整地区占比。"},
    {"group": "用户画像", "title": "活跃分层占比", "frontend": "用户画像 / 活跃分层饼图", "api": "/api/admin/super/user-profile/activity-distribution", "table": "user_profile", "fields": ["active_level"], "operation": "占比由 active_level 分组计数决定；常用值 high/medium/low。"},
    {"group": "用户画像", "title": "绑定软件占比", "frontend": "用户画像 / 绑定软件饼图", "api": "/api/admin/super/user-profile/music-service-distribution", "table": "user_profile", "fields": ["bound_platforms"], "operation": "只归并为两个类别：网易云音乐、QQ音乐；历史逗号组合会拆开计入这两个桶，不再作为第三类显示。"},
    {"group": "用户价值", "title": "普通用户 / 高活用户环图", "frontend": "用户价值 / valueDonut", "api": "/api/admin/super/user-value/*", "table": "user_profile", "fields": ["active_level", "value_level"], "operation": "高活用户是 active_level='high' 的数量；普通用户是总画像数减高活用户数。"},
    {"group": "用户分群", "title": "分群人数 / 留存 / 均值", "frontend": "用户分群 / segmentPie 和表格", "api": "/api/admin/market/segments", "table": "user_value_segment_daily", "fields": ["stat_date", "segment_name", "user_count", "active_user_count", "avg_play_count", "avg_pay_amount", "retention_rate"], "operation": "修改最新 stat_date 下的分群行；新增分群需新增唯一 segment_code。"},
    {"group": "热歌排行", "title": "热歌播放量 / 名次", "frontend": "热歌排行 / state.songs", "api": "/api/admin/market/top-songs", "table": "hot_ranking_daily", "fields": ["ranking_date", "scope_code", "rank_no", "target_name", "target_category", "metric_value"], "operation": "热歌平台来源来自 play_history.source_platform 或 media_mapping.platform；手工维护时 scope_code 填 网易云音乐 或 QQ音乐，保存后按 metric_value 从高到低自动重排名次。"},
    {"group": "留存", "title": "购买后 1/7/30 日留存", "frontend": "趋势分析 / 市场角色留存趋势", "api": "/api/admin/market/retention/device-purchase", "table": "sales_order", "fields": ["user_id", "pay_status", "created_at"], "operation": "购买人数来自已支付订单的 user_id；留存人数来自 play_history 中购买后对应日期范围内仍有播放的用户。"},
    {"group": "留存", "title": "播放留存来源", "frontend": "趋势分析 / 留存计算", "api": "/api/admin/market/retention/device-purchase", "table": "play_history", "fields": ["user_id", "created_at", "play_duration"], "operation": "给购买用户新增购买日后 1/7/30 天之后的播放记录，会提高对应留存计数。"},
    {"group": "运营管理", "title": "反馈总数 / 待处理数 / 评分", "frontend": "用户反馈", "api": "/api/admin/*/feedback/list", "table": "user_feedback", "fields": ["feedback_type", "status", "priority", "star_rating", "created_at"], "operation": "新增反馈行增加总数；status 改为 pending/open 会增加待处理，改为 processed/closed 会减少。"},
    {"group": "运营管理", "title": "设备列表 / 固件版本 / 在线状态", "frontend": "设备管理", "api": "/api/admin/operator/device/list", "table": "device", "fields": ["device_number", "model_name", "online_status", "status", "firmware_version", "last_active"], "operation": "新增设备行会增加设备列表；online_status=online 显示在线、offline 显示离线；online_status 为空才看 status，firmware_version 影响固件版本展示。"},
    {"group": "运营管理", "title": "设备所属用户 / 房间", "frontend": "设备详情 / bound-user", "api": "/api/admin/operator/device/bound-user", "table": "user_device_binding", "fields": ["user_id", "device_id", "custom_device_name", "default_room", "bind_time"], "operation": "绑定关系决定设备详情里的用户、设备别名和房间；新增绑定或修改 custom_device_name/default_room 即可调整。"},
    {"group": "运营管理", "title": "设备日志数量 / 内容", "frontend": "设备日志", "api": "/api/admin/operator/device/logs", "table": "device_log", "fields": ["log_type", "log_level", "title", "content", "created_at"], "operation": "新增日志行增加列表；修改 log_level/title/content 改变前端展示。"},
    {"group": "小程序播放", "title": "播放历史 / 歌曲名 / 播放次数", "frontend": "小程序播放历史、后台热歌来源", "api": "/api/play-history 与 /api/admin/market/top-songs", "table": "play_history", "fields": ["device_id", "user_id", "mapping_id", "play_duration", "created_at", "style"], "operation": "新增播放记录会增加播放历史；每日任务会把播放记录聚合到 hot_ranking_daily 和 daily_stats。"},
    {"group": "小程序播放", "title": "歌曲标题 / 歌手 / 平台", "frontend": "小程序当前歌曲、热歌排行", "api": "/api/song-info 与 /api/admin/market/top-songs", "table": "media_mapping", "fields": ["song_title", "artist", "platform", "external_id", "cover_url"], "operation": "修改 media_mapping 可改变歌曲名、歌手、平台和封面；play_history.mapping_id 关联到这张表。"},
    {"group": "日报任务", "title": "每日自动汇总时间", "frontend": "所有日报型图表", "api": "/api/db/daily-stats/run", "table": "daily_stats", "fields": ["generated_at", "updated_at"], "operation": "“运行每日汇总”只聚合现有明细，并自动补齐上次汇总日期到今天之间漏掉的日报；每日新增明细由后端自动任务生成。"},
]

FRONT_DATA_CATALOG.extend([
    {"group": "决策驾驶舱", "title": "播放次数 / 活跃用户 / 活跃设备 / 平均播放时长", "frontend": "决策驾驶舱 / cards", "api": "/api/admin/super/decision/summary", "table": "daily_stats", "fields": ["stat_date", "total_play_count", "unique_user_count", "unique_device_count", "avg_play_duration_seconds"], "operation": "读取 daily_stats 最新日期；改 play_history 后需要运行每日汇总才会更新这些卡片。"},
    {"group": "决策驾驶舱", "title": "播放趋势", "frontend": "决策驾驶舱 / trend", "api": "/api/admin/super/decision/summary", "table": "daily_stats", "fields": ["stat_date", "total_play_count"], "operation": "按 stat_date 展示最近日报播放趋势；新增历史播放记录后运行每日汇总可补出对应日期趋势。"},
    {"group": "决策驾驶舱", "title": "异常风险提示", "frontend": "决策驾驶舱 / risks", "api": "/api/admin/super/decision/summary", "table": "system_config", "fields": ["config_group", "config_key", "config_name", "config_value", "config_type", "description"], "operation": "读取 config_group='decision_risk' 的配置项；新增配置行即可增加风险提示。"},
    {"group": "营销洞察", "title": "新增-绑定-首播-7日活跃漏斗", "frontend": "营销洞察 / funnels", "api": "/api/admin/market/insights", "table": "user", "fields": ["user_id", "created_at"], "operation": "漏斗按近 30 天新增用户逐级推导：新增用户 -> 已绑定设备 -> 绑定后完成首播 -> 首播后跨天且最近 7 天仍播放。"},
    {"group": "营销洞察", "title": "绑定设备漏斗步骤", "frontend": "营销洞察 / 绑定设备", "api": "/api/admin/market/insights", "table": "user_device_binding", "fields": ["user_id", "device_id", "bind_time"], "operation": "绑定设备步骤来自 user_device_binding；bind_time 必须不早于用户创建时间且不晚于当前时间。"},
    {"group": "营销洞察", "title": "首播 / 7日活跃漏斗步骤", "frontend": "营销洞察 / 首播与活跃", "api": "/api/admin/market/insights", "table": "play_history", "fields": ["user_id", "created_at", "play_duration"], "operation": "首播要求绑定后存在播放记录；7 日活跃要求该用户至少两个播放日期，且最后播放在最近 7 天内。"},
    {"group": "营销洞察", "title": "运营建议", "frontend": "营销洞察 / recommendations", "api": "/api/admin/market/insights", "table": "system_config", "fields": ["config_group", "config_name", "config_value", "description"], "operation": "读取 config_group='market_recommendation'；新增配置即可增加建议文案。"},
    {"group": "用户分群", "title": "分群饼图占比", "frontend": "用户分群 / segmentPie", "api": "/api/admin/market/segments", "table": "user_value_segment_daily", "fields": ["stat_date", "segment_code", "segment_name", "user_count"], "operation": "饼图占比=user_count/最新分群总人数；如果分群日报为空，接口会回退按 user_profile.value_level 实时分组。"},
    {"group": "设备运行", "title": "当前设备运行状态", "frontend": "设备管理 / runtime-status", "api": "/api/admin/operator/device/runtime-status", "table": "device", "fields": ["device_id", "online_status", "firmware_version", "last_active"], "operation": "基础信息来自 device；音量、电量、信号等运行值来自 Mongo runtime 文档，缺失时返回默认值。"},
    {"group": "设备运行", "title": "设备运行附加指标", "frontend": "设备详情 / 音量、电量、信号、网络", "api": "/api/admin/operator/device/runtime-status", "table": "MongoDB device_runtime", "fields": ["volume", "battery", "signal_strength", "current_network"], "operation": "修改 MongoDB 设备运行文档会影响详情运行指标；MySQL device 只保存基础设备信息。"},
    {"group": "设备运行", "title": "设备分组", "frontend": "设备分组 / groups", "api": "/api/admin/operator/device/groups", "table": "device", "fields": ["model_name", "online_status", "status", "firmware_version"], "operation": "按 model_name 聚合；onlineCount 使用统一在线口径，firmwareVersions 来自 device.firmware_version。"},
    {"group": "设备运行", "title": "告警中心", "frontend": "告警中心 / alerts", "api": "/api/admin/operator/device/alerts", "table": "device_log", "fields": ["log_type", "log_level", "title", "content", "created_at"], "operation": "优先读取 warning/error/alert 日志；同时从离线设备、失败固件任务、待处理反馈动态生成真实异常，不再只依赖日志表。"},
    {"group": "设备运行", "title": "离线设备告警来源", "frontend": "告警中心 / 设备离线", "api": "/api/admin/operator/device/alerts", "table": "device", "fields": ["device_id", "device_number", "device_name", "online_status", "status", "last_active"], "operation": "online_status=offline 或回退 status=0 会生成离线设备告警。"},
    {"group": "设备运行", "title": "固件失败告警来源", "frontend": "告警中心 / 固件失败", "api": "/api/admin/operator/device/alerts", "table": "device_firmware_update_task", "fields": ["task_no", "device_id", "target_version", "status", "fail_reason"], "operation": "status 为 failed/fail/error 或 fail_reason 不为空会生成固件失败告警。"},
    {"group": "设备日志", "title": "设备日志列表", "frontend": "设备日志 / logs", "api": "/api/admin/operator/device/logs", "table": "device_log", "fields": ["log_id", "log_level", "title", "content", "device_name", "online_status", "created_at"], "operation": "日志列表按 created_at/log_id 倒序；新增日志行会立即出现在运营日志页。"},
    {"group": "设备日志", "title": "设备日志详情", "frontend": "设备日志 / log-detail", "api": "/api/admin/operator/device/log-detail", "table": "device_log", "fields": ["log_id", "trace_id", "event_code", "title", "content", "ip_address", "network_type"], "operation": "点击日志读取同一行详情；修改 title/content/event_code 会影响详情展示。"},
    {"group": "反馈管理", "title": "反馈详情", "frontend": "用户反馈 / detail", "api": "/api/admin/operator/feedback/detail", "table": "user_feedback", "fields": ["feedback_no", "title", "content", "status", "star_rating", "reply_content", "handled_at"], "operation": "反馈详情来自 user_feedback 联表 user；status=open/pending 按待处理显示。"},
    {"group": "反馈管理", "title": "处理反馈", "frontend": "用户反馈 / 标记已处理", "api": "/api/admin/operator/feedback/handle", "table": "user_feedback", "fields": ["status", "handler_name", "reply_content", "handled_at"], "operation": "点击处理会把 status 更新为 processed，并写入处理人、回复和处理时间。"},
    {"group": "系统管理", "title": "管理员账号列表", "frontend": "用户管理 / users", "api": "/api/admin/super/users", "table": "admin_user", "fields": ["admin_id", "username", "role", "real_name", "job_no", "phone", "email", "status"], "operation": "系统管理员账号优先来自 admin_user；如果表为空则回退 DEFAULT_ADMINS。新增/修改账号会影响登录与用户管理列表。"},
    {"group": "系统管理", "title": "业务绑定用户预览", "frontend": "用户管理 / 绑定用户", "api": "/api/admin/super/users", "table": "user", "fields": ["user_id", "username", "nickname", "phone", "created_at", "last_login_at"], "operation": "用户管理页除管理员外还会预览少量业务用户，来自 user 联表 user_profile。"},
    {"group": "系统管理", "title": "角色权限矩阵", "frontend": "角色权限 / roles", "api": "/api/admin/super/roles", "table": "system_config", "fields": ["config_group", "config_key", "config_name", "description"], "operation": "角色权限可由 system_config 的 admin_role 配置覆盖；否则使用代码内默认角色目录。"},
    {"group": "系统管理", "title": "角色权限保存", "frontend": "角色权限 / 编辑权限", "api": "/api/admin/super/roles/permissions", "table": "system_config", "fields": ["config_group", "config_key", "description"], "operation": "保存权限会写入持久化 state 的 rolePermissions，不直接改前端菜单代码。"},
    {"group": "系统管理", "title": "系统配置", "frontend": "系统配置 / settings", "api": "/api/admin/super/system/config", "table": "system_config", "fields": ["config_key", "config_value", "config_type", "config_group", "config_name", "description"], "operation": "系统名称、主题、上传限制、接口超时、数据保留等来自 system_config；缺失时用后端默认值。"},
    {"group": "系统监控", "title": "系统监控指标", "frontend": "系统监控 / metrics", "api": "/api/admin/super/monitor", "table": "user,device,user_feedback", "targetTable": "user", "relatedTables": ["device", "user_feedback"], "fields": ["user_id", "device_id", "online_status", "status", "feedback_id"], "targetFields": ["user_id", "status", "created_at"], "operation": "totalUsers 来自 user，totalDevices/onlineDevices 来自 device，feedbackTotal 来自 user_feedback。"},
    {"group": "系统监控", "title": "最近异常", "frontend": "系统监控 / exceptions", "api": "/api/admin/super/monitor", "table": "system_config", "fields": ["config_group", "config_key", "config_name", "config_type", "description"], "operation": "优先读取 monitor_exception 配置；为空时后端从离线设备、待处理反馈、失败固件任务动态生成异常。"},
    {"group": "系统公告", "title": "公告列表", "frontend": "系统公告 / notices", "api": "/api/admin/super/notices", "table": "system_config", "fields": ["config_group", "config_key", "config_value", "config_type", "config_name", "description"], "operation": "公告来自 notice/notices/system_notice 配置组或 notice.* key；新增公告会新增 system_config 行。"},
    {"group": "审计日志", "title": "后台操作审计", "frontend": "审计日志 / audit", "api": "/api/admin/super/security/logs", "table": "admin_operation_log", "fields": ["admin_id", "action", "module", "operation_name", "path", "request_method", "result_status", "error_message", "created_at"], "operation": "审计日志只展示有管理意义的操作：登录、解绑设备、发布固件、处理反馈、修改权限、发布公告；记录谁、时间、操作、对象、结果、IP。"},
    {"group": "账户信息", "title": "当前登录账号资料", "frontend": "个人信息 / account", "api": "/api/admin/profile", "table": "admin_user", "fields": ["username", "role", "real_name", "job_no", "position", "phone", "email", "wechat_open_id"], "operation": "登录 token 解析当前账号；资料来自 admin_user 或 DEFAULT_ADMINS 回退。"},
    {"group": "账户信息", "title": "修改个人密码", "frontend": "个人信息 / password", "api": "/api/admin/password", "table": "admin_user", "fields": ["username", "password_hash", "updated_at"], "operation": "四种后台角色均可修改自己的密码；数据库账号更新 admin_user.password_hash，默认账号写入后台账号覆盖层。"},
    {"group": "模拟原始数据", "title": "中文模拟用户与画像", "frontend": "后端每日自动任务", "api": "/api/db/daily-stats/run", "table": "user,user_profile,auth_token", "targetTable": "user_profile", "relatedTables": ["user", "auth_token"], "fields": ["username", "nickname", "age", "age_range", "province_name", "active_level", "value_level", "bound_platforms", "platform_type"], "targetFields": ["user_id", "nickname", "age", "age_range", "province_name", "active_level", "value_level", "bound_platforms"], "operation": "每日自动任务写入中文用户名、自然昵称、地区、年龄、活跃/价值等级；绑定平台只写网易云音乐或 QQ音乐。"},
    {"group": "模拟原始数据", "title": "中文模拟设备与绑定", "frontend": "后端每日自动任务", "api": "/api/db/daily-stats/run", "table": "device,user_device_binding", "targetTable": "user_device_binding", "relatedTables": ["device"], "fields": ["device_number", "model_name", "online_status", "firmware_version", "custom_device_name", "default_room", "bind_time"], "targetFields": ["user_id", "device_id", "custom_device_name", "default_room", "current_network", "bind_time"], "operation": "每日自动任务同步 status 与 online_status，并写用户设备绑定关系、房间和真实风格 Wi-Fi。"},
    {"group": "模拟原始数据", "title": "中文模拟订单", "frontend": "后端每日自动任务", "api": "/api/db/daily-stats/run", "table": "sales_order", "fields": ["order_no", "user_id", "device_id", "pay_amount", "pay_status", "province_name", "created_at"], "operation": "模拟订单 pay_status=paid，会进入销售额、订单数、区域销售、购买留存分母。"},
    {"group": "模拟原始数据", "title": "中文模拟歌曲与播放", "frontend": "后端每日自动任务", "api": "/api/db/daily-stats/run", "table": "media_mapping,play_history", "targetTable": "play_history", "relatedTables": ["media_mapping"], "fields": ["song_title", "artist", "platform", "external_id", "play_duration", "source_platform", "created_at"], "targetFields": ["device_id", "user_id", "mapping_id", "play_duration", "source_platform", "created_at"], "operation": "播放记录是热歌、播放总量、活跃用户、留存分子的原始来源；改完明细后运行每日汇总重算。"},
    {"group": "汇总计算数据", "title": "日报主表计算结果", "frontend": "趋势/决策/报表", "api": "/api/db/daily-stats/run", "table": "daily_stats", "fields": ["total_play_count", "unique_user_count", "unique_device_count", "online_device_count", "new_user_count", "new_device_count", "total_sales_amount"], "operation": "daily_stats 是计算结果，不是原始数据；改原始 user/device/sales_order/play_history 后运行每日汇总重算。"},
    {"group": "汇总计算数据", "title": "地区/热歌/分群/活跃日报", "frontend": "地区热力、热歌排行、用户分群", "api": "/api/db/daily-stats/run", "table": "region_stats_daily,hot_ranking_daily,user_value_segment_daily,user_activity_daily,analytics_metric_daily", "targetTable": "region_stats_daily", "relatedTables": ["hot_ranking_daily", "user_value_segment_daily", "user_activity_daily", "analytics_metric_daily"], "fields": ["stat_date", "ranking_date", "metric_date", "metric_value", "user_count", "sales_amount"], "targetFields": ["stat_date", "region_name", "user_count", "active_user_count", "order_count", "sales_amount"], "operation": "这些表都由每日汇总从原始明细计算；需要改口径时改 daily_stats_job.py，维护表值只影响当前展示。"},
])

FRONT_DATA_CATALOG.extend([
    {"group": "设备绑定与解绑", "title": "设备是否真的解绑", "frontend": "设备管理 / 解绑设备、绑定用户详情", "api": "/api/admin/operator/device/unbind；/api/admin/operator/device/bound-user", "table": "user_device_binding", "targetTable": "user_device_binding", "relatedTables": ["user", "user_profile", "device"], "fields": ["user_id", "device_id", "custom_device_name", "default_room", "current_network", "bind_time"], "operation": "解绑只删除 user_device_binding 的用户-设备关系，不删除 device 设备本体；解绑成功后对应 device_id 的绑定行不存在，但设备列表仍有该设备。"},
    {"group": "设备绑定与解绑", "title": "绑定用户资料来源", "frontend": "设备详情 / 当前绑定用户", "api": "/api/admin/operator/device/bound-user", "table": "user_device_binding", "targetTable": "user_device_binding", "relatedTables": ["user", "user_profile", "device"], "fields": ["user_id", "device_id", "bind_time"], "operation": "绑定关系在 user_device_binding；用户昵称、电话、地区、活跃/价值等级分别来自 user 和 user_profile；设备名来自 device。"},
    {"group": "设备绑定与解绑", "title": "设备基础信息与归属", "frontend": "设备管理 / 设备列表", "api": "/api/admin/operator/device/list；/api/admin/operator/device/detail", "table": "device", "targetTable": "device", "relatedTables": ["user_device_binding"], "fields": ["device_id", "device_number", "device_name", "model_name", "online_status", "firmware_version"], "operation": "设备本体在 device；如果只删除 user_device_binding，设备仍存在，但绑定用户会消失。要删除设备本体才维护 device。"},
    {"group": "MongoDB 运行态", "title": "设备实时状态", "frontend": "设备详情 / 音量、电量、信号、网络", "api": "/api/admin/operator/device/runtime-status", "table": "device_runtime", "source": "mongo", "collection": "device_runtime", "fields": ["device_id", "deviceId", "battery", "volume", "signalStrength", "networkType"], "operation": "运行态不是 MySQL；去 MongoDB 的 device_runtime 集合维护，device_id/deviceId 要能对应 MySQL device.device_id。"},
    {"group": "MongoDB 运行态", "title": "播放器当前状态", "frontend": "播放状态、当前歌曲、播放进度", "api": "MongoDB runtime 读取", "table": "player_state", "source": "mongo", "collection": "player_state", "fields": ["device_id", "deviceId", "isPlaying", "songId", "songName", "artist", "playTime"], "operation": "当前播放态在 MongoDB player_state；它影响当前歌曲、播放/暂停状态和播放进度。"},
    {"group": "MongoDB 运行态", "title": "播放队列", "frontend": "下一首、播放队列", "api": "MongoDB runtime 读取", "table": "play_queue", "source": "mongo", "collection": "play_queue", "fields": ["device_id", "deviceId", "queue"], "operation": "队列数据在 MongoDB play_queue；queue 里每首歌要包含 songId/songName/artist 等前端可读字段。"},
    {"group": "MongoDB 运行态", "title": "运行操作日志", "frontend": "运行态操作记录", "api": "MongoDB operation_logs", "table": "operation_logs", "source": "mongo", "collection": "operation_logs", "fields": ["requestId", "device_id", "action", "result", "created_at"], "operation": "设备运行过程中的临时操作记录在 MongoDB operation_logs；后台审计日志仍在 MySQL admin_operation_log。"},
    {"group": "MongoDB 运行态", "title": "歌曲元数据缓存", "frontend": "歌曲封面、歌手、时长缓存", "api": "MongoDB media_metadata", "table": "media_metadata", "source": "mongo", "collection": "media_metadata", "fields": ["song_id", "external_id", "name", "artist", "cover_url", "duration"], "operation": "歌曲缓存数据在 MongoDB media_metadata；正式热歌排行仍主要看 MySQL media_mapping、play_history、hot_ranking_daily。"},
    {"group": "系统账号与权限", "title": "管理员和老板账号", "frontend": "用户管理 / 管理员与绑定用户", "api": "/api/admin/super/users", "table": "admin_user", "targetTable": "admin_user", "fields": ["admin_id", "username", "password_hash", "role", "status", "real_name", "job_no", "phone", "email", "last_login_at"], "operation": "用户管理页现在只显示管理员和老板账号；账号资料来自 admin_user，默认账号来自代码兜底，不再混入普通业务用户。"},
    {"group": "系统账号与权限", "title": "超级管理员权限必须全选", "frontend": "角色权限矩阵 / 超级管理员", "api": "/api/admin/super/roles", "table": "system_config", "targetTable": "system_config", "fields": ["config_group", "config_key", "config_name", "description"], "operation": "角色权限保存覆盖在 system_config 或后台 state；但 super_admin 后端强制返回权限目录全集，旧配置不能裁剪超级管理员。"},
    {"group": "系统账号与权限", "title": "后台登录与最近登录", "frontend": "登录页、个人信息、用户管理最近登录", "api": "/api/admin/login；/api/admin/profile", "table": "admin_user", "targetTable": "admin_user", "fields": ["username", "password_hash", "last_login_at", "status"], "operation": "登录成功会更新 admin_user.last_login_at；默认账号没有数据库行时，会从后端默认管理员配置回显。"},
    {"group": "公告与审计", "title": "系统公告创建结果", "frontend": "系统公告 / 新建公告", "api": "/api/admin/super/notices", "table": "system_config", "targetTable": "system_config", "fields": ["config_key", "config_value", "config_type", "config_group", "config_name", "description", "created_at", "updated_at"], "operation": "公告写在 system_config，config_group 为 notice/notices/system_notice 或 config_key 以 notice. 开头；创建后应该能在这里查到新行。"},
    {"group": "公告与审计", "title": "审计与安全日志", "frontend": "审计日志 / 操作日志、登录日志、安全事件", "api": "/api/admin/super/security/logs", "table": "admin_operation_log", "targetTable": "admin_operation_log", "fields": ["log_id", "admin_id", "action", "module", "operation_name", "path", "request_method", "ip_address", "result_status", "error_message", "created_at"], "operation": "真实后台操作写入 admin_operation_log；谁、什么时候、做了什么、对象、结果和 IP 都应能在这张表维护或核验。"},
    {"group": "反馈与公告", "title": "用户反馈处理结果", "frontend": "用户反馈 / 处理反馈", "api": "/api/admin/operator/feedback/handle", "table": "user_feedback", "targetTable": "user_feedback", "fields": ["feedback_id", "feedback_no", "status", "handler_name", "reply_content", "handled_at", "closed_at"], "operation": "处理反馈会修改 user_feedback.status、handler_name、reply_content、handled_at；如果前端状态不对就查这些字段。"},
    {"group": "播放与趋势", "title": "每日播放次数趋势", "frontend": "趋势分析 / 每日播放次数趋势", "api": "/api/admin/super/trend/growth?type=play", "table": "daily_stats", "targetTable": "daily_stats", "relatedTables": ["play_history"], "fields": ["stat_date", "total_play_count", "total_play_duration_seconds", "unique_user_count", "unique_device_count"], "operation": "趋势图读 daily_stats.total_play_count；原始播放明细在 play_history，改原始明细后需要运行每日汇总。"},
    {"group": "播放与趋势", "title": "播放原始明细", "frontend": "播放趋势、热歌、留存分子", "api": "/api/db/daily-stats/run", "table": "play_history", "targetTable": "play_history", "relatedTables": ["media_mapping", "daily_stats", "hot_ranking_daily"], "fields": ["history_id", "user_id", "device_id", "mapping_id", "play_duration", "source_platform", "created_at", "style"], "operation": "play_history 是播放次数、播放时长、活跃用户、留存分子的原始来源；删除这里的明细后要补跑 daily_stats。"},
    {"group": "播放与趋势", "title": "歌曲映射与平台", "frontend": "热歌排行 / 平台来源", "api": "/api/admin/market/top-songs", "table": "media_mapping", "targetTable": "media_mapping", "relatedTables": ["play_history", "hot_ranking_daily"], "fields": ["mapping_id", "song_title", "artist", "platform", "external_id", "cover_url"], "operation": "歌曲名称、歌手、平台映射来自 media_mapping；播放记录 source_platform 和映射 platform 会共同影响热歌展示。"},
    {"group": "关系与社交", "title": "好友关系", "frontend": "小程序好友关系、社交数据", "api": "/api/db/friendship/detail", "table": "friendship", "targetTable": "friendship", "fields": ["user_id_1", "user_id_2"], "operation": "friendship 是联合主键表；维护页现在会使用 detail 接口删除 user_id_1 + user_id_2 对应关系。"},
])


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
    if table_key == "device" and "online_status" in normalized:
        online_text = str(normalized.get("online_status") or "").strip().lower()
        if online_text in {"online", "true", "1", "yes", "在线"}:
            normalized["online_status"] = "online"
            normalized["status"] = 1
        elif online_text in {"offline", "false", "0", "no", "离线"}:
            normalized["online_status"] = "offline"
            normalized["status"] = 0
        else:
            normalized["online_status"] = str(normalized.get("online_status") or "").strip()
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
    return datetime.now().strftime("%m%d%H%M%S") + f"{uuid.uuid4().int % 100000000:08d}"


SAMPLE_SURNAMES = [
    "林", "陈", "周", "苏", "顾", "许", "沈", "陆", "赵", "唐", "宋", "何",
    "韩", "梁", "程", "孟", "秦", "夏", "叶", "方", "罗", "白", "魏", "姜",
]
SAMPLE_GIVEN_NAMES = [
    "清和", "知远", "安宁", "沐阳", "思语", "景行", "若溪", "星河", "云舒", "予安",
    "听澜", "书白", "南风", "嘉树", "初夏", "青禾", "明川", "以宁", "念真", "晚晴",
]
SAMPLE_NICK_PREFIXES = [
    "晨光", "晚风", "星河", "南山", "海盐", "青柠", "云朵", "月白", "竹影", "晴川",
]
SAMPLE_NICK_SUFFIXES = [
    "电台", "歌单", "随身听", "音乐盒", "唱片架", "点歌台", "小屋", "频道",
]


def sample_index(suffix, offset=0):
    try:
        return int("".join(ch for ch in str(suffix) if ch.isdigit())[-8:]) + offset
    except ValueError:
        return int(time.time() * 1000) + offset


def natural_user_fields(suffix):
    index = sample_index(suffix)
    surname = SAMPLE_SURNAMES[index % len(SAMPLE_SURNAMES)]
    given = SAMPLE_GIVEN_NAMES[(index // len(SAMPLE_SURNAMES)) % len(SAMPLE_GIVEN_NAMES)]
    username = f"{surname}{given}"
    prefix = SAMPLE_NICK_PREFIXES[index % len(SAMPLE_NICK_PREFIXES)]
    suffix_word = SAMPLE_NICK_SUFFIXES[(index // 3) % len(SAMPLE_NICK_SUFFIXES)]
    nickname_options = [
        f"{given[-1]}的{suffix_word}",
        f"{given}{suffix_word}",
        f"{prefix}{given[-1]}",
        f"{given[-1]}在听歌",
        f"{prefix}{suffix_word}",
    ]
    nickname = nickname_options[(index // 7) % len(nickname_options)]
    if nickname == username:
        nickname = f"{given[-1]}的歌单"
    return username, nickname


def ensure_unique_user_sample(cursor, sample):
    if not sample.get("username"):
        return sample
    for attempt in range(12):
        cursor.execute("SELECT 1 FROM `user` WHERE username=%s LIMIT 1", (sample["username"],))
        if not cursor.fetchone():
            return sample
        username, nickname = natural_user_fields(f"{unique_sample_suffix()}{attempt}")
        sample["username"] = username
        sample["nickname"] = nickname
        sample["email"] = f"user{unique_sample_suffix()}@smart-speaker.local"
    return sample


def uniquify_sample_record(table_key, data):
    sample = dict(data or {})
    suffix = unique_sample_suffix()
    for field in UNIQUE_SAMPLE_FIELDS.get(table_key, []):
        value = sample.get(field)
        if value in (None, ""):
            continue
        text = str(value)
        if table_key == "device" and field == "device_number":
            parts = text.split("-")
            if len(parts) >= 3 and parts[-1].isdigit():
                sample[field] = "-".join(parts[:-1] + [suffix[-4:]])
            else:
                sample[field] = f"{text}-{suffix[-4:]}"[:250]
        elif field == "email" and "@" in text:
            name, domain = text.split("@", 1)
            sample[field] = f"{name}+{suffix}@{domain}"
        elif field == "phone":
            sample[field] = f"139{suffix[-8:]}"[:11]
        else:
            sample[field] = f"{text}-{suffix}"[:250]
    if table_key == "user":
        username, nickname = natural_user_fields(suffix)
        sample["username"] = username
        sample["nickname"] = nickname
        sample["password_hash"] = "123456"
        sample["status"] = sample.get("status") or "active"
        if sample.get("email"):
            sample["email"] = f"user{suffix}@smart-speaker.local"
    if table_key == "user_profile":
        _, nickname = natural_user_fields(suffix)
        sample["nickname"] = nickname
        sample["user_status"] = sample.get("user_status") or "active"
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
    data["scope_type"] = data.get("scope_type") or "platform"
    data["scope_code"] = data.get("scope_code") or "网易云音乐"
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
            online_device_count = scalar_value(cursor, f"SELECT COUNT(*) AS c FROM device WHERE {ONLINE_DEVICE_CONDITION}")
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
            for table_name in [
                "auth_token",
                "user_device_binding",
                "admin_user",
                "system_config",
                "admin_operation_log",
                "region_stats_daily",
                "user_activity_daily",
                "user_value_segment_daily",
                "analytics_metric_daily",
                "device_firmware",
                "device_firmware_release",
                "device_firmware_update_task",
                "friendship",
            ]:
                snapshot.setdefault(
                    table_name,
                    f"{int(scalar_value(cursor, f'SELECT COUNT(*) AS c FROM {quote_identifier(table_name)}') or 0)} 条记录",
                )
            cursor.execute(
                """
                SELECT stat_date, total_play_count, unique_user_count, unique_device_count,
                       total_sales_amount
                FROM daily_stats
                ORDER BY stat_date DESC
                LIMIT 1
                """
            )
            latest_daily = cursor.fetchone() or {}
            if latest_daily:
                snapshot["daily_stats"] = (
                    f"{latest_daily.get('stat_date')}：播放 {int(latest_daily.get('total_play_count') or 0)} 次，"
                    f"活跃用户 {int(latest_daily.get('unique_user_count') or 0)}，"
                    f"活跃设备 {int(latest_daily.get('unique_device_count') or 0)}，"
                    f"销售额 {float(latest_daily.get('total_sales_amount') or 0):.2f}"
                )
        try:
            db = mongo_db()
            if db is not None:
                for collection_name in [
                    "device_runtime",
                    "player_state",
                    "play_queue",
                    "operation_logs",
                    "media_metadata",
                    "song_info",
                    "play_logs",
                ]:
                    if collection_name in db.list_collection_names():
                        snapshot[collection_name] = f"{db[collection_name].count_documents({})} 个文档"
        except Exception:
            pass
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
            target = copy.get("collection") or copy.get("targetTable") or table
            first_table = str(target or "").split(",")[0].strip()
            copy["current"] = snapshot.get(first_table) or snapshot.get(table) or snapshot.get("error") or "暂无当前值"
        enriched.append(copy)
    return enriched


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

    keyword = str(request.args.get("q") or "").strip()
    if keyword:
        keyword_parts = [
            f"CAST({quote_identifier(column)} AS CHAR) LIKE %s"
            for column in columns
        ]
        where_parts.append("(" + " OR ".join(keyword_parts) + ")")
        params.extend([f"%{keyword}%"] * len(columns))

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
            if table_key == "user":
                data = ensure_unique_user_sample(cursor, data)
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
