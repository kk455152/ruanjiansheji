---
title: 默认模块
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"

---

# 默认模块

Base URLs:

# Authentication

# web管理后台/web登录页

## POST 管理员登录

POST /api/admin/login

管理员登录

> Body 请求参数

```json
{
  "username": "admin",
  "password": "123456"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» username|body|string| 是 |none|
|» password|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "token": "xxxx",
  "adminInfo": {
    "adminId": 1,
    "username": "admin"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "msg": "登录失败",
  "error_details": "请求参数不完整，密码不能为空。"
}
```

> 401 Response

```json
{
  "code": 401,
  "msg": "认证失败",
  "error_details": "用户名或密码错误，请重新输入。"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» token|string|true|none||none|
|» adminInfo|object|true|none||none|
|»» adminId|integer|true|none||none|
|»» username|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» msg|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» msg|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/Dashboard 首页

## GET Dashboard 总览接口

GET /api/admin/overview

Dashboard 总览接口

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|range|query|string| 否 |以做切换按钮，大屏折线图能根据参数动态拉取 7 天或 30 天的数据|
|refresh|query|boolean| 否 |refresh=true 允许管理员手动点击大屏上的“刷新”按钮强制穿透缓存获取最新硬件状态|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "onlineDevices": 12,
  "activeUsers": 85,
  "todayPlayCount": 326,
  "totalPlayDuration": 102400
}
```

> 401 Response

```json
{
  "code": 401,
  "msg": "未授权访问",
  "error_details": "Token 已过期或无效，请重新登录。"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» onlineDevices|integer|true|none||none|
|» activeUsers|integer|true|none||none|
|» todayPlayCount|integer|true|none||none|
|» totalPlayDuration|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» msg|string|true|none||none|
|» error_details|string|true|none||none|

## GET 最近7天趋势接口

GET /api/admin/trend

最近7天趋势接口
数据来源
Daily_Stats
页面
ECharts 折线图

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|days|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "dates": [
      "05-01",
      "05-02",
      "05-03"
    ],
    "play_count": [
      120,
      150,
      180
    ],
    "active_users": [
      23,
      31,
      40
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Forbidden"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» dates|[string]|true|none||none|
|» playCounts|[integer]|true|none||none|
|» activeUsers|[integer]|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

## GET 热门歌曲排行接口

GET /api/admin/top-songs

热门歌曲排行接口
数据来源
play_history
页面
柱状图 / 排行榜

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|range|query|string| 否 |时间范围|
|platform|query|string| 否 |音乐平台|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "list": [
    {
      "songName": "城市夜航",
      "artist": "Luna Echo",
      "playCount": 128
    }
  ]
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Admin permission required"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» list|[object]|true|none||none|
|»» songName|string|false|none||none|
|»» artist|string|false|none||none|
|»» playCount|integer|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

# web管理后台/设备管理页

## GET 获取设备详情 

GET /api/device/detail

Web 设备管理页
用于获取用户绑定设备的详细信息，包括设备名称、型号、在线状态、当前音量、网络信息等。

前端进入设备详情页时调用。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|deviceId|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "deviceId": "dev_01",
    "deviceName": "客厅音箱",
    "modelName": "SH-Mini A1",
    "online": true,
    "isConnecting": false,
    "volume": 60,
    "signalStrength": -73.59,
    "bassGain": 8,
    "currentNetwork": "Home-5G",
    "volumeLimit": 80
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录",
  "data": null
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "设备不存在",
  "data": null
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» deviceName|string|true|none||none|
|»» modelName|string|true|none||none|
|»» online|boolean|true|none||none|
|»» isConnecting|boolean|true|none||none|
|»» volume|integer|true|none||none|
|»» signalStrength|number|true|none||none|
|»» bassGain|integer|true|none||none|
|»» currentNetwork|string|true|none||none|
|»» volumeLimit|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## POST 解绑设备 

POST /api/device/unbind

解绑设备

> Body 请求参数

```json
{
  "deviceId": "dev_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "设备解绑成功",
  "data": {
    "deviceId": "dev_001",
    "unbound": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录或登录已失效",
  "data": null
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "设备不存在",
  "data": {
    "deviceId": "dev_001"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» unbound|boolean|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|

## GET 设备列表

GET /GET /api/admin/device/list

设备列表
数据来源
device
user

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |none|
|page_size|query|string| 否 |none|
|status|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "list": [
    {
      "deviceId": 1,
      "deviceName": "客厅音箱",
      "owner": "张三"
    }
  ]
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Permission denied"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» list|[object]|true|none||none|
|»» deviceId|integer|false|none||none|
|»» deviceName|string|false|none||none|
|»» owner|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

## GET 实时设备状态

GET /GET /api/admin/device-runtime

实时设备状态
数据来源
MongoDB：
device_runtime

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |none|
|page_size|query|string| 否 |none|
|status|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "list": [
    {
      "deviceId": 1,
      "online": true,
      "battery": 82,
      "currentSong": "城市夜航"
    }{
      "code": 200,
      "message": "success",
      "data": {
        "total": 2,
        "list": [
          {
            "device_id": 1001,
            "device_name": "客厅音箱",
            "status": "online",
            "battery": 82,
            "volume": 65,
            "current_song": "城市夜航",
            "last_heartbeat": "2026-05-19 21:30:00"
          },
          {
            "device_id": 1002,
            "device_name": "卧室音箱",
            "status": "offline",
            "battery": 40,
            "volume": 20,
            "current_song": null,
            "last_heartbeat": "2026-05-19 20:10:00"
          }
        ]
      }
    }
  ]
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Admin permission required"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» list|[object]|true|none||none|
|»» deviceId|integer|false|none||none|
|»» online|boolean|false|none||none|
|»» battery|integer|false|none||none|
|»» currentSong|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

## POST 自定义设备名 

POST /POST /api/device/rename

管理员修改设备名称
用于修改用户设备名称。

用户在设备详情页编辑设备名称后，前端调用该接口更新设备显示名称。

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "name": "客厅音箱"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» name|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "设备名称修改成功",
  "data": {
    "deviceId": "dev_001",
    "name": "客厅音箱"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录或登录已失效",
  "data": null
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "设备不存在",
  "data": {
    "deviceId": "dev_001"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» name|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|

# web管理后台/用户管理页

## GET 用户列表

GET /GET /api/admin/user/list

用户列表
数据来源
user
device

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |none|
|page_size|query|string| 否 |none|
|keyword|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 120,
    "list": [
      {
        "user_id": 1001,
        "nickname": "张三",
        "avatar": "https://xxx.com/avatar.jpg",
        "device_count": 2,
        "play_count": 152,
        "created_at": "2026-05-01 10:20:00"
      },
      {
        "user_id": 1002,
        "nickname": "李四",
        "avatar": "https://xxx.com/avatar2.jpg",
        "device_count": 1,
        "play_count": 86,
        "created_at": "2026-05-03 12:00:00"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Admin permission required"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» list|[object]|true|none||none|
|»» userId|integer|false|none||none|
|»» nickname|string|false|none||none|
|»» deviceCount|integer|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

# web管理后台/播放统计页

## DELETE 清理 30 天前历史 

DELETE /api/play-history/clear-old

清理 30 天前历史
用于清理当前用户指定天数之前的播放历史。

用户在播放历史页面点击“清理 30 天前历史”后，前端调用该接口删除旧播放记录。默认清理 30 天前的数据，也可以通过 days 指定清理范围。

> Body 请求参数

```json
{
  "days": 30
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» days|body|integer| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "30 天前播放历史清理成功",
  "data": {
    "days": 30,
    "deletedCount": 18
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录或登录已失效",
  "data": null
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» days|integer|true|none||none|
|»» deletedCount|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## GET 全平台播放历史

GET /GET /api/admin/play-history

全平台播放历史
数据来源
play_history
user

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |none|
|page_size|query|string| 否 |none|
|platform|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1280,
    "list": [
      {
        "play_id": 1,
        "song_name": "城市夜航",
        "artist": "Luna Echo",
        "platform": "qq",
        "nickname": "张三",
        "device_name": "客厅音箱",
        "played_at": "2026-05-19 21:30:00",
        "duration": 245
      },
      {
        "play_id": 2,
        "song_name": "雨后电台",
        "artist": "阿青",
        "platform": "netease",
        "nickname": "李四",
        "device_name": "卧室音箱",
        "played_at": "2026-05-19 20:10:00",
        "duration": 198
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "Admin permission required"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» list|[object]|true|none||none|
|»» songName|string|false|none||none|
|»» user|string|false|none||none|
|»» playedAt|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|

# web管理后台/音乐服务管理页

## GET 获取已绑定服务 

GET /api/music-service/list

获取已绑定服务
用户进入“音乐服务管理”页面后，前端调用该接口，展示 QQ 音乐、网易云音乐等平台的绑定状态、账号名称和同步状态

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取已绑定音乐服务成功",
  "data": {
    "services": [
      {
        "service": "qq",
        "serviceName": "QQ 音乐",
        "bound": true,
        "accountName": "用户昵称",
        "syncStatus": "synced"
      },
      {
        "service": "netease",
        "serviceName": "网易云音乐",
        "bound": true,
        "accountName": "网易云用户",
        "syncStatus": "syncing"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录或登录已失效",
  "data": null
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» services|[object]|true|none||none|
|»»» service|string|true|none||none|
|»»» serviceName|string|true|none||none|
|»»» bound|boolean|true|none||none|
|»»» accountName|string|true|none||none|
|»»» syncStatus|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## POST 绑定音乐服务 

POST /api/music-service/bind

后台绑定测试账号
用于绑定第三方音乐平台账号（如 QQ 音乐、网易云音乐等）
用户完成第三方 OAuth 授权后，客户端将授权返回的 authCode 提交到本接口，后端完成账号绑定并保存授权信息。

> Body 请求参数

```json
{
  "service": "qq",
  "authCode": "第三方授权code"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» service|body|string| 是 |none|
|» authCode|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "音乐服务绑定成功",
  "data": {
    "service": "qq",
    "bound": true,
    "accountName": "用户昵称"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "用户未登录或登录已失效",
  "data": null
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "不支持的音乐平台",
  "data": {
    "service": "test"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» service|string|true|none||none|
|»» bound|boolean|true|none||none|
|»» accountName|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» service|string|true|none||none|

# web管理后台/一起听管理

## GET 获取房间详情 

GET /api/listen-room/detail

Web 用途

后台查看：

房间数量
房间成员
在线状态

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|roomId|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取房间详情成功",
  "data": {
    "roomId": "room_001",
    "roomName": "雨后电台",
    "status": "active",
    "syncDelay": 0.2,
    "source": "netease",
    "currentSong": {
      "songId": "song_001",
      "songName": "城市夜航",
      "artist": "Luna Echo",
      "coverUrl": "https://cdn.musicplayer.cn/song_001.jpg",
      "isPlaying": true
    },
    "currentUser": {
      "userId": 10001,
      "role": "owner",
      "isHost": true
    },
    "members": [
      {
        "userId": 10001,
        "nickname": "我",
        "avatar": "https://cdn.musicplayer.cn/avatar/me.jpg",
        "role": "owner",
        "online": true
      },
      {
        "userId": 10002,
        "nickname": "阿青",
        "avatar": "https://cdn.musicplayer.cn/avatar/u002.jpg",
        "role": "member",
        "online": true
      },
      {
        "userId": 10003,
        "nickname": "小北",
        "avatar": "https://cdn.musicplayer.cn/avatar/u003.jpg",
        "role": "member",
        "online": true
      }
    ]
  }
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "房间不存在",
  "data": {
    "roomId": "room_001"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|
|»» roomName|string|true|none||none|
|»» status|string|true|none||none|
|»» syncDelay|number|true|none||none|
|»» source|string|true|none||none|
|»» currentSong|object|true|none||none|
|»»» songId|string|true|none||none|
|»»» songName|string|true|none||none|
|»»» artist|string|true|none||none|
|»»» coverUrl|string|true|none||none|
|»»» isPlaying|boolean|true|none||none|
|»» currentUser|object|true|none||none|
|»»» userId|integer|true|none||none|
|»»» role|string|true|none||none|
|»»» isHost|boolean|true|none||none|
|»» members|[object]|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» role|string|true|none||none|
|»»» online|boolean|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|

# 数据模型

