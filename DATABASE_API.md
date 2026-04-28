# 数据库接口开发说明

## 1. 本次新增内容

为了尽量不影响你原来的项目，我没有改现有的 `app.py` 网关逻辑，而是额外新增了一套独立的数据库接口服务：

- `db_api_app.py`
  - 独立 Flask 启动入口
- `db_api_service.py`
  - MySQL CRUD 和 MongoDB 查看逻辑
- `db_tools/mysql_native.py`
  - 纯 Python MySQL 原生协议客户端
- `db_tools/mysql_probe.py`
  - MySQL 结构探测脚本
- `db_tools/mongo_native.py`
  - 纯 Python MongoDB 原生协议只读客户端
- `db_tools/mongo_probe.py`
  - MongoDB 探测脚本
- `.env.db_api.example`
  - 数据库接口服务环境变量示例

这套代码和你原来的网关服务是分开的，可以单独启动，默认端口是 `5001`。

## 1.1 Flask 接口到底是什么

你可以把 Flask 接口理解成：

- 一个运行在服务器上的 Python Web 服务
- 它负责接收前端、Postman、浏览器或者其他系统发过来的 HTTP 请求
- 根据请求路径、请求方法和请求参数，调用后端 Python 逻辑
- 再由 Python 逻辑去访问 MySQL / MongoDB
- 最后把数据库结果重新包装成 JSON 响应返回给调用方

用一句最容易画图的话来说就是：

`调用方 -> Flask 路由 -> 业务服务层 -> 数据库访问层 -> MySQL/MongoDB -> 返回 JSON`

## 1.2 这次新增接口在项目里的职责

这次新增的数据库接口服务，主要职责是：

- 对 MySQL 业务表提供统一的增删改查入口
- 对 MongoDB 提供只读探测入口
- 不改动你原有 `app.py` 网关逻辑
- 让数据库访问能力从原项目里“独立出来”

所以它本质上是一个“数据库管理型 Flask API 服务”。

## 2. 我实际查看到的数据库情况

### 2.1 MySQL

- 服务器：你的 MySQL 云服务器
- 账号：使用你自己的数据库账号
- 业务库：`smart_speaker`
- MySQL 版本：`8.0.45-0ubuntu0.22.04.1`

我实际探测到 `smart_speaker` 中有下面这些业务表：

- `Daily_Stats`
- `action_dict`
- `auth_token`
- `device`
- `friendship`
- `media_mapping`
- `play_history`
- `user`
- `user_device_binding`
- `user_feedback`

其中典型数据情况如下：

- `device`
  - 主键：`device_id`
  - 示例数据：`dev_01`、`dev_02`、`dev_04`
- `user`
  - 主键：`user_id`
  - 示例数据：`user_01@smart-speaker.local`
- `user_device_binding`
  - 复合主键：`user_id + device_id`
- `play_history`
  - 主键：`history_id`
  - 记录了设备、用户、歌曲映射、播放时长、创建时间

### 2.2 MongoDB

- 连接串格式示例：`mongodb://<username>:<password>@<host>:27017/musicplayer?authSource=musicplayer`
- 我在 `2026-04-28` 实际连接成功后看到：
  - 当前数据库名：`musicplayer`
  - 集合数量：`0`
  - 可见数据库：`READ_ME_TO_RECOVER_YOUR_DATA`、`admin`、`config`

也就是说，MongoDB 当前可以认证登录，但 `musicplayer` 这个库目前没有返回任何集合数据。如果这不是你的预期，需要你重点检查云服务器上的 MongoDB 数据是否还在这个实例里。

## 3. 已实现的 Flask 接口

接口前缀统一为：`/db-api`

### 3.1 健康检查

- 方法：`GET`
- 路径：`/db-api/health`
- 作用：检查 MySQL 和 MongoDB 是否能访问，并返回基本概况

示例响应：

```json
{
  "success": true,
  "message": "success",
  "data": {
    "mysql_database": "smart_speaker",
    "mysql_table_count": 10,
    "mongo_database": "musicplayer",
    "mongo_collection_count": 0
  }
}
```

### 3.2 获取 MySQL 全部业务表

- 方法：`GET`
- 路径：`/db-api/mysql/tables`
- 作用：列出支持 CRUD 的表，以及每张表的主键信息

### 3.3 刷新 MySQL 元数据缓存

- 方法：`POST`
- 路径：`/db-api/mysql/metadata/refresh`
- 作用：当你在 MySQL 中新增字段或新表后，调用这个接口刷新服务缓存

### 3.4 获取某张表的字段结构

- 方法：`GET`
- 路径：`/db-api/mysql/tables/<table_name>/schema`
- 作用：查看字段类型、主键、必填字段

示例：

```text
GET /db-api/mysql/tables/device/schema
```

### 3.5 分页查询某张表的数据

- 方法：`GET`
- 路径：`/db-api/mysql/tables/<table_name>/rows`
- 参数：
  - `limit`：每页条数，默认 `20`，最大 `200`
  - `offset`：偏移量，默认 `0`

示例：

```text
GET /db-api/mysql/tables/device/rows?limit=10&offset=0
```

### 3.6 根据主键查询单条记录

- 方法：`GET`
- 路径：`/db-api/mysql/tables/<table_name>/record`
- 说明：
  - 单主键表：把主键作为查询参数传入
  - 复合主键表：把所有主键都作为查询参数传入

单主键示例：

```text
GET /db-api/mysql/tables/device/record?device_id=1
```

复合主键示例：

```text
GET /db-api/mysql/tables/user_device_binding/record?user_id=1&device_id=3
```

### 3.7 新增 MySQL 记录

- 方法：`POST`
- 路径：`/db-api/mysql/tables/<table_name>/record`
- 请求体：JSON 对象
- 说明：
  - 字段名必须是真实表字段
  - 非空且无默认值、无自增的字段必须传

`device` 表新增示例：

```json
{
  "device_number": "dev_99",
  "model_name": "smart-speaker-simulator",
  "status": 1,
  "last_active": "2026-04-28 20:00:00"
}
```

`user_device_binding` 表新增示例：

```json
{
  "user_id": 2,
  "device_id": 1,
  "custom_device_name": "living-room-speaker",
  "is_primary": 0
}
```

### 3.8 修改 MySQL 记录

- 方法：`PUT`
- 路径：`/db-api/mysql/tables/<table_name>/record`
- 请求体格式：

```json
{
  "primary_keys": {
    "user_id": 2,
    "device_id": 1
  },
  "data": {
    "custom_device_name": "living-room-speaker-v2",
    "is_primary": 1
  }
}
```

- 说明：
  - `primary_keys` 用来定位记录
  - `data` 是要修改的字段
  - 不允许修改主键字段本身

### 3.9 删除 MySQL 记录

- 方法：`DELETE`
- 路径：`/db-api/mysql/tables/<table_name>/record`
- 说明：
  - 删除条件通过查询参数传主键

单主键示例：

```text
DELETE /db-api/mysql/tables/device/record?device_id=15
```

复合主键示例：

```text
DELETE /db-api/mysql/tables/user_device_binding/record?user_id=2&device_id=1
```

### 3.10 查看 MongoDB 概况

- 方法：`GET`
- 路径：`/db-api/mongo/overview`
- 作用：
  - 查看当前 Mongo 库名
  - 查看集合列表
  - 查看每个集合前 3 条样例文档
  - 查看账号当前可见数据库

## 4. 整体逻辑链条

这一部分你可以直接拿去画框架图。

### 4.1 系统结构

```text
调用端（浏览器 / 前端 / Postman）
        |
        v
Flask 路由层（db_api_app.py）
        |
        v
服务层（db_api_service.py）
        |
        +------------------> MySQL 原生访问层（db_tools/mysql_native.py）
        |                              |
        |                              v
        |                        MySQL: smart_speaker
        |
        +------------------> Mongo 原生访问层（db_tools/mongo_native.py）
                                       |
                                       v
                                 MongoDB: musicplayer
```

### 4.2 一次 MySQL 查询请求的执行链

以这个接口为例：

`GET /db-api/mysql/tables/device/record?device_id=1`

它的执行过程是：

1. 客户端向 Flask 发起 HTTP 请求。
2. `db_api_app.py` 里的路由函数 `mysql_get_record()` 接收到请求。
3. 路由函数先解析路径参数 `device` 和查询参数 `device_id=1`。
4. 路由函数调用 `db_api_service.py` 的 `get_record('device', {'device_id': 1})`。
5. 服务层先读取表元数据，确认：
   - `device` 表存在
   - 它的主键是 `device_id`
6. 服务层拼出 SQL：

```sql
SELECT * FROM `device` WHERE `device_id` = 1 LIMIT 1;
```

7. SQL 交给 `db_tools/mysql_native.py` 发送到 MySQL。
8. MySQL 返回结果。
9. 服务层把结果整理成 Python 字典。
10. Flask 把字典包装成 JSON 返回给客户端。

### 4.3 一次新增记录请求的执行链

以这个接口为例：

`POST /db-api/mysql/tables/device/record`

请求体：

```json
{
  "device_number": "dev_99",
  "model_name": "smart-speaker-simulator",
  "status": 1,
  "last_active": "2026-04-28 20:00:00"
}
```

执行过程是：

1. Flask 路由收到 POST 请求。
2. 路由把 JSON 请求体解析为 Python 字典。
3. 服务层读取 `device` 表元数据。
4. 校验请求字段是否都是真实字段。
5. 校验必填字段是否都传了。
6. 生成 SQL：

```sql
INSERT INTO `device` (`device_number`, `model_name`, `status`, `last_active`)
VALUES ('dev_99', 'smart-speaker-simulator', 1, '2026-04-28 20:00:00');
```

7. 把 SQL 发给 MySQL 执行。
8. 如果主键是自增字段，拿到 `last_insert_id`。
9. 再用主键反查一次，把完整记录返回。
10. Flask 以 JSON 形式告诉调用方“新增成功”。

### 4.4 一次修改请求的执行链

以 `user_device_binding` 为例，这张表是复合主键：

- `user_id`
- `device_id`

请求：

```json
{
  "primary_keys": {
    "user_id": 2,
    "device_id": 1
  },
  "data": {
    "custom_device_name": "living-room-speaker-v2",
    "is_primary": 1
  }
}
```

执行过程：

1. Flask 路由接收 PUT 请求。
2. 服务层先识别这张表的主键组合是 `user_id + device_id`。
3. 用 `primary_keys` 定位记录。
4. 用 `data` 构建更新字段。
5. 生成 SQL：

```sql
UPDATE `user_device_binding`
SET `custom_device_name` = 'living-room-speaker-v2', `is_primary` = 1
WHERE `user_id` = 2 AND `device_id` = 1;
```

6. 执行成功后，再查一次最新记录并返回。

### 4.5 一次删除请求的执行链

以复合主键删除为例：

`DELETE /db-api/mysql/tables/user_device_binding/record?user_id=2&device_id=1`

执行过程：

1. Flask 路由接收 DELETE 请求。
2. 服务层识别主键字段。
3. 先查出这条旧记录，方便回显。
4. 生成删除 SQL：

```sql
DELETE FROM `user_device_binding`
WHERE `user_id` = 2 AND `device_id` = 1;
```

5. 删除成功后，把被删掉的旧记录返回。

## 5. 代码分层说明

### 5.1 `db_api_app.py`

这一层是“接口层”或者“控制器层”。

它负责：

- 定义 URL 路径
- 区分 GET / POST / PUT / DELETE
- 解析请求参数
- 调用服务层
- 返回统一 JSON
- 处理错误码

### 5.2 `db_api_service.py`

这一层是“业务服务层”。

它负责：

- 读取 MySQL 元数据
- 判断表是否存在
- 判断主键是什么
- 校验字段是否合法
- 拼接 SQL
- 组织返回数据
- 统一调用 MySQL 和 MongoDB 访问层

### 5.3 `db_tools/mysql_native.py`

这一层是“MySQL 访问层”。

它负责：

- 用原生 MySQL 协议连接数据库
- 发送 SQL
- 接收 MySQL 返回结果
- 把结果转成 Python 可读结构

### 5.4 `db_tools/mongo_native.py`

这一层是“MongoDB 访问层”。

它负责：

- 连接 MongoDB
- 做 SCRAM 认证
- 执行 `listCollections`、`find`、`listDatabases` 等命令
- 把 BSON 结果转成 Python 字典

## 6. 对 MySQL 表完成增删改查的核心原理

这一部分你可以直接拿去写报告。

### 6.1 查

查的本质是执行 `SELECT`：

- 查列表：`SELECT * FROM 表 LIMIT ? OFFSET ?`
- 查单条：`SELECT * FROM 表 WHERE 主键条件 LIMIT 1`

### 6.2 增

增的本质是执行 `INSERT`：

- 根据请求体里的字段动态拼接字段列表
- 把值做转义，避免 SQL 语法错误
- 执行插入
- 如果表有自增主键，再根据主键回查完整记录

### 6.3 改

改的本质是执行 `UPDATE`：

- 先找到主键字段
- 根据 `primary_keys` 拼接 `WHERE`
- 根据 `data` 拼接 `SET`
- 执行更新
- 更新后再查一次最新数据返回

### 6.4 删

删的本质是执行 `DELETE`：

- 根据主键构建 `WHERE`
- 删除之前先查一次旧记录
- 删除后把旧记录返回，方便确认删的是哪条

## 7. 适合你画图的两个模板

### 7.1 框架图模板

```text
前端/测试工具
    |
    v
Flask API 服务
    |
    +---- MySQL CRUD 模块 ----> smart_speaker 数据库
    |
    +---- Mongo 探测模块 -----> musicplayer 数据库
```

### 7.2 流程图模板

```text
发起请求
  -> Flask 路由匹配
  -> 解析参数
  -> 调服务层
  -> 校验表和字段
  -> 生成 SQL / Mongo 命令
  -> 执行数据库操作
  -> 组装结果
  -> 返回 JSON
```

## 8. 统一返回格式

成功时：

```json
{
  "success": true,
  "message": "success",
  "data": {}
}
```

失败时：

```json
{
  "success": false,
  "message": "错误信息"
}
```

## 9. 我已经验证过的能力

我已经实际用代码验证了下面这一组流程：

- 成功读取 MySQL 业务表清单
- 成功读取 `device` 表结构
- 成功读取 MongoDB 当前概况
- 成功对 `user_device_binding` 表完成一整套 CRUD 验证：
  - 创建一条测试绑定
  - 查询这条绑定
  - 修改这条绑定
  - 删除这条绑定

测试数据最后已经删除，没有保留脏数据。

## 10. 云服务器部署与启动步骤

这一部分是“你登录到云服务器之后”的操作步骤。

### 10.1 克隆或更新代码

如果服务器上还没有项目：

```bash
git clone https://github.com/kk455152/ruanjiansheji.git
cd ruanjiansheji
```

如果服务器上已经有项目：

```bash
cd ruanjiansheji
git pull origin main
```

### 10.2 创建 Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 10.3 安装依赖

```bash
pip install -r requirements.txt
```

### 10.4 配置环境变量

```bash
export MYSQL_HOST=<your-mysql-host>
export MYSQL_PORT=3306
export MYSQL_USER=<your-mysql-user>
export MYSQL_PASSWORD=<your-mysql-password>
export MYSQL_DATABASE=<your-mysql-database>
export MONGO_URI='mongodb://<your-mongo-user>:<your-mongo-password>@<your-mongo-host>:27017/<your-mongo-database>?authSource=<your-auth-db>'
export DB_API_HOST=0.0.0.0
export DB_API_PORT=5001
```

### 10.5 启动 Flask 服务

```bash
python db_api_app.py
```

### 10.6 后台启动方式

如果你想让它在后台运行，可以这样：

```bash
nohup python db_api_app.py > db_api.log 2>&1 &
```

然后查看进程：

```bash
ps -ef | grep db_api_app.py
```

### 10.7 对外访问

如果服务器防火墙和安全组已经放行 `5001` 端口，那么你可以直接访问：

```text
http://<your-server-ip>:5001/db-api/health
```

### 10.8 如果你要长期运行

建议后续再做下面两件事：

- 用 `gunicorn` 或 `uwsgi` 托管 Flask
- 用 `nginx` 做反向代理

这样会比直接 `python db_api_app.py` 更稳定。

## 11. 本地启动方法

### 11.1 安装依赖

你的项目原本就已经有 `Flask` 依赖声明。只要你的运行环境装好了 `requirements.txt` 里的依赖即可。

如果你本机还没装 Flask，可以执行：

```powershell
python -m pip install -r requirements.txt
```

### 11.2 配置环境变量

你可以直接参考 `.env.db_api.example`。

PowerShell 临时设置方式：

```powershell
$env:MYSQL_HOST="<your-mysql-host>"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="<your-mysql-user>"
$env:MYSQL_PASSWORD="<your-mysql-password>"
$env:MYSQL_DATABASE="<your-mysql-database>"
$env:MONGO_URI="mongodb://<your-mongo-user>:<your-mongo-password>@<your-mongo-host>:27017/<your-mongo-database>?authSource=<your-auth-db>"
$env:DB_API_HOST="0.0.0.0"
$env:DB_API_PORT="5001"
```

### 11.3 启动数据库接口服务

```powershell
python db_api_app.py
```

启动后访问：

- `http://127.0.0.1:5001/db-api/health`

## 12. 常用调试命令

### 12.1 重新查看 MySQL 库表结构

```powershell
$env:MYSQL_USER="<your-mysql-user>"
$env:MYSQL_PASSWORD="<your-mysql-password>"
python db_tools\mysql_probe.py
```

### 12.2 重新查看 MongoDB 当前状态

```powershell
$env:MONGO_URI="mongodb://<your-mongo-user>:<your-mongo-password>@<your-mongo-host>:27017/<your-mongo-database>?authSource=<your-auth-db>"
python db_tools\mongo_probe.py
```

## 13. 你接下来最建议做的事

### 13.1 先确认 MongoDB 是否真的是空库

因为我在 `2026-04-28` 实际读到的是：

- `musicplayer` 没有集合
- 可见库里出现了 `READ_ME_TO_RECOVER_YOUR_DATA`

如果这是异常现象，建议你先登录云服务器检查 MongoDB 数据目录、实例配置和备份情况。

### 13.2 如果你想把接口继续做细

当前这版已经是通用 CRUD。
如果你下一步想要，我还可以继续帮你做：

- 按表拆成更“业务化”的接口
- 增加参数校验
- 增加 Swagger/OpenAPI 文档
- 增加登录鉴权
- 增加单元测试和接口测试
