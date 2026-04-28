# 数据库接口开发说明

## 1. 开发目标

本模块用于完成课程任务中的第四项：

> 实现 Flask 的接口开发，完成对 MySQL 数据库表中的增删改查操作。

本次开发是在原有智能音箱项目基础上新增数据库接口能力。原项目已有 HTTPS 网关、RabbitMQ、worker 等模块，本次没有破坏原有设备数据上报流程，而是在 Flask 主应用中新增 `/api/db/...` 数据库接口模块，用于操作 MySQL 中的业务表。

---

## 2. 当前实际部署方式

数据库接口已经集成到原 Flask Gateway 中，由 Docker Compose 中的 `gateway` 服务运行。

访问方式：

```text
https://服务器IP/api/db/...
```

本地服务器测试方式：

```bash
curl -k https://127.0.0.1/api/db/health
```

说明：

- 接口通过 HTTPS 访问。
- Flask 应用运行在 gateway 容器中。
- 数据库连接信息通过 `.env.db_api` 注入 gateway 容器。
- `.env.db_api.example` 只作为模板文件提交到 GitHub，不保存真实密码。

---

## 3. 相关文件说明

### 3.1 `app.py`

原项目的 Flask 主应用。

本次新增数据库接口时，在 `app.py` 中注册数据库接口模块：

```python
from db_api_service import db_api
app.register_blueprint(db_api)
```

作用：

- 保留原有 `/api/bass`、`/api/signal`、`/api/volume` 等接口。
- 新增 `/api/db/...` MySQL CRUD 接口。
- 让数据库接口和原 HTTPS 网关共用同一个 Flask 应用。

---

### 3.2 `db_api_service.py`

数据库接口核心文件。

作用：

- 定义 `/api/db/...` 路由。
- 根据请求路径判断要操作哪张表。
- 根据请求方法执行查询、新增、修改、删除。
- 调用 `db_config.py` 获取 MySQL 连接。
- 返回统一 JSON 格式结果。

---

### 3.3 `db_config.py`

MySQL 连接配置文件。

作用：

- 从环境变量中读取 MySQL 配置。
- 创建 MySQL 数据库连接。
- 供 `db_api_service.py` 调用。

需要的环境变量：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=smart_speaker
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
```

---

### 3.4 `.env.db_api.example`

数据库配置模板文件，可以提交到 GitHub。

示例：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=smart_speaker
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
```

注意：

```text
.env.db_api.example 可以上传 GitHub
.env.db_api 不要上传 GitHub
```

---

### 3.5 `.env.db_api`

服务器真实运行配置文件。

该文件只保存在服务器中，不提交到 GitHub。

示例：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=smart_speaker
MYSQL_USER=root
MYSQL_PASSWORD=真实密码
```

---

### 3.6 `docker-compose.yml`

用于管理 gateway、rabbitmq、worker 等容器服务。

本次新增数据库接口后，`gateway` 服务需要读取 `.env.db_api`：

```yaml
gateway:
  build:
    context: .
    dockerfile: Dockerfile.gateway
  network_mode: host
  env_file:
    - .env.db_api
```

这样 gateway 容器中的 Flask 接口才能读取 MySQL 配置。

---

## 4. 当前 MySQL 数据库表

数据库名：

```text
smart_speaker
```

当前接口严格按照实际存在的 MySQL 表进行配置，不额外创建不存在的表。

支持的业务表如下：

| 表名 | 主键 | 说明 |
|---|---|---|
| `user` | `user_id` | 用户表 |
| `device` | `device_id` | 设备表 |
| `auth_token` | `auth_id` | 第三方平台授权令牌表 |
| `media_mapping` | `mapping_id` | 歌曲映射表 |
| `action_dict` | `action_id` | 操作字典表 |
| `play_history` | `history_id` | 播放历史表 |
| `friendship` | `user_id_1 + user_id_2` | 用户好友关系表 |
| `user_device_binding` | `user_id + device_id` | 用户设备绑定表 |
| `user_feedback` | `feedback_id` | 用户反馈表 |
| `Daily_Stats` | `stat_date` | 每日统计表 |

说明：

- 当前真实数据库中没有 `operation_log` 表，因此接口不提供 `/api/db/operation_log`。
- `Daily_Stats` 表中的热门歌曲字段为 `hottest_song_id`，不是 `hottest_song_external_id`。
- `friendship` 和 `user_device_binding` 是联合主键表，需要使用专门的 `detail` 接口进行单条查询、修改或删除。
- `action_dict.action_id` 不是自增字段，新增时需要手动传入 `action_id`。

---

## 5. 统一返回格式

### 5.1 成功响应

```json
{
  "status": "success",
  "message": "success",
  "data": {}
}
```

### 5.2 失败响应

```json
{
  "status": "error",
  "message": "错误信息"
}
```

---

## 6. 接口列表

接口统一前缀：

```text
/api/db
```

---

### 6.1 健康检查

请求：

```text
GET /api/db/health
```

作用：检查 Flask 接口是否能正常连接 MySQL。

测试命令：

```bash
curl -k https://127.0.0.1/api/db/health
```

成功示例：

```json
{
  "data": {
    "mysql": "connected",
    "result": {
      "ok": 1
    }
  },
  "message": "success",
  "status": "success"
}
```

---

### 6.2 查看接口支持的表

请求：

```text
GET /api/db/tables
```

测试命令：

```bash
curl -k https://127.0.0.1/api/db/tables
```

返回示例：

```json
{
  "status": "success",
  "message": "success",
  "data": [
    "user",
    "device",
    "auth_token",
    "media_mapping",
    "action_dict",
    "play_history",
    "friendship",
    "user_device_binding",
    "user_feedback",
    "Daily_Stats"
  ]
}
```

---

## 7. 单主键表通用 CRUD 接口

适用于以下表：

```text
user
device
auth_token
media_mapping
action_dict
play_history
user_feedback
Daily_Stats
```

### 7.1 查询列表

请求格式：

```text
GET /api/db/<table_name>
```

示例：

```bash
curl -k https://127.0.0.1/api/db/device
```

支持按字段过滤，例如：

```bash
curl -k "https://127.0.0.1/api/db/device?device_number=dev_01"
```

支持分页参数：

```text
limit   每次返回条数，默认 100，最大 500
offset  偏移量，默认 0
```

分页示例：

```bash
curl -k "https://127.0.0.1/api/db/play_history?limit=10&offset=0"
```

---

### 7.2 查询单条记录

请求格式：

```text
GET /api/db/<table_name>/<primary_key_value>
```

查询 `device_id = 1` 的设备：

```bash
curl -k https://127.0.0.1/api/db/device/1
```

查询 `user_id = 1` 的用户：

```bash
curl -k https://127.0.0.1/api/db/user/1
```

查询某天的每日统计：

```bash
curl -k https://127.0.0.1/api/db/Daily_Stats/2026-04-29
```

---

### 7.3 新增记录

请求格式：

```text
POST /api/db/<table_name>
```

新增设备：

```bash
curl -k -X POST https://127.0.0.1/api/db/device \
  -H "Content-Type: application/json" \
  -d '{
    "device_number": "dev_test",
    "model_name": "test-speaker",
    "status": 1,
    "last_active": "2026-04-29 01:40:00"
  }'
```

新增用户：

```bash
curl -k -X POST https://127.0.0.1/api/db/user \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user@smart-speaker.local",
    "password_hash": "test_hash",
    "phone": "13800000000",
    "created_at": "2026-04-29 01:40:00"
  }'
```

新增每日统计：

```bash
curl -k -X POST https://127.0.0.1/api/db/Daily_Stats \
  -H "Content-Type: application/json" \
  -d '{
    "stat_date": "2026-04-29",
    "total_play_count": 10,
    "unique_song_count": 3,
    "unique_user_count": 2,
    "unique_device_count": 2,
    "total_play_duration_seconds": 1200,
    "avg_play_duration_seconds": 120.00,
    "hottest_song_id": "2651425710",
    "hottest_song_name": "稻香",
    "hottest_artist": "Lucky小爱",
    "hottest_play_count": 5,
    "generated_at": "2026-04-29 02:00:00",
    "updated_at": "2026-04-29 02:00:00"
  }'
```

---

### 7.4 修改记录

请求格式：

```text
PUT /api/db/<table_name>/<primary_key_value>
```

修改设备：

```bash
curl -k -X PUT https://127.0.0.1/api/db/device/1 \
  -H "Content-Type: application/json" \
  -d '{
    "device_number": "dev_01",
    "model_name": "smart-speaker-updated",
    "status": 1,
    "last_active": "2026-04-29 01:45:00"
  }'
```

修改用户反馈：

```bash
curl -k -X PUT https://127.0.0.1/api/db/user_feedback/1 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "content": "like_status=True; device_number=dev_01"
  }'
```

修改每日统计：

```bash
curl -k -X PUT https://127.0.0.1/api/db/Daily_Stats/2026-04-29 \
  -H "Content-Type: application/json" \
  -d '{
    "total_play_count": 12,
    "unique_song_count": 4,
    "unique_user_count": 2,
    "unique_device_count": 2,
    "total_play_duration_seconds": 1440,
    "avg_play_duration_seconds": 120.00,
    "hottest_song_id": "2651425710",
    "hottest_song_name": "稻香",
    "hottest_artist": "Lucky小爱",
    "hottest_play_count": 6,
    "generated_at": "2026-04-29 02:00:00",
    "updated_at": "2026-04-29 02:10:00"
  }'
```

---

### 7.5 删除记录

请求格式：

```text
DELETE /api/db/<table_name>/<primary_key_value>
```

删除设备：

```bash
curl -k -X DELETE https://127.0.0.1/api/db/device/1
```

删除每日统计：

```bash
curl -k -X DELETE https://127.0.0.1/api/db/Daily_Stats/2026-04-29
```

---

## 8. 联合主键表接口

联合主键表不能直接使用 `/api/db/<table>/<id>` 形式定位单条记录，需要通过查询参数传入多个主键。

### 8.1 `friendship` 表

主键：

```text
user_id_1
user_id_2
```

查询列表：

```bash
curl -k https://127.0.0.1/api/db/friendship
```

新增好友关系：

```bash
curl -k -X POST https://127.0.0.1/api/db/friendship \
  -H "Content-Type: application/json" \
  -d '{
    "user_id_1": 1,
    "user_id_2": 2
  }'
```

查询单条好友关系：

```bash
curl -k "https://127.0.0.1/api/db/friendship/detail?user_id_1=1&user_id_2=2"
```

说明：`friendship` 表只有两个主键字段，没有其他可修改字段。如果需要变更好友关系，应先删除再新增。

删除好友关系：

```bash
curl -k -X DELETE "https://127.0.0.1/api/db/friendship/detail?user_id_1=1&user_id_2=2"
```

---

### 8.2 `user_device_binding` 表

主键：

```text
user_id
device_id
```

查询列表：

```bash
curl -k https://127.0.0.1/api/db/user_device_binding
```

新增绑定：

```bash
curl -k -X POST https://127.0.0.1/api/db/user_device_binding \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "device_id": 1,
    "custom_device_name": "客厅音箱",
    "is_primary": 1
  }'
```

查询单条绑定：

```bash
curl -k "https://127.0.0.1/api/db/user_device_binding/detail?user_id=1&device_id=1"
```

修改绑定：

```bash
curl -k -X PUT "https://127.0.0.1/api/db/user_device_binding/detail?user_id=1&device_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "custom_device_name": "卧室音箱",
    "is_primary": 0
  }'
```

删除绑定：

```bash
curl -k -X DELETE "https://127.0.0.1/api/db/user_device_binding/detail?user_id=1&device_id=1"
```

---

## 9. 各表字段说明

### 9.1 `user`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `user_id` | bigint, 主键, 自增 | 用户 ID |
| `username` | varchar(50) | 用户名 |
| `password_hash` | varchar(255) | 密码哈希 |
| `phone` | varchar(20) | 手机号 |
| `created_at` | datetime | 创建时间 |

### 9.2 `device`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `device_id` | bigint, 主键, 自增 | 设备 ID |
| `device_number` | varchar(64) | 设备编号 |
| `model_name` | varchar(50) | 设备型号 |
| `status` | tinyint | 设备状态 |
| `last_active` | datetime | 最近活跃时间 |

### 9.3 `auth_token`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `auth_id` | bigint, 主键, 自增 | 授权 ID |
| `user_id` | bigint | 用户 ID |
| `platform_type` | varchar(20) | 平台类型 |
| `access_token` | text | 访问令牌 |
| `refresh_token` | varchar(512) | 刷新令牌 |
| `expires_at` | datetime | 过期时间 |

### 9.4 `media_mapping`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `mapping_id` | bigint, 主键, 自增 | 映射 ID |
| `user_id` | bigint | 用户 ID |
| `song_title` | varchar(255) | 歌曲名 |
| `artist` | varchar(100) | 歌手 |
| `platform` | varchar(20) | 平台 |
| `external_id` | varchar(100) | 外部歌曲 ID |
| `cover_url` | varchar(512) | 封面地址 |

### 9.5 `action_dict`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `action_id` | int, 主键 | 操作 ID |
| `action_code` | varchar(50) | 操作编码 |
| `action_name` | varchar(100) | 操作名称 |
| `category` | varchar(50) | 分类 |

注意：`action_id` 不是自增字段，新增时需要手动传入。

### 9.6 `play_history`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `history_id` | bigint, 主键, 自增 | 播放历史 ID |
| `device_id` | bigint | 设备 ID |
| `user_id` | bigint | 用户 ID |
| `mapping_id` | bigint | 歌曲映射 ID |
| `play_duration` | bigint | 播放时长，单位秒 |
| `created_at` | datetime | 创建时间 |
| `style` | varchar(50) | 数据来源或类型 |

### 9.7 `friendship`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `user_id_1` | bigint, 联合主键 | 用户 1 |
| `user_id_2` | bigint, 联合主键 | 用户 2 |

### 9.8 `user_device_binding`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `user_id` | bigint, 联合主键 | 用户 ID |
| `device_id` | bigint, 联合主键 | 设备 ID |
| `custom_device_name` | varchar(50) | 用户自定义设备名 |
| `is_primary` | tinyint | 是否主设备 |

### 9.9 `user_feedback`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `feedback_id` | bigint, 主键, 自增 | 反馈 ID |
| `user_id` | bigint | 用户 ID |
| `content` | text | 反馈内容 |

### 9.10 `Daily_Stats`

| 字段 | 类型说明 | 说明 |
|---|---|---|
| `stat_date` | date, 主键 | 统计日期 |
| `total_play_count` | int | 总播放次数 |
| `unique_song_count` | int | 不重复歌曲数量 |
| `unique_user_count` | int | 不重复用户数量 |
| `unique_device_count` | int | 不重复设备数量 |
| `total_play_duration_seconds` | bigint | 总播放时长，单位秒 |
| `avg_play_duration_seconds` | decimal(10,2) | 平均播放时长，单位秒 |
| `hottest_song_id` | varchar(100) | 最热门歌曲 ID |
| `hottest_song_name` | varchar(255) | 最热门歌曲名 |
| `hottest_artist` | varchar(255) | 最热门歌手 |
| `hottest_play_count` | int | 最热门歌曲播放次数 |
| `generated_at` | datetime | 生成时间 |
| `updated_at` | datetime | 更新时间 |

---

## 10. 已验证结果

### 10.1 MySQL 连接验证

```bash
curl -k https://127.0.0.1/api/db/health
```

结果：

```text
MySQL connected
```

### 10.2 表查询验证

已成功查询：

```text
user
device
auth_token
media_mapping
action_dict
play_history
friendship
user_device_binding
user_feedback
```

`Daily_Stats` 字段已按照真实数据库结构修正为 `hottest_song_id`。

### 10.3 `device` 表完整 CRUD 验证

新增：

```bash
curl -k -X POST https://127.0.0.1/api/db/device \
  -H "Content-Type: application/json" \
  -d '{
    "device_number": "dev_test",
    "model_name": "test-speaker",
    "status": 1,
    "last_active": "2026-04-29 01:40:00"
  }'
```

查询：

```bash
curl -k "https://127.0.0.1/api/db/device?device_number=dev_test"
```

修改：

```bash
curl -k -X PUT https://127.0.0.1/api/db/device/6 \
  -H "Content-Type: application/json" \
  -d '{
    "device_number": "dev_test",
    "model_name": "test-speaker-updated",
    "status": 1,
    "last_active": "2026-04-29 01:45:00"
  }'
```

删除：

```bash
curl -k -X DELETE https://127.0.0.1/api/db/device/6
```

删除后再次查询：

```bash
curl -k "https://127.0.0.1/api/db/device?device_number=dev_test"
```

结果：

```text
data: []
```

说明删除生效。

---

## 11. 部署步骤

### 11.1 更新代码

```bash
cd /www/wwwroot/mysite
git pull origin main
```

### 11.2 检查服务器真实配置

服务器需要存在 `.env.db_api`：

```bash
cat .env.db_api
```

示例：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=smart_speaker
MYSQL_USER=root
MYSQL_PASSWORD=真实密码
```

注意：不要把 `.env.db_api` 提交到 GitHub。

### 11.3 重新构建 gateway

```bash
docker compose up -d --build --no-deps --force-recreate gateway
```

### 11.4 查看 gateway 日志

```bash
docker compose logs --tail=50 gateway
```

### 11.5 验证接口

```bash
curl -k https://127.0.0.1/api/db/health
curl -k https://127.0.0.1/api/db/tables
curl -k https://127.0.0.1/api/db/device
curl -k https://127.0.0.1/api/db/user
curl -k https://127.0.0.1/api/db/Daily_Stats
```

---

## 12. 检测所有真实表

```bash
for t in user device auth_token media_mapping action_dict play_history friendship user_device_binding user_feedback Daily_Stats
do
  echo "===== $t ====="
  curl -k "https://127.0.0.1/api/db/$t"
  echo
done
```

如果每个表都返回：

```json
"status": "success"
```

说明查询接口正常。

---

## 13. 架构图说明

### 13.1 系统架构图

```text
用户 / 小程序 / 测试工具
        |
        | HTTPS
        v
Docker Gateway 容器
Flask + Gunicorn
        |
        | /api/db/... CRUD 请求
        v
db_api_service.py
        |
        v
db_config.py
        |
        v
MySQL: smart_speaker
```

### 13.2 请求处理流程

```text
HTTP 请求
  -> Flask 路由匹配
  -> db_api_service.py 判断表名和请求方法
  -> db_config.py 获取 MySQL 连接
  -> 执行 SELECT / INSERT / UPDATE / DELETE
  -> 序列化 datetime / decimal
  -> 返回 JSON
```

---

## 14. 本人完成内容总结

本次本人负责 Flask 数据库接口开发部分，完成内容如下：

1. 在原有 Flask Gateway 中新增 `/api/db/...` 数据库接口。
2. 使用 `Blueprint` 将 `db_api_service.py` 注册到 `app.py`。
3. 使用 `db_config.py` 统一管理 MySQL 连接。
4. 使用 `.env.db_api` 和 `docker-compose.yml` 将数据库配置注入 gateway 容器。
5. 按照 `smart_speaker` 实际 MySQL 表结构配置接口字段。
6. 实现对真实业务表的查询、新增、修改、删除操作。
7. 完成 HTTPS 环境下的接口测试。
8. 完成 `device` 表完整增删改查验证。
9. 修正 `Daily_Stats` 字段为真实字段 `hottest_song_id`。
10. 移除不存在的 `operation_log` 表接口配置。
