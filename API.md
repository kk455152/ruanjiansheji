music
v1.0.0
Base URLs:
Authentication
Default
POST signal_strength
POST /api/signal
本接口用于智能音箱终端向云端服务器上报设备实时状态数据。数据为信号强度。 设备id：dev_01 验证机制 强制要求：为了确保数据来源合法，所有请求必须在 JSON 中携带 token 字段。 Token 值：2b7337190886a048757041793740266e 拦截逻辑：若 token 缺失或不符，后端验证模块（Validator）将直接拦截该请求，数据不会被存储。 接口说明： { "device_id": "string", "type": "string", "value": "integer", "signal_strength": "number" }
Body 请求参数
{
  "token": "2b7337190886a048757041793740266e",
  "data": "U2FsdGVkX19v8+I7z... (此处是加密后的密文)",
  "sign": "a1b2c3d4..."
}
请求参数
名称	位置	类型	必选	说明
body	body	object	是	none
» token	body	string	是	none
» data	body	string	是	none
» sign	body	string	是	none
返回示例
100 Response
{}
200 Response
{
  "status": "success",
  "message": "数据合法，已进入处理队列"
}
400 Response
{
  "code": 400,
  "message": "Token verification failed"
}
500 Response
{
  "message": "Internal Server Error"
}
返回结果
状态码	状态码含义	说明	数据模型
100	Continue
none	Inline
102	Processing
none	Inline
200	OK
none	Inline
400	Bad Request
none	Inline
404	Not Found
none	Inline
500	Internal Server Error
none	Inline
返回数据结构
状态码 200
名称	类型	必选	约束	中文名	说明
» status	string	true	none		none
» message	string	true	none		none
状态码 400
名称	类型	必选	约束	中文名	说明
» code	integer	true	none		错误码 (如 4001)
» message	string	true	none		错误描述
状态码 500
名称	类型	必选	约束	中文名	说明
» message	string	true	none		Server Error
返回头部 Header
Status	Header	Type	Format	Description
200	Authorization	string		所有请求必须携带此 Header，否则 网关直接拦截并返回 401 Unauthorized 或 403 Forbidden
POST volume
POST /api/volume
本接口用于智能音箱终端向云端服务器上报设备实时状态数据。数据为音量。 设备id：dev_01 验证机制 强制要求：为了确保数据来源合法，所有请求必须在 JSON 中携带 token 字段。 Token 值：smart_speaker_2026 拦截逻辑：若 token 缺失或不符，后端验证模块（Validator）将直接拦截该请求，数据不会被存储。 { "device_id": "string", "type": "string", "value": "integer", "volume": "number" }
Body 请求参数
{
  "timestamp": "{{current_timestamp}}",
  "token": "{{current_token}}",
  "data": "U2FsdGVk...",
  "sign": "a1b2c3d4..."
}
请求参数
名称	位置	类型	必选	说明
Authorization	header	string	否	所有请求必须携带此 Header，否则 网关直接拦截并返回 401 Unauthorized 或 403 Forbidden
body	body	object	是	none
» timestamp	body	integer	是	none
» token	body	string	是	none
» data	body	string	是	none
» sign	body	string	是	none
返回示例
100 Response
{}
200 Response
{
  "status": "success",
  "message": "数据合法，已进入处理队列"
}
400 Response
{
  "code": 400,
  "message": "Token verification failed"
}
500 Response
{
  "message": "Internal Server Error"
}
返回结果
状态码	状态码含义	说明	数据模型
100	Continue
none	Inline
102	Processing
none	Inline
200	OK
none	Inline
400	Bad Request
none	Inline
404	Not Found
none	Inline
500	Internal Server Error
none	Inline
返回数据结构
状态码 200
名称	类型	必选	约束	中文名	说明
» status	string	true	none		none
» message	string	true	none		none
状态码 400
名称	类型	必选	约束	中文名	说明
» code	integer	true	none		错误码（如4001）
» message	string	true	none		错误说明
状态码 500
名称	类型	必选	约束	中文名	说明
» message	string	true	none		Server Error
POST bass_gain
POST /api/bass
本接口用于智能音箱终端向云端服务器上报设备实时状态数据。数据为低音增益。 设备id：dev_01 验证机制 强制要求：为了确保数据来源合法，所有请求必须在 JSON 中携带 token 字段。 Token 值：smart_speaker_2026 拦截逻辑：若 token 缺失或不符，后端验证模块（Validator）将直接拦截该请求，数据不会被存储。 { "device_id": "string", "type": "string", "value": "integer", "bass_gain": "number" }
Body 请求参数
{
  "timestamp": "{{current_timestamp}}",
  "token": "{{current_token}}",
  "data": "T3BlbiBTZXNhbWU... (此处是低音业务数据加密后的密文)",
  "sign": "b5c6d7e8..."
}
请求参数
名称	位置	类型	必选	说明
Authorization	header	string	否	所有请求必须携带此 Header，否则 网关直接拦截并返回 401 Unauthorized 或 403 Forbidden
body	body	object	是	none
» timestamp	body	string	是	none
» token	body	string	是	none
» data	body	string	是	none
» sign	body	string	是	none
返回示例
100 Response
{}
200 Response
{
  "status": "success",
  "message": "数据合法，已进入处理队列"
}
400 Response
{
  "code": 400,
  "message": "Token verification failed"
}
500 Response
{
  "message": "Internal Server Error"
}
返回结果
状态码	状态码含义	说明	数据模型
100	Continue
none	Inline
102	Processing
none	Inline
200	OK
none	Inline
400	Bad Request
none	Inline
404	Not Found
none	Inline
500	Internal Server Error
none	Inline
返回数据结构
状态码 200
名称	类型	必选	约束	中文名	说明
» status	string	true	none		none
» message	string	true	none		none
状态码 400
名称	类型	必选	约束	中文名	说明
» code	integer	true	none		错误码（如4001）
» message	string	true	none		错误说明
状态码 500
名称	类型	必选	约束	中文名	说明
» message	string	true	none		none
POST is_connected
POST /api/connection
本接口用于智能音箱终端向云端服务器上报设备实时状态数据。数据为连接状态。 设备id：dev_01 验证机制 强制要求：为了确保数据来源合法，所有请求必须在 JSON 中携带 token 字段。 Token 值：smart_speaker_2026 拦截逻辑：若 token 缺失或不符，后端验证模块（Validator）将直接拦截该请求，数据不会被存储。 { "device_id": "string", "type": "string", "value": "integer", "bass_gain": "number" }
Body 请求参数
{
  "timestamp": "{{current_timestamp}}",
  "token": "{{current_token}}",
  "data": "aG9sYV9hbWlnbw... (此处是连接状态业务数据加密后的密文)",
  "sign": "c3d4e5f6..."
}
请求参数
名称	位置	类型	必选	说明
Authorization	header	string	否	所有请求必须携带此 Header，否则 网关直接拦截并返回 401 Unauthorized 或 403 Forbidden
body	body	object	是	none
» timestamp	body	integer	是	none
» token	body	string	是	none
» data	body	string	是	none
» sign	body	string	是	none
返回示例
100 Response
{}
200 Response
{
  "status": "success",
  "message": "数据合法，已进入处理队列"
}
400 Response
{
  "code": 400,
  "message": "Token verification failed"
}
500 Response
{
  "message": "Internal Server Error"
}
返回结果
状态码	状态码含义	说明	数据模型
100	Continue
none	Inline
102	Processing
none	Inline
200	OK
none	Inline
400	Bad Request
none	Inline
404	Not Found
none	Inline
500	Internal Server Error
none	Inline
返回数据结构
状态码 200
名称	类型	必选	约束	中文名	说明
» status	string	true	none		none
» message	string	true	none		none
状态码 400
名称	类型	必选	约束	中文名	说明
» code	integer	true	none		错误码（如4001）
» message	string	true	none		错误说明
状态码 500
名称	类型	必选	约束	中文名	说明
» message	string	true	none		none
POST like_status
POST /api/like
本接口用于智能音箱终端向云端服务器上报设备实时状态数据。数据为收藏状态。 设备id：dev_01 验证机制 强制要求：为了确保数据来源合法，所有请求必须在 JSON 中携带 token 字段。 Token 值：smart_speaker_2026 拦截逻辑：若 token 缺失或不符，后端验证模块（Validator）将直接拦截该请求，数据不会被存储。 { "device_id": "string", "type": "string", "value": "integer", "like_status": "number" }
Body 请求参数
{
  "timestamp": "{{current_timestamp}}",
  "token": "{{current_token}}",
  "data": "Z3Vlc3Nfd2hhdF9pbl9oZXJl... (此处是收藏状态加密后的密文)",
  "sign": "d4e5f6g7..."
}
请求参数
名称	位置	类型	必选	说明
Authorization	header	string	否	所有请求必须携带此 Header，否则 网关直接拦截并返回 401 Unauthorized 或 403 Forbidden
body	body	object	是	none
» timestamp	body	integer	是	none
» token	body	string	是	none
» data	body	string	是	none
» sign	body	string	是	none
返回示例
100 Response
{}
200 Response
{
  "status": "success",
  "message": "数据合法，已进入处理队列"
}
400 Response
{
  "code": 400,
  "message": "Token verification failed"
}
500 Response
{
  "message": "Internal Server Error"
}
返回结果
状态码	状态码含义	说明	数据模型
100	Continue
none	Inline
102	Processing
none	Inline
200	OK
none	Inline
400	Bad Request
none	Inline
404	Not Found
none	Inline
500	Internal Server Error
none	Inline
返回数据结构
状态码 200
名称	类型	必选	约束	中文名	说明
» status	string	true	none		none
» message	string	true	none		none
状态码 400
名称	类型	必选	约束	中文名	说明
» code	integer	true	none		错误码（如4001）
» message	string	true	none		错误描述
状态码 500
名称	类型	必选	约束	中文名	说明
» message	string	true	none		Server Error
数据模型
