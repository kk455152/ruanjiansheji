# 智能音箱数据上报系统 RESTful API 文档

版本：v1.0.0

## 1. 概述

本文档说明智能音箱模拟终端与云端服务器之间的数据上报接口。系统通过 HTTPS 提供 RESTful API，客户端将模拟设备数据进行 AES 加密后上传到服务器。服务器完成身份鉴权、数据解密后，将合法数据写入 RabbitMQ 消息队列，由后端 Worker 模块进行本地持久化保存。

当前后端主要包含以下能力：

- 基于 HTTPS 的 RESTful API 数据接收。
- 基于 `Authorization` Header 和 `timestamp` 的动态 Token 鉴权。
- 基于 AES 的业务数据加密传输，服务端解密后处理。
- 基于 RabbitMQ 的消息队列转发。
- Worker 消费队列数据，并按设备和数据类型保存为本地 JSON 文件。
- 提供内部监控接口，用于查看网关处理速率和队列状态。

## 2. Base URL

```text
https://8.137.165.220
```

本项目网关默认监听 HTTPS 443 端口。请求示例中如未单独说明，均基于以上 Base URL。

## 3. 通用安全机制

### 3.1 Authentication

所有业务上报接口都需要携带 `Authorization` Header。服务端不会以 Body 中的 `token` 字段作为最终鉴权依据，而是以 `Authorization` Header 为准。

Token 生成规则：

```text
token = MD5(TOKEN_SALT + timestamp)
```

其中：

```text
TOKEN_SALT = smart_speaker_2026_salt
timestamp = 当前 Unix 时间戳，单位为秒
```

请求 Header 示例：

```http
Authorization: 2b7337190886a048757041793740266e
Content-Type: application/json
```

如果缺少 `timestamp`、缺少 `Authorization` Header，或者 Token 校验失败，服务器返回 `401 Unauthorized`，数据不会进入 RabbitMQ，也不会被保存。

### 3.2 数据加密

业务数据在客户端侧使用 AES 加密，服务端收到后进行解密。当前实现支持：

- OpenSSL/CryptoJS 兼容的 salted AES-CBC 格式。
- 旧版本 AES-ECB 密文的兼容解密。

请求 Body 中的 `data` 字段为加密后的密文字符串，通常以 Base64 格式传输。

### 3.3 通用请求 Body

所有业务上报接口采用相同的外层 JSON 结构：

```json
{
  "timestamp": 1776355200,
  "token": "2b7337190886a048757041793740266e",
  "data": "U2FsdGVkX1...encrypted_payload...",
  "sign": "2b7337190886a048757041793740266e"
}
```

字段说明：

| 名称 | 位置 | 类型 | 必选 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | Header | string | 是 | 动态 Token。服务端实际使用该 Header 进行鉴权。 |
| Content-Type | Header | string | 是 | 固定为 `application/json`。 |
| timestamp | Body | integer | 是 | 生成 Token 时使用的 Unix 时间戳。 |
| data | Body | string | 是 | AES 加密后的业务数据密文。 |
| token | Body | string | 否 | 客户端兼容字段，可与 Header 中 Token 保持一致。当前服务端不以该字段作为最终鉴权依据。 |
| sign | Body | string | 否 | 客户端兼容字段，可与 Token 保持一致。当前服务端不单独校验该字段。 |

### 3.4 解密后的业务数据结构

`data` 解密后应为如下 JSON 对象：

```json
{
  "device_id": "dev_01",
  "type": "volume",
  "value": 50
}
```

字段说明：

| 名称 | 类型 | 必选 | 说明 |
| --- | --- | --- | --- |
| device_id | string | 是 | 设备 ID，例如 `dev_01`。 |
| type | string | 是 | 数据类型，例如 `volume`、`signal_strength`。 |
| value | number / boolean / string | 是 | 具体业务值，不同接口含义不同。 |

服务器解密成功后，会额外写入 `api_path` 字段，用于记录数据来自哪个 API 路径。

## 4. 通用返回格式

### 4.1 成功响应

HTTP Status Code：`200 OK`

```json
{
  "status": "success",
  "message": "Verified data from /api/volume queued for broker delivery"
}
```

说明：请求通过鉴权和解密后，数据已经进入网关发送队列，等待投递到 RabbitMQ。

### 4.2 错误响应

#### Invalid JSON

HTTP Status Code：`400 Bad Request`

```json
{
  "status": "error",
  "message": "Invalid JSON Payload"
}
```

#### Unauthorized

HTTP Status Code：`401 Unauthorized`

```json
{
  "status": "error",
  "message": "Unauthorized: Invalid Token"
}
```

可能原因：

- 缺少 `timestamp`。
- 缺少或错误的 `Authorization` Header。
- `Authorization` Header 与服务端计算出的 Token 不一致。
- 缺少 `data` 字段。
- `data` 字段解密失败。

#### Gateway Queue Busy

HTTP Status Code：`503 Service Unavailable`

```json
{
  "status": "error",
  "message": "Gateway queue is busy, please retry"
}
```

说明：网关内部发送队列已满，客户端可稍后重试。

## 5. 业务上报接口

### 5.1 上报信号强度

接口名称：`signal_strength`

```http
POST /api/signal
```

说明：用于上报智能音箱设备的信号强度数据。

解密后的业务数据示例：

```json
{
  "device_id": "dev_01",
  "type": "signal_strength",
  "value": -60.5
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| device_id | string | 设备 ID。 |
| type | string | 固定为 `signal_strength`。 |
| value | number | 信号强度，单位 dBm。 |

完整请求示例：

```http
POST /api/signal HTTP/1.1
Host: 8.137.165.220
Content-Type: application/json
Authorization: 2b7337190886a048757041793740266e
```

```json
{
  "timestamp": 1776355200,
  "token": "2b7337190886a048757041793740266e",
  "data": "U2FsdGVkX1...encrypted_payload...",
  "sign": "2b7337190886a048757041793740266e"
}
```

### 5.2 上报音量

接口名称：`volume`

```http
POST /api/volume
```

说明：用于上报智能音箱设备的当前音量。

解密后的业务数据示例：

```json
{
  "device_id": "dev_01",
  "type": "volume",
  "value": 50
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| device_id | string | 设备 ID。 |
| type | string | 固定为 `volume`。 |
| value | integer | 音量值，范围通常为 0 到 100。 |

### 5.3 上报低音增益

接口名称：`bass_gain`

```http
POST /api/bass
```

说明：用于上报智能音箱设备的低音增益数据。

解密后的业务数据示例：

```json
{
  "device_id": "dev_01",
  "type": "bass_gain",
  "value": 6
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| device_id | string | 设备 ID。 |
| type | string | 固定为 `bass_gain`。 |
| value | integer | 低音增益值。 |

### 5.4 上报连接状态

接口名称：`connection_status`

```http
POST /api/status/connection
```

说明：用于上报智能音箱设备的连接状态。模拟器中的 `is_connected` 和 `is_connecting` 类型都会发送到该接口。

解密后的业务数据示例：

```json
{
  "device_id": "dev_01",
  "type": "is_connected",
  "value": true
}
```

或：

```json
{
  "device_id": "dev_01",
  "type": "is_connecting",
  "value": false
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| device_id | string | 设备 ID。 |
| type | string | `is_connected` 或 `is_connecting`。 |
| value | boolean | 连接状态值。 |

### 5.5 上报收藏状态

接口名称：`like_status`

```http
POST /api/status/like
```

说明：用于上报智能音箱设备的收藏、喜欢状态。

解密后的业务数据示例：

```json
{
  "device_id": "dev_01",
  "type": "like_status",
  "value": true
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| device_id | string | 设备 ID。 |
| type | string | 固定为 `like_status`。 |
| value | boolean | 是否收藏或喜欢。 |

## 6. 内部监控接口

### 6.1 获取网关指标

接口名称：`internal_metrics`

```http
GET /internal/metrics
```

说明：用于查看网关近期处理能力、内部队列长度等运行指标。该接口主要用于系统内部监控、自动扩容和压力测试观察。

当前实现中该接口不要求业务鉴权，建议仅在内网或受控环境中访问。

返回示例：

```json
{
  "updated_at": 1776355200.123,
  "accepted_per_second": 9.2,
  "accepted_in_window": 92,
  "window_seconds": 10.0,
  "dispatcher_queue_size": 0,
  "process_count": 4
}
```

字段说明：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| updated_at | number | 指标更新时间戳。 |
| accepted_per_second | number | 最近统计窗口内的平均接收速率。 |
| accepted_in_window | integer | 最近统计窗口内通过网关接收的数据条数。 |
| window_seconds | number | 统计窗口长度，单位为秒。 |
| dispatcher_queue_size | integer | 网关内部待发送队列长度。 |
| process_count | integer | 多进程模式下参与汇总的进程数量。 |

## 7. 服务端处理流程

业务上报接口的处理流程如下：

1. 客户端生成模拟数据。
2. 客户端根据 `timestamp` 生成动态 Token。
3. 客户端将业务数据使用 AES 加密，放入 Body 的 `data` 字段。
4. 客户端通过 HTTPS POST 请求上传数据，并在 Header 中携带 `Authorization`。
5. Flask 网关校验 `Authorization` 和 `timestamp`。
6. 网关解密 `data` 字段。
7. 鉴权和解密成功后，网关将明文业务数据发布到 RabbitMQ。
8. Worker 从 RabbitMQ 队列消费数据。
9. Writer Worker 将数据保存到服务器本地目录。

本地保存路径：

```text
/www/wwwroot/mysite/data_db/{device_id}/{type}.json
```

保存内容为 JSON Lines 格式，每条数据占一行。

## 8. RabbitMQ 队列说明

系统使用 RabbitMQ 作为消息队列中间件。网关将合法业务数据发布到 Exchange：

```text
smart_speaker_exchange
```

相关队列包括：

| 队列名称 | 作用 |
| --- | --- |
| writer_v2 | Writer Worker 消费该队列，将数据持久化保存到本地文件。 |
| validator_v2 | Validator Worker 消费该队列，用于业务字段范围检查和日志输出。 |
| logger_v2 | Logger Worker 消费该队列，用于记录系统运行日志。 |
| speaker_data | 历史或兼容队列名称。 |

当前系统中，身份鉴权和解密由 API Gateway 完成；Worker 层主要负责业务处理、校验输出、日志和本地保存。

## 9. 状态码汇总

| HTTP Status Code | 含义 | 说明 |
| --- | --- | --- |
| 200 OK | 请求成功 | 数据通过鉴权和解密，已进入队列处理流程。 |
| 400 Bad Request | 请求格式错误 | 请求 Body 不是合法 JSON。 |
| 401 Unauthorized | 鉴权或解密失败 | Token 错误、缺少时间戳、缺少密文或密文无法解密。 |
| 503 Service Unavailable | 网关繁忙 | 网关内部队列已满，需要稍后重试。 |
| 500 Internal Server Error | 服务端异常 | 服务端出现未预期错误。 |

## 10. 示例：一次完整的业务请求

以下示例展示客户端上报音量数据的 HTTP 请求结构。实际 `data` 字段应由客户端使用 AES 加密生成。

```http
POST /api/volume HTTP/1.1
Host: 8.137.165.220
Content-Type: application/json
Authorization: 2b7337190886a048757041793740266e
```

```json
{
  "timestamp": 1776355200,
  "token": "2b7337190886a048757041793740266e",
  "data": "U2FsdGVkX1...encrypted_payload...",
  "sign": "2b7337190886a048757041793740266e"
}
```

成功响应：

```json
{
  "status": "success",
  "message": "Verified data from /api/volume queued for broker delivery"
}
```
