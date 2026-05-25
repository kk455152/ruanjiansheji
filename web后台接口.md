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

# web管理后台/登录界面

## POST 管理员登录

POST /api/admin/login

管理员登录

> Body 请求参数

```json
{
  "username": "admin",
  "password": "123456",
  "loginType": "password"
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
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "xxxxxx",
    "adminInfo": {
      "adminId": 1,
      "username": "admin",
      "role": "super_admin",
      "roleName": "超级管理员",
      "realName": "张三",
      "jobNo": "A001",
      "position": "超级管理员"
    }
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

## POST 微信快捷登录

POST /api/admin/wechat-login

微信快捷登录

> Body 请求参数

```json
{
  "code": "wx_code_xxx",
  "state": "login_state_xxx"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» code|body|string| 是 |none|
|» state|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "微信登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "adminInfo": {
      "adminId": 2,
      "username": "market",
      "role": "market_admin",
      "roleName": "市场分析管理员",
      "realName": "李四",
      "jobNo": "M001",
      "position": "市场分析管理员",
      "wechatOpenId": "oXxx123456789"
    }
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "code 不能为空"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "账号不存在",
  "error_details": "当前微信账号未绑定任何后台管理员账号"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» access_token|string|true|none||none|
|»» token_type|string|true|none||none|
|»» expires_in|integer|true|none||none|
|»» adminInfo|object|true|none||none|
|»»» adminId|integer|true|none||none|
|»»» username|string|true|none||none|
|»»» role|string|true|none||none|
|»»» roleName|string|true|none||none|
|»»» realName|string|true|none||none|
|»»» jobNo|string|true|none||none|
|»»» position|string|true|none||none|
|»»» wechatOpenId|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取当前登录管理员信息

GET /api/admin/profile

获取当前登录管理员信息

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "adminId": 1,
    "username": "admin",
    "role": "super_admin",
    "roleName": "超级管理员",
    "realName": "张三",
    "jobNo": "A001",
    "position": "超级管理员"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "管理员账号不存在",
  "error_details": "当前登录账号不存在或已被删除"
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
|»» adminId|integer|true|none||none|
|»» username|string|true|none||none|
|»» role|string|true|none||none|
|»» roleName|string|true|none||none|
|»» realName|string|true|none||none|
|»» jobNo|string|true|none||none|
|»» position|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## POST 退出登录

POST /api/admin/logout

退出登录

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "退出登录成功",
  "data": null
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "账号已被禁用",
  "error_details": "请联系系统管理员"
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
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/数据总览

## GET 获取用户总数

GET /api/admin/super/overview/user-count

获取用户总数

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|range|query|string| 否 |today / 7d / 30d / month / all|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "userCount": 1280,
    "newUserCount": 35
  }
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看用户统计数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» userCount|integer|true|none||none|
|»» newUserCount|integer|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取设备总数

GET /api/admin/super/overview/device-count

获取设备总数

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "deviceCount": 860,
    "onlineDeviceCount": 320,
    "offlineDeviceCount": 540
  }
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看设备统计数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» deviceCount|integer|true|none||none|
|»» onlineDeviceCount|integer|true|none||none|
|»» offlineDeviceCount|integer|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取销售额

GET /api/admin/super/overview/sales-amount

获取销售额

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|startDate|query|string| 否 |none|
|endDate|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "salesAmount": 325000.5,
    "orderCount": 240
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "startDate 或 endDate 格式错误，应为 YYYY-MM-DD"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看销售额统计数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» salesAmount|number|true|none||none|
|»» orderCount|integer|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取活跃度

GET /api/admin/super/overview/activity-rate

获取活跃度

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|type|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "activeUserCount": 380,
    "totalUserCount": 1280,
    "activityRate": 0.2968
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 total、today、week、month"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看活跃度统计数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» activeUserCount|integer|true|none||none|
|»» totalUserCount|integer|true|none||none|
|»» activityRate|number|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/趋势分析

## GET 查看增长趋势

GET /api/admin/super/trend/growth

查看增长趋势

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|type|query|string| 否 |none|
|startDate|query|string| 否 |none|
|endDate|query|string| 否 |none|
|granularity|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "type": "user",
    "dimension": "day",
    "list": [
      {
        "date": "2026-05-01",
        "value": 120
      },
      {
        "date": "2026-05-02",
        "value": 150
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 user、device、sales"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看增长趋势数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» type|string|true|none||none|
|»» dimension|string|true|none||none|
|»» list|[object]|true|none||none|
|»»» date|string|true|none||none|
|»»» value|integer|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/区域热力图

## GET 查看地区销售额分布

GET /api/admin/super/region/sales-heatmap

查看地区销售额分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|level|query|string| 否 |	province / city|
|startDate|query|string| 否 |开始日期|
|endDate|query|string| 否 |结束日期|
|type|query|string| 否 |统计类型：today、week、month、year、total|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionCode": "440000",
        "regionName": "广东省",
        "salesAmount": 65000,
        "orderCount": 50
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 today、week、month、year、total"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区销售额分布数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionCode|string|false|none||none|
|»»» regionName|string|false|none||none|
|»»» salesAmount|integer|false|none||none|
|»»» orderCount|integer|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 查看地区用户分布

GET /api/admin/super/region/user-heatmap

查看地区用户分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|type|query|string| 否 |统计类型：today、week、month、year、total|
|startDate|query|string| 否 |开始日期，格式：YYYY-MM-DD|
|endDate|query|string| 否 |结束日期，格式：YYYY-MM-DD|
|level|query|string| 否 |地区层级：country、province、city|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionCode": "440000",
        "regionName": "广东省",
        "userCount": 520,
        "activeUserCount": 180
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 today、week、month、year、total"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区用户分布数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionCode|string|false|none||none|
|»»» regionName|string|false|none||none|
|»»» userCount|integer|false|none||none|
|»»» activeUserCount|integer|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/用户价值分析

## GET 获取普通用户数量

GET /api/admin/super/user-value/normal-users

获取普通用户数量

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "normalUserCount": 900
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看普通用户数量"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» normalUserCount|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取高活跃用户数量

GET /api/admin/super/user-value/high-active-users

获取高活跃用户数量

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|period|query|string| 否 |none|
|metric|query|string| 否 |none|
|threshold|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "highActiveUserCount": 260
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "period 只能为 7d、30d、90d"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看高活跃用户数量"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» highActiveUserCount|integer|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/用户画像概览

## GET 年龄分布

GET /api/admin/super/user-profile/age-distribution

年龄分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "ageRange": "18-25",
        "count": 320
      },
      {
        "ageRange": "26-35",
        "count": 460
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看年龄分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» ageRange|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 地区分布

GET /api/admin/super/user-profile/region-distribution

地区分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionName": "广东省",
        "count": 500
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionName|string|false|none||none|
|»»» count|integer|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 活跃度分布

GET /api/admin/super/user-profile/activity-distribution

活跃度分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "level": "high",
        "levelName": "高活跃",
        "count": 260
      },
      {
        "level": "normal",
        "levelName": "普通用户",
        "count": 900
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看活跃分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» level|string|true|none||none|
|»»» levelName|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 绑定软件分布

GET /api/admin/super/user-profile/music-service-distribution

绑定软件分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "service": "qq",
        "serviceName": "QQ音乐",
        "count": 300
      },
      {
        "service": "netease",
        "serviceName": "网易云音乐",
        "count": 260
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看绑定软件分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» service|string|true|none||none|
|»»» serviceName|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/超级管理员/用户反馈/评价

## GET 用户反馈列表

GET /api/admin/super/feedback/list

用户反馈列表

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |页码|
|pageSize|query|string| 否 |每页数量|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "page": 1,
    "pageSize": 10,
    "total": 3,
    "totalPages": 1,
    "list": [
      {
        "feedbackId": "FB202501310001",
        "userId": 10086,
        "nickname": "张三",
        "avatar": "https://example.com/avatar/10086.png",
        "phone": "138****8888",
        "feedbackType": "bug",
        "feedbackTypeText": "问题反馈",
        "content": "登录时偶尔提示网络异常，但网络是正常的。",
        "images": [
          "https://example.com/feedback/FB202501310001_1.png",
          "https://example.com/feedback/FB202501310001_2.png"
        ],
        "contact": "13888888888",
        "status": "pending",
        "statusText": "待处理",
        "priority": "normal",
        "priorityText": "普通",
        "handlerId": null,
        "handlerName": null,
        "replyContent": null,
        "handledAt": null,
        "createdAt": "2025-01-31 10:20:30",
        "updatedAt": "2025-01-31 10:20:30"
      },
      {
        "feedbackId": "FB202501300002",
        "userId": 10087,
        "nickname": "李四",
        "avatar": "https://example.com/avatar/10087.png",
        "phone": "139****6666",
        "feedbackType": "suggestion",
        "feedbackTypeText": "功能建议",
        "content": "建议增加订单导出功能，方便核对数据。",
        "images": [],
        "contact": "lisi@example.com",
        "status": "processing",
        "statusText": "处理中",
        "priority": "high",
        "priorityText": "高",
        "handlerId": 1,
        "handlerName": "超级管理员",
        "replyContent": null,
        "handledAt": null,
        "createdAt": "2025-01-30 16:45:10",
        "updatedAt": "2025-01-31 09:10:00"
      },
      {
        "feedbackId": "FB202501280003",
        "userId": 10088,
        "nickname": "王五",
        "avatar": "https://example.com/avatar/10088.png",
        "phone": "137****1234",
        "feedbackType": "complaint",
        "feedbackTypeText": "投诉",
        "content": "客服回复速度较慢，希望能尽快处理。",
        "images": [],
        "contact": "13712341234",
        "status": "resolved",
        "statusText": "已解决",
        "priority": "high",
        "priorityText": "高",
        "handlerId": 2,
        "handlerName": "管理员A",
        "replyContent": "您好，已为您反馈给客服主管，我们会优化处理流程。",
        "handledAt": "2025-01-29 11:30:00",
        "createdAt": "2025-01-28 14:05:20",
        "updatedAt": "2025-01-29 11:30:00"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看用户反馈列表"
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
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» page|integer|true|none||none|
|»» pageSize|integer|true|none||none|
|»» total|integer|true|none||none|
|»» totalPages|integer|true|none||none|
|»» list|[object]|true|none||none|
|»»» feedbackId|string|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» phone|string|true|none||none|
|»»» feedbackType|string|true|none||none|
|»»» feedbackTypeText|string|true|none||none|
|»»» content|string|true|none||none|
|»»» images|[string]|true|none||none|
|»»» contact|string|true|none||none|
|»»» status|string|true|none||none|
|»»» statusText|string|true|none||none|
|»»» priority|string|true|none||none|
|»»» priorityText|string|true|none||none|
|»»» handlerId|integer¦null|true|none||none|
|»»» handlerName|string¦null|true|none||none|
|»»» replyContent|string¦null|true|none||none|
|»»» handledAt|string¦null|true|none||none|
|»»» createdAt|string|true|none||none|
|»»» updatedAt|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 用户反馈详情

GET /api/admin/super/feedback/detail

用户反馈详情

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|feedbackId|query|string| 否 |反馈 ID|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "feedbackId": "FB202501310001",
    "userInfo": {
      "userId": 10086,
      "nickname": "张三",
      "avatar": "https://example.com/avatar/10086.png",
      "phone": "138****8888",
      "email": "zhangsan@example.com",
      "registerTime": "2024-08-12 09:30:20",
      "userStatus": "normal",
      "userStatusText": "正常"
    },
    "feedbackInfo": {
      "feedbackType": "bug",
      "feedbackTypeText": "问题反馈",
      "title": "登录时提示网络异常",
      "content": "登录时偶尔提示网络异常，但我的网络是正常的，希望尽快排查。",
      "images": [
        "https://example.com/feedback/FB202501310001_1.png",
        "https://example.com/feedback/FB202501310001_2.png"
      ],
      "contact": "13888888888",
      "source": "app",
      "sourceText": "移动端 App",
      "appVersion": "1.2.5",
      "deviceInfo": {
        "deviceType": "iOS",
        "deviceModel": "iPhone 14",
        "systemVersion": "iOS 17.2",
        "networkType": "WiFi"
      },
      "createdAt": "2025-01-31 10:20:30",
      "updatedAt": "2025-01-31 10:20:30"
    },
    "processInfo": {
      "status": "pending",
      "statusText": "待处理",
      "priority": "normal",
      "priorityText": "普通",
      "handlerId": null,
      "handlerName": null,
      "replyContent": null,
      "handledAt": null,
      "closedAt": null
    },
    "processLogs": [
      {
        "logId": 1,
        "action": "submit",
        "actionText": "用户提交反馈",
        "operatorId": 10086,
        "operatorName": "张三",
        "operatorType": "user",
        "remark": "用户提交反馈",
        "createdAt": "2025-01-31 10:20:30"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看用户反馈详情"
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
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» feedbackId|string|true|none||none|
|»» userInfo|object|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» phone|string|true|none||none|
|»»» email|string|true|none||none|
|»»» registerTime|string|true|none||none|
|»»» userStatus|string|true|none||none|
|»»» userStatusText|string|true|none||none|
|»» feedbackInfo|object|true|none||none|
|»»» feedbackType|string|true|none||none|
|»»» feedbackTypeText|string|true|none||none|
|»»» title|string|true|none||none|
|»»» content|string|true|none||none|
|»»» images|[string]|true|none||none|
|»»» contact|string|true|none||none|
|»»» source|string|true|none||none|
|»»» sourceText|string|true|none||none|
|»»» appVersion|string|true|none||none|
|»»» deviceInfo|object|true|none||none|
|»»»» deviceType|string|true|none||none|
|»»»» deviceModel|string|true|none||none|
|»»»» systemVersion|string|true|none||none|
|»»»» networkType|string|true|none||none|
|»»» createdAt|string|true|none||none|
|»»» updatedAt|string|true|none||none|
|»» processInfo|object|true|none||none|
|»»» status|string|true|none||none|
|»»» statusText|string|true|none||none|
|»»» priority|string|true|none||none|
|»»» priorityText|string|true|none||none|
|»»» handlerId|null|true|none||none|
|»»» handlerName|null|true|none||none|
|»»» replyContent|null|true|none||none|
|»»» handledAt|null|true|none||none|
|»»» closedAt|null|true|none||none|
|»» processLogs|[object]|true|none||none|
|»»» logId|integer|false|none||none|
|»»» action|string|false|none||none|
|»»» actionText|string|false|none||none|
|»»» operatorId|integer|false|none||none|
|»»» operatorName|string|false|none||none|
|»»» operatorType|string|false|none||none|
|»»» remark|string|false|none||none|
|»»» createdAt|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/获取热歌排行

## GET 获取热歌排行

GET /api/admin/market/top-songs

获取热歌排行

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|rankType|query|string| 否 |none|
|rangeType|query|string| 否 |none|
|page|query|string| 否 |none|
|pageSize|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "rank": 1,
        "songName": "城市夜航",
        "artist": "Luna Echo",
        "platform": "qq",
        "playCount": 128,
        "userCount": 60
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看热歌排行"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» rank|integer|false|none||none|
|»»» songName|string|false|none||none|
|»»» artist|string|false|none||none|
|»»» platform|string|false|none||none|
|»»» playCount|integer|false|none||none|
|»»» userCount|integer|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/用户画像概览 

## GET 年龄分布

GET /api/admin/market/user-profile/age-distribution

年龄分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "ageRange": "18-25",
        "count": 320
      },
      {
        "ageRange": "26-35",
        "count": 460
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看年龄分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» ageRange|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 地区分布

GET /api/admin/market/user-profile/region-distribution

地区分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionName": "广东省",
        "count": 500
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionName|string|false|none||none|
|»»» count|integer|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 活跃度分布

GET /api/admin/market/user-profile/activity-distribution

活跃度分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "level": "high",
        "levelName": "高活跃",
        "count": 260
      },
      {
        "level": "normal",
        "levelName": "普通用户",
        "count": 900
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看活跃分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» level|string|true|none||none|
|»»» levelName|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 绑定软件分布

GET /api/admin/market/user-profile/music-service-distribution

绑定软件分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "service": "qq",
        "serviceName": "QQ音乐",
        "count": 300
      },
      {
        "service": "netease",
        "serviceName": "网易云音乐",
        "count": 260
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看绑定软件分布数据"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» service|string|true|none||none|
|»»» serviceName|string|true|none||none|
|»»» count|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/区域热力图 

## GET 查看地区销售额分布

GET /api/admin/market/region/sales-heatmap

查看地区销售额分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|level|query|string| 否 |	province / city|
|startDate|query|string| 否 |开始日期|
|endDate|query|string| 否 |结束日期|
|type|query|string| 否 |统计类型：today、week、month、year、total|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionCode": "440000",
        "regionName": "广东省",
        "salesAmount": 65000,
        "orderCount": 50
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 today、week、month、year、total"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区销售额分布数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionCode|string|false|none||none|
|»»» regionName|string|false|none||none|
|»»» salesAmount|integer|false|none||none|
|»»» orderCount|integer|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 查看地区用户分布

GET /api/admin/market/region/user-heatmap

查看地区用户分布

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|type|query|string| 否 |统计类型：today、week、month、year、total|
|startDate|query|string| 否 |开始日期，格式：YYYY-MM-DD|
|endDate|query|string| 否 |结束日期，格式：YYYY-MM-DD|
|level|query|string| 否 |地区层级：country、province、city|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "regionCode": "440000",
        "regionName": "广东省",
        "userCount": 520,
        "activeUserCount": 180
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "type 只能为 today、week、month、year、total"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看地区用户分布数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» regionCode|string|false|none||none|
|»»» regionName|string|false|none||none|
|»»» userCount|integer|false|none||none|
|»»» activeUserCount|integer|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/用户价值分析 

## GET 获取普通用户数量

GET /api/admin/market/user-value/normal-users

获取普通用户数量

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "normalUserCount": 900
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看普通用户数量"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» normalUserCount|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 获取高活跃用户数量

GET /api/admin/market/user-value/high-active-users

获取高活跃用户数量

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|period|query|string| 否 |none|
|metric|query|string| 否 |none|
|threshold|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "highActiveUserCount": 260
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "period 只能为 7d、30d、90d"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看高活跃用户数量"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» highActiveUserCount|integer|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/留存分析

## GET 购买设备后是否持续使用

GET /api/admin/market/retention/device-purchase

购买设备后是否持续使用

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|startDate|query|string| 否 |开始日期|
|endDate|query|string| 否 |结束日期|
|rangeType|query|string| 否 |none|
|groupBy|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "date": "2026-05-01",
        "purchaseUserCount": 100,
        "day1RetainedCount": 62,
        "day7RetainedCount": 35,
        "day30RetainedCount": 18,
        "day1RetentionRate": 0.62,
        "day7RetentionRate": 0.35,
        "day30RetentionRate": 0.18
      }
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error_details": "rangeType=custom 时，startDate 和 endDate 不能为空"
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看设备购买留存数据"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» date|string|false|none||none|
|»»» purchaseUserCount|integer|false|none||none|
|»»» day1RetainedCount|integer|false|none||none|
|»»» day7RetainedCount|integer|false|none||none|
|»»» day30RetainedCount|integer|false|none||none|
|»»» day1RetentionRate|number|false|none||none|
|»»» day7RetentionRate|number|false|none||none|
|»»» day30RetentionRate|number|false|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/市场分析管理员/个人信息

## GET 查看个人信息

GET /api/admin/market/profile

查看个人信息

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "adminId": 2,
    "username": "market",
    "realName": "李四",
    "jobNo": "M001",
    "position": "市场分析管理员",
    "role": "market_admin",
    "phone": "13800000000",
    "email": "market@example.com"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "认证失败",
  "error_details": "Authorization 格式错误，应为 Bearer access_token"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "账号不存在",
  "error_details": "当前登录账号不存在或已被删除"
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
|»» adminId|integer|true|none||none|
|»» username|string|true|none||none|
|»» realName|string|true|none||none|
|»» jobNo|string|true|none||none|
|»» position|string|true|none||none|
|»» role|string|true|none||none|
|»» phone|string|true|none||none|
|»» email|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/普通管理员/用户反馈/评价 

## GET 用户反馈列表

GET /api/admin/operator/feedback/list

用户反馈列表

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |页码|
|pageSize|query|string| 否 |每页数量|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "page": 1,
    "pageSize": 10,
    "total": 3,
    "totalPages": 1,
    "list": [
      {
        "feedbackId": "FB202501310001",
        "userId": 10086,
        "nickname": "张三",
        "avatar": "https://example.com/avatar/10086.png",
        "phone": "138****8888",
        "feedbackType": "bug",
        "feedbackTypeText": "问题反馈",
        "content": "登录时偶尔提示网络异常，但网络是正常的。",
        "images": [
          "https://example.com/feedback/FB202501310001_1.png",
          "https://example.com/feedback/FB202501310001_2.png"
        ],
        "contact": "13888888888",
        "status": "pending",
        "statusText": "待处理",
        "priority": "normal",
        "priorityText": "普通",
        "handlerId": null,
        "handlerName": null,
        "replyContent": null,
        "handledAt": null,
        "createdAt": "2025-01-31 10:20:30",
        "updatedAt": "2025-01-31 10:20:30"
      },
      {
        "feedbackId": "FB202501300002",
        "userId": 10087,
        "nickname": "李四",
        "avatar": "https://example.com/avatar/10087.png",
        "phone": "139****6666",
        "feedbackType": "suggestion",
        "feedbackTypeText": "功能建议",
        "content": "建议增加订单导出功能，方便核对数据。",
        "images": [],
        "contact": "lisi@example.com",
        "status": "processing",
        "statusText": "处理中",
        "priority": "high",
        "priorityText": "高",
        "handlerId": 1,
        "handlerName": "超级管理员",
        "replyContent": null,
        "handledAt": null,
        "createdAt": "2025-01-30 16:45:10",
        "updatedAt": "2025-01-31 09:10:00"
      },
      {
        "feedbackId": "FB202501280003",
        "userId": 10088,
        "nickname": "王五",
        "avatar": "https://example.com/avatar/10088.png",
        "phone": "137****1234",
        "feedbackType": "complaint",
        "feedbackTypeText": "投诉",
        "content": "客服回复速度较慢，希望能尽快处理。",
        "images": [],
        "contact": "13712341234",
        "status": "resolved",
        "statusText": "已解决",
        "priority": "high",
        "priorityText": "高",
        "handlerId": 2,
        "handlerName": "管理员A",
        "replyContent": "您好，已为您反馈给客服主管，我们会优化处理流程。",
        "handledAt": "2025-01-29 11:30:00",
        "createdAt": "2025-01-28 14:05:20",
        "updatedAt": "2025-01-29 11:30:00"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看用户反馈列表"
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
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» page|integer|true|none||none|
|»» pageSize|integer|true|none||none|
|»» total|integer|true|none||none|
|»» totalPages|integer|true|none||none|
|»» list|[object]|true|none||none|
|»»» feedbackId|string|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» phone|string|true|none||none|
|»»» feedbackType|string|true|none||none|
|»»» feedbackTypeText|string|true|none||none|
|»»» content|string|true|none||none|
|»»» images|[string]|true|none||none|
|»»» contact|string|true|none||none|
|»»» status|string|true|none||none|
|»»» statusText|string|true|none||none|
|»»» priority|string|true|none||none|
|»»» priorityText|string|true|none||none|
|»»» handlerId|integer¦null|true|none||none|
|»»» handlerName|string¦null|true|none||none|
|»»» replyContent|string¦null|true|none||none|
|»»» handledAt|string¦null|true|none||none|
|»»» createdAt|string|true|none||none|
|»»» updatedAt|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 用户反馈详情

GET /api/admin/operator/feedback/detail

用户反馈详情

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|feedbackId|query|string| 否 |反馈 ID|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "feedbackId": "FB202501310001",
    "userInfo": {
      "userId": 10086,
      "nickname": "张三",
      "avatar": "https://example.com/avatar/10086.png",
      "phone": "138****8888",
      "email": "zhangsan@example.com",
      "registerTime": "2024-08-12 09:30:20",
      "userStatus": "normal",
      "userStatusText": "正常"
    },
    "feedbackInfo": {
      "feedbackType": "bug",
      "feedbackTypeText": "问题反馈",
      "title": "登录时提示网络异常",
      "content": "登录时偶尔提示网络异常，但我的网络是正常的，希望尽快排查。",
      "images": [
        "https://example.com/feedback/FB202501310001_1.png",
        "https://example.com/feedback/FB202501310001_2.png"
      ],
      "contact": "13888888888",
      "source": "app",
      "sourceText": "移动端 App",
      "appVersion": "1.2.5",
      "deviceInfo": {
        "deviceType": "iOS",
        "deviceModel": "iPhone 14",
        "systemVersion": "iOS 17.2",
        "networkType": "WiFi"
      },
      "createdAt": "2025-01-31 10:20:30",
      "updatedAt": "2025-01-31 10:20:30"
    },
    "processInfo": {
      "status": "pending",
      "statusText": "待处理",
      "priority": "normal",
      "priorityText": "普通",
      "handlerId": null,
      "handlerName": null,
      "replyContent": null,
      "handledAt": null,
      "closedAt": null
    },
    "processLogs": [
      {
        "logId": 1,
        "action": "submit",
        "actionText": "用户提交反馈",
        "operatorId": 10086,
        "operatorName": "张三",
        "operatorType": "user",
        "remark": "用户提交反馈",
        "createdAt": "2025-01-31 10:20:30"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看用户反馈详情"
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
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» feedbackId|string|true|none||none|
|»» userInfo|object|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» phone|string|true|none||none|
|»»» email|string|true|none||none|
|»»» registerTime|string|true|none||none|
|»»» userStatus|string|true|none||none|
|»»» userStatusText|string|true|none||none|
|»» feedbackInfo|object|true|none||none|
|»»» feedbackType|string|true|none||none|
|»»» feedbackTypeText|string|true|none||none|
|»»» title|string|true|none||none|
|»»» content|string|true|none||none|
|»»» images|[string]|true|none||none|
|»»» contact|string|true|none||none|
|»»» source|string|true|none||none|
|»»» sourceText|string|true|none||none|
|»»» appVersion|string|true|none||none|
|»»» deviceInfo|object|true|none||none|
|»»»» deviceType|string|true|none||none|
|»»»» deviceModel|string|true|none||none|
|»»»» systemVersion|string|true|none||none|
|»»»» networkType|string|true|none||none|
|»»» createdAt|string|true|none||none|
|»»» updatedAt|string|true|none||none|
|»» processInfo|object|true|none||none|
|»»» status|string|true|none||none|
|»»» statusText|string|true|none||none|
|»»» priority|string|true|none||none|
|»»» priorityText|string|true|none||none|
|»»» handlerId|null|true|none||none|
|»»» handlerName|null|true|none||none|
|»»» replyContent|null|true|none||none|
|»»» handledAt|null|true|none||none|
|»»» closedAt|null|true|none||none|
|»» processLogs|[object]|true|none||none|
|»»» logId|integer|false|none||none|
|»»» action|string|false|none||none|
|»»» actionText|string|false|none||none|
|»»» operatorId|integer|false|none||none|
|»»» operatorName|string|false|none||none|
|»»» operatorType|string|false|none||none|
|»»» remark|string|false|none||none|
|»»» createdAt|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/普通管理员/ 设备当前固件版本

## GET  查看设备当前固件版本

GET /api/admin/operator/device/firmware-version

 查看设备当前固件版本

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|deviceId|query|string| 否 |设备 ID|
|Authorization|header|string| 否 |none|

#### 详细说明

**deviceId**: 设备 ID

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "deviceId": "dev_001",
    "deviceName": "客厅音箱",
    "modelName": "SH-Mini A1",
    "currentVersion": "1.0.3",
    "latestVersion": "1.0.5",
    "needUpdate": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "认证失败",
  "error_details": "Authorization 格式错误，应为 Bearer access_token"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看设备固件版本"
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
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» deviceName|string|true|none||none|
|»» modelName|string|true|none||none|
|»» currentVersion|string|true|none||none|
|»» latestVersion|string|true|none||none|
|»» needUpdate|boolean|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## POST  更新设备固件

POST /api/admin/operator/device/update-firmware

 更新设备固件

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "targetVersion": "1.0.5"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» targetVersion|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "固件更新任务已创建",
  "data": {
    "taskId": 10001,
    "deviceId": "dev_001",
    "targetVersion": "1.0.5",
    "status": "pending"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "设备不存在",
  "error_details": "未找到对应设备"
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
|»» taskId|integer|true|none||none|
|»» deviceId|string|true|none||none|
|»» targetVersion|string|true|none||none|
|»» status|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/普通管理员/设备管理

## GET 设备列表

GET /api/admin/operator/device/list

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
|keyword|query|string| 否 |设备名 / 设备编号|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "total": 120,
    "list": [
      {
        "deviceId": "dev_001",
        "deviceName": "客厅音箱",
        "modelName": "SH-Mini A1",
        "ownerName": "张三",
        "online": true,
        "firmwareVersion": "1.0.3",
        "lastOnlineAt": "2026-05-20 10:00:00"
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

## GET 获取设备详情 

GET /api/admin/operator/device/detail

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
    "deviceId": "dev_001",
    "deviceName": "客厅音箱",
    "modelName": "SH-Mini A1",
    "ownerName": "张三",
    "online": true,
    "volume": 60,
    "battery": 82,
    "signalStrength": -73.59,
    "currentNetwork": "Home-5G",
    "firmwareVersion": "1.0.3",
    "createdAt": "2026-05-01 10:00:00"
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

## GET 实时设备状态

GET /api/admin/operator/device/runtime-status

实时设备状态
数据来源
MongoDB：
device_runtime

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
    "deviceId": "dev_001",
    "online": true,
    "battery": 82,
    "volume": 65,
    "currentSong": "城市夜航",
    "currentArtist": "Luna Echo",
    "lastHeartbeat": "2026-05-20 10:30:00"
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

POST /api/admin/operator/device/rename

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

## POST 解绑设备 

POST /api/admin/operator/device/unbind

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

# web管理后台/普通管理员/ 查看设备日志

## GET 查看设备日志列表

GET /api/admin/operator/device/logs

查看设备日志列表

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|deviceSn|query|string| 否 |none|
|logLevel|query|string| 否 |none|
|page|query|string| 否 |none|
|pageSize|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "total": 50,
    "list": [
      {
        "logId": 1,
        "deviceId": "dev_001",
        "deviceName": "客厅音箱",
        "logType": "online",
        "content": "设备上线",
        "createdAt": "2026-05-20 10:00:00"
      }
    ]
  }
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限操作",
  "error_details": "当前账号无权更新设备固件"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» total|integer|true|none||none|
|»» list|[object]|true|none||none|
|»»» logId|integer|false|none||none|
|»»» deviceId|string|false|none||none|
|»»» deviceName|string|false|none||none|
|»»» logType|string|false|none||none|
|»»» content|string|false|none||none|
|»»» createdAt|string|false|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

## GET 查看设备日志详情

GET /api/admin/operator/device/log-detail

查看设备日志详情

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|logId|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "logId": 900001,
    "deviceId": 10001,
    "deviceSn": "SN202501310001",
    "deviceName": "客厅智能音箱",
    "deviceType": "speaker",
    "deviceTypeText": "智能音箱",
    "deviceModel": "SPK-A1",
    "logType": "firmware",
    "logTypeText": "固件日志",
    "logLevel": "info",
    "logLevelText": "普通信息",
    "title": "固件升级任务已下发",
    "content": "设备接收到固件升级任务，目标版本：1.3.0",
    "eventCode": "FIRMWARE_UPDATE_ISSUED",
    "traceId": "TRACE202501310001",
    "taskId": "FWU202501310001",
    "firmwareVersion": "1.3.0",
    "onlineStatus": "online",
    "onlineStatusText": "在线",
    "ipAddress": "192.168.1.100",
    "networkType": "wifi",
    "location": "客厅",
    "extra": {
      "currentVersion": "1.2.3",
      "targetVersion": "1.3.0",
      "batteryLevel": 86,
      "signalStrength": -58
    },
    "stackTrace": null,
    "requestInfo": {
      "requestUrl": "/api/device/firmware/update",
      "requestMethod": "POST",
      "requestId": "REQ202501310001"
    },
    "responseInfo": {
      "responseCode": 200,
      "responseMessage": "success"
    },
    "operatorInfo": {
      "operatorId": 3001,
      "operatorName": "admin",
      "operatorType": "admin"
    },
    "createdAt": "2025-01-31 18:45:00",
    "updatedAt": "2025-01-31 18:45:00"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录",
  "error_details": "缺少 Authorization 请求头"
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "无权限访问",
  "error_details": "当前账号无权查看设备日志详情"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "日志不存在",
  "error_details": "未找到对应日志记录"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|
|403|[Forbidden](https://tools.ietf.org/html/rfc7231#section-6.5.3)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» logId|integer|true|none||none|
|»» deviceId|integer|true|none||none|
|»» deviceSn|string|true|none||none|
|»» deviceName|string|true|none||none|
|»» deviceType|string|true|none||none|
|»» deviceTypeText|string|true|none||none|
|»» deviceModel|string|true|none||none|
|»» logType|string|true|none||none|
|»» logTypeText|string|true|none||none|
|»» logLevel|string|true|none||none|
|»» logLevelText|string|true|none||none|
|»» title|string|true|none||none|
|»» content|string|true|none||none|
|»» eventCode|string|true|none||none|
|»» traceId|string|true|none||none|
|»» taskId|string|true|none||none|
|»» firmwareVersion|string|true|none||none|
|»» onlineStatus|string|true|none||none|
|»» onlineStatusText|string|true|none||none|
|»» ipAddress|string|true|none||none|
|»» networkType|string|true|none||none|
|»» location|string|true|none||none|
|»» extra|object|true|none||none|
|»»» currentVersion|string|true|none||none|
|»»» targetVersion|string|true|none||none|
|»»» batteryLevel|integer|true|none||none|
|»»» signalStrength|integer|true|none||none|
|»» stackTrace|null|true|none||none|
|»» requestInfo|object|true|none||none|
|»»» requestUrl|string|true|none||none|
|»»» requestMethod|string|true|none||none|
|»»» requestId|string|true|none||none|
|»» responseInfo|object|true|none||none|
|»»» responseCode|integer|true|none||none|
|»»» responseMessage|string|true|none||none|
|»» operatorInfo|object|true|none||none|
|»»» operatorId|integer|true|none||none|
|»»» operatorName|string|true|none||none|
|»»» operatorType|string|true|none||none|
|»» createdAt|string|true|none||none|
|»» updatedAt|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# web管理后台/普通管理员/个人信息 

## GET 查看个人信息

GET /api/operator/market/profile

查看个人信息

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "adminId": 2,
    "username": "market",
    "realName": "李四",
    "jobNo": "O001",
    "position": "市场分析管理员",
    "role": "market_admin",
    "phone": "13800000000",
    "email": "market@example.com"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "认证失败",
  "error_details": "Authorization 格式错误，应为 Bearer access_token"
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "账号不存在",
  "error_details": "当前登录账号不存在或已被删除"
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
|»» adminId|integer|true|none||none|
|»» username|string|true|none||none|
|»» realName|string|true|none||none|
|»» jobNo|string|true|none||none|
|»» position|string|true|none||none|
|»» role|string|true|none||none|
|»» phone|string|true|none||none|
|»» email|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» error_details|string|true|none||none|

# 数据模型

