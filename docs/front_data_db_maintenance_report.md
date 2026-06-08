# 前端数据数据库维护报告

更新时间：2026-06-08

## 维护入口

- 打开 `/db-admin` 或 `/api/db-admin`。
- 页面顶部是“前端数据维护目录”。
- 搜索要改的数字，例如“年龄占比”“销售额”“热歌播放量”。
- 点击“去维护”后会跳转到对应 MySQL 表，并把建议修改的字段高亮。
- 修改基础业务表后，点击“运行每日汇总”，会刷新 `daily_stats`、`region_stats_daily`、`hot_ranking_daily`、`user_activity_daily`、`user_value_segment_daily`、`analytics_metric_daily`。

## 前端数字与数据库操作

| 前端数据 | 数据表 | 字段 | 增加或减少方式 |
| --- | --- | --- | --- |
| 总用户 | `user` | `user_id`, `created_at`, `status` | 新增用户行会增加总数；删除用户行会减少总数。 |
| 今日新增用户 | `user` | `created_at` | 把 `created_at` 改成今天会增加今日新增；改成历史日期会减少今日新增。 |
| 设备数 / 在线率 | `device` | `device_id`, `status`, `online_status` | 新增设备行增加设备数；`status=1` 增加在线数，`status=0` 减少在线数。 |
| 销售额 / 订单数 | `sales_order` | `pay_amount`, `pay_status` | `pay_status` 为 `paid/success/finished` 才统计；调高 `pay_amount` 增加销售额，改成 `pending/closed` 减少统计。 |
| 活跃度 / 活跃用户 | `user_profile` | `active_level` | `active_level='high'` 增加活跃用户；改成 `medium/low` 减少。 |
| 用户/设备/销售趋势 | `daily_stats` | `new_user_count`, `new_device_count`, `total_sales_amount` | 按 `stat_date` 找日期行，直接修改对应字段。 |
| 地区销售热力 | `region_stats_daily` | `region_name`, `sales_amount`, `order_count` | 修改最新 `stat_date` 下地区行；新增地区需新增唯一 `region_code`。 |
| 地区用户热力 | `region_stats_daily` | `user_count`, `active_user_count` | 修改最新 `stat_date` 下地区行，数值越大条形越长。 |
| 年龄占比 | `user_profile` | `age`, `age_range` | 占比由 `age_range` 分组计数决定；想提高某年龄段占比，就把更多画像改成该 `age_range`。 |
| 用户地区占比 | `user_profile` | `province_name`, `city_name` | 占比由 `province_name` 分组计数决定。 |
| 活跃分层占比 | `user_profile` | `active_level` | 按 `high/medium/low` 分组计数。 |
| 绑定软件占比 | `user_profile` | `bound_platforms` | 按 `qq/netease/wechat` 等值分组计数。 |
| 普通用户 / 高活用户环图 | `user_profile` | `active_level`, `value_level` | 高活用户是 `active_level='high'`；普通用户是总画像数减高活用户数。 |
| 用户分群人数 / 留存 / 均值 | `user_value_segment_daily` | `user_count`, `active_user_count`, `avg_play_count`, `avg_pay_amount`, `retention_rate` | 修改最新 `stat_date` 的分群行；新增分群需唯一 `segment_code`。 |
| 热歌排行 / 播放量 | `hot_ranking_daily` | `ranking_date`, `rank_no`, `target_name`, `target_category`, `metric_value` | 修改最新 `ranking_date` 且 `ranking_type='song'` 的排行行。 |
| 购买后 1/7/30 日留存 | `sales_order`, `play_history` | `user_id`, `created_at`, `pay_status` | 已支付订单决定购买人数；购买后有播放记录会提高留存人数。 |
| 反馈总数 / 待处理数 / 评分 | `user_feedback` | `feedback_type`, `status`, `priority`, `star_rating` | 新增反馈增加总数；`pending/open` 增加待处理，`processed/closed` 减少待处理。 |
| 设备列表 / 固件版本 / 在线状态 | `device` | `device_number`, `model_name`, `status`, `firmware_version` | 新增设备行增加列表；修改 `firmware_version` 改前端版本展示。 |
| 设备所属用户 / 房间 | `user_device_binding` | `user_id`, `device_id`, `custom_device_name`, `default_room` | 新增/修改绑定关系会改变设备详情中的用户、别名和房间。 |
| 设备日志数量 / 内容 | `device_log` | `log_type`, `log_level`, `title`, `content` | 新增日志行增加列表；修改内容字段改变展示。 |
| 播放历史 / 播放次数 | `play_history` | `device_id`, `user_id`, `mapping_id`, `play_duration`, `created_at` | 新增播放记录会增加播放历史；每日汇总后影响热歌和日报统计。 |
| 歌曲标题 / 歌手 / 平台 | `media_mapping` | `song_title`, `artist`, `platform`, `external_id`, `cover_url` | `play_history.mapping_id` 关联这里，修改后会影响歌曲展示。 |
| 每日汇总时间 | `daily_stats` | `generated_at`, `updated_at` | 点击维护页“运行每日汇总”会写入真实当前时间。 |

## 本次验证

- `python -m py_compile daily_stats_job.py db_api_service.py admin_routes.py app.py`：通过。
- `npm run build`：通过，仅有依赖包 annotation 和 chunk size 警告。
- `/api/db/front-data-catalog` Flask 测试客户端：通过，返回 24 个维护项。
- 实际刷新远程数据库：未完成，本机直连 `8.137.165.220` 的 MySQL 在握手阶段连续断开，错误为 `(2013, 'Lost connection to MySQL server during query')`；MongoDB 直连也出现 `connection closed`。代码已改为纯日报刷新不依赖 Mongo，并给 MySQL 连接加了三次重试。
