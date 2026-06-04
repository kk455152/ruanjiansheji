---
title: Web后台接口文档
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - python: Python
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"

---

# Web后台接口文档

Base URLs:

- 线上服务器：`http://8.137.165.220`
- 本地或部署环境可通过 `VITE_API_BASE_URL` 覆盖；未配置时，本地域名默认访问线上服务器，部署后默认走当前站点同源接口。

# Authentication

除登录接口外，前端请求会携带后台登录 token：

`Authorization: Bearer <admin_token>`

通用返回结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

# web后台登录/认证
## POST 账号密码登录
POST /api/admin/login

后台管理员使用用户名和密码登录，成功后返回 token 和管理员信息。

> Body 请求示例

```json
{
  "username": "admin",
  "password": "123456",
  "loginType": "password"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|username|body|string|是|登录用户名|
|password|body|string|是|登录密码|
|loginType|body|string|否|登录方式，前端固定传 password|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "admin-token",
    "adminInfo": {
      "adminId": 1,
      "username": "admin",
      "role": "super_admin",
      "roleName": "超级管理员"
    }
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 微信快捷登录
POST /api/admin/wechat-login

后台微信快捷登录，前端传入微信登录 code。

> Body 请求示例

```json
{
  "code": "demo-wechat-code"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|c|o|d|e||
|b|o|d|y||
|s|t|r|i|n|
|是|||||
|微|信|登|录|临|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "admin-token",
    "adminInfo": {
      "adminId": 1,
      "username": "admin",
      "role": "super_admin",
      "roleName": "超级管理员"
    }
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 获取当前管理员信息
GET /api/admin/profile

根据 Authorization token 获取当前登录管理员资料。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 退出登录
POST /api/admin/logout

清理后台登录态，前端调用后会移除本地 token。

> Body 请求示例

```json
{}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 超级管理员数据总览
## GET 用户数量概览
GET /api/admin/super/overview/user-count

获取总用户数、新增用户数等用户指标。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备数量概览
GET /api/admin/super/overview/device-count

获取设备总数、在线设备数等设备指标。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 销售金额概览
GET /api/admin/super/overview/sales-amount

获取销售额和订单数量统计。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 活跃度概览
GET /api/admin/super/overview/activity-rate

获取活跃用户数和活跃率。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 系统监控
GET /api/admin/super/monitor

获取 Web API、MySQL、MongoDB 等服务健康状态和异常信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 趋势与决策分析
## GET 增长趋势
GET /api/admin/super/trend/growth

获取用户、设备、销售或留存趋势。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|type|query|string|否|指标类型：user/device/sales/retention|
|dimension|query|string|否|统计维度：day/week/month/year|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员决策汇总
GET /api/admin/super/decision/summary

获取超级管理员视角的决策卡片、趋势和风险提示。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员决策汇总
GET /api/admin/market/decision/summary

获取市场分析管理员视角的决策卡片、趋势和风险提示。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 区域热力图
## GET 超级管理员销售热力图
GET /api/admin/super/region/sales-heatmap

获取各地区销售金额和订单数量。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员用户热力图
GET /api/admin/super/region/user-heatmap

获取各地区用户数和活跃用户数。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员销售热力图
GET /api/admin/market/region/sales-heatmap

获取市场视角各地区销售金额和订单数量。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员用户热力图
GET /api/admin/market/region/user-heatmap

获取市场视角各地区用户数和活跃用户数。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 用户画像
## GET 超级管理员年龄分布
GET /api/admin/super/user-profile/age-distribution

获取用户年龄段分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员地区分布
GET /api/admin/super/user-profile/region-distribution

获取用户地区分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员活跃分布
GET /api/admin/super/user-profile/activity-distribution

获取用户活跃层级分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员音乐服务分布
GET /api/admin/super/user-profile/music-service-distribution

获取用户绑定音乐平台分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员年龄分布
GET /api/admin/market/user-profile/age-distribution

获取市场视角用户年龄段分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员地区分布
GET /api/admin/market/user-profile/region-distribution

获取市场视角用户地区分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员活跃分布
GET /api/admin/market/user-profile/activity-distribution

获取市场视角用户活跃层级分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员音乐服务分布
GET /api/admin/market/user-profile/music-service-distribution

获取市场视角用户绑定音乐平台分布。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 用户价值
## GET 超级管理员普通用户统计
GET /api/admin/super/user-value/normal-users

获取普通用户数量及占比。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员高活跃用户统计
GET /api/admin/super/user-value/high-active-users

获取高活跃用户数量及占比。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员普通用户统计
GET /api/admin/market/user-value/normal-users

获取市场视角普通用户数量及占比。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场管理员高活跃用户统计
GET /api/admin/market/user-value/high-active-users

获取市场视角高活跃用户数量及占比。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 市场分析
## GET 热歌排行
GET /api/admin/market/top-songs

获取播放量、用户数和平台来源排行榜。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备购买留存
GET /api/admin/market/retention/device-purchase

获取购买设备后的用户留存数据。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 用户分群
GET /api/admin/market/segments

获取按活跃、留存、绑定和偏好建立的运营人群。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 营销洞察
GET /api/admin/market/insights

获取转化漏斗和运营建议。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 市场决策报表
GET /api/admin/market/reports

获取市场日报、周报或月报列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员决策报表
GET /api/admin/super/reports

获取超级管理员视角的决策报表列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 用户反馈
## GET 超级管理员反馈列表
GET /api/admin/super/feedback/list

分页获取用户反馈列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|page|query|integer|否|页码，默认 1|
|pageSize|query|integer|否|每页数量，默认 20|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 超级管理员反馈详情
GET /api/admin/super/feedback/detail

根据反馈 ID 获取反馈、用户和处理信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|f|e|e|d|b|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|反|馈| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 运营管理员反馈列表
GET /api/admin/operator/feedback/list

分页获取运营管理员可处理的用户反馈列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|page|query|integer|否|页码，默认 1|
|pageSize|query|integer|否|每页数量，默认 20|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 运营管理员反馈详情
GET /api/admin/operator/feedback/detail

根据反馈 ID 获取反馈详情。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|f|e|e|d|b|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|反|馈| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 处理用户反馈
POST /api/admin/operator/feedback/handle

运营管理员修改反馈处理状态和备注。

> Body 请求示例

```json
{
  "feedbackId": "FB-001",
  "status": "processed",
  "remark": "后台已处理"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|feedbackId|body|string|是|反馈 ID|
|status|body|string|是|处理状态，例如 processed|
|remark|body|string|否|处理备注|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 设备运营管理
## GET 设备列表
GET /api/admin/operator/device/list

获取设备列表、在线状态和归属用户摘要。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备运行状态
GET /api/admin/operator/device/runtime-status

根据设备 ID 获取电量、音量、网络等实时状态。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|d|e|v|i|c|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|设|备| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备分组
GET /api/admin/operator/device/groups

获取设备分组统计。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 告警列表
GET /api/admin/operator/device/alerts

获取设备离线、升级失败等告警。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备详情
GET /api/admin/operator/device/detail

根据设备 ID 获取设备详情。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|d|e|v|i|c|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|设|备| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备绑定用户
GET /api/admin/operator/device/bound-user

根据设备 ID 获取当前绑定用户信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|d|e|v|i|c|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|设|备| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备日志列表
GET /api/admin/operator/device/logs

分页获取设备日志。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|page|query|integer|否|页码，默认 1|
|pageSize|query|integer|否|每页数量，默认 20|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 设备日志详情
GET /api/admin/operator/device/log-detail

根据日志 ID 获取日志原文和追踪信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|l|o|g|I|d|
|q|u|e|r|y|
|s|t|r|i|n|
|是|||||
|日|志| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 重命名设备
POST /api/admin/operator/device/rename

修改设备展示名称。

> Body 请求示例

```json
{
  "deviceId": "1",
  "name": "卧室音箱"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|deviceId|body|string|是|设备 ID 或设备编号|
|name|body|string|是|新的设备名称|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 解绑设备
POST /api/admin/operator/device/unbind

解除设备与当前用户的绑定关系。

> Body 请求示例

```json
{
  "deviceId": "1"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|d|e|v|i|c|
|b|o|d|y||
|s|t|r|i|n|
|是|||||
|设|备| |I|D|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 设备固件
## GET 当前固件版本
GET /api/admin/operator/device/firmware-version

获取当前固件版本、最新版本和是否需要升级。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 固件包列表
GET /api/admin/operator/device/firmware-packages

获取可上传、已上传或可发布的固件包。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 固件升级任务列表
GET /api/admin/operator/device/firmware-tasks

获取固件升级任务进度。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 固件上传选项
GET /api/admin/operator/device/firmware-upload-options

获取弹窗中可选择上传的固件包。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "name": "示例数据",
        "value": 100
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 上传固件包
POST /api/admin/operator/device/firmware-upload

将选中的固件包标记为已上传。

> Body 请求示例

```json
{
  "packageId": "FW-001"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|p|a|c|k|a|
|b|o|d|y||
|s|t|r|i|n|
|是|||||
|固|件|包| |I|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 创建固件升级任务
POST /api/admin/operator/device/firmware-task

创建固件灰度或全量升级任务。

> Body 请求示例

```json
{
  "targetVersion": "1.0.5",
  "targetScope": "灰度 20%"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|targetVersion|body|string|是|目标固件版本|
|targetScope|body|string|否|升级范围，例如 灰度 20%|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 系统管理
## GET 管理员账号列表
GET /api/admin/super/users

获取后台管理员账号列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 新增管理员账号
POST /api/admin/super/users/create

创建新的后台管理员账号。

> Body 请求示例

```json
{
  "username": "operator01",
  "password": "123456",
  "role": "operator_admin",
  "realName": "运营人员",
  "phone": "13800000000",
  "email": "op@example.com",
  "jobNo": "A001"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|username|body|string|是|登录用户名|
|password|body|string|是|初始密码|
|role|body|string|是|角色：super_admin/market_admin/operator_admin/boss|
|realName|body|string|否|真实姓名|
|phone|body|string|否|手机号|
|email|body|string|否|邮箱|
|jobNo|body|string|否|工号|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 更新管理员账号
POST /api/admin/super/users/update

更新后台管理员账号资料，密码留空则不修改。

> Body 请求示例

```json
{
  "username": "operator01",
  "role": "operator_admin",
  "realName": "运营人员",
  "phone": "13800000000"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|username|body|string|是|需要更新的用户名|
|password|body|string|否|新密码|
|role|body|string|否|新角色|
|realName|body|string|否|真实姓名|
|phone|body|string|否|手机号|
|email|body|string|否|邮箱|
|jobNo|body|string|否|工号|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 删除管理员账号
POST /api/admin/super/users/delete

删除指定后台管理员账号。

> Body 请求示例

```json
{
  "username": "operator01"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|u|s|e|r|n|
|b|o|d|y||
|s|t|r|i|n|
|是|||||
|需|要|删|除|的|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 角色权限列表
GET /api/admin/super/roles

获取角色列表、已分配权限和权限目录。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 保存角色权限
POST /api/admin/super/roles/permissions

保存指定角色的权限菜单。

> Body 请求示例

```json
{
  "role": "operator_admin",
  "permissions": ["overview", "devices", "feedback"]
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|role|body|string|是|角色标识|
|permissions|body|array|是|权限 key 数组|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "result": true
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 获取系统配置
GET /api/admin/super/system/config

获取系统名称、主题、上传限制、接口超时等配置。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|systemName|body|string|否|系统名称|
|logoText|body|string|否|Logo 文案|
|defaultTheme|body|string|否|默认主题|
|uploadLimitMb|body|integer|否|上传限制 MB|
|apiTimeoutSeconds|body|integer|否|接口超时秒数|
|dataRetentionDays|body|integer|否|数据保留天数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 保存系统配置
POST /api/admin/super/system/config

保存系统名称、主题、上传限制、接口超时等配置。

> Body 请求示例

```json
{
  "systemName": "声盒 Mini 后台管理系统",
  "logoText": "Mini",
  "defaultTheme": "green",
  "uploadLimitMb": 100,
  "apiTimeoutSeconds": 15,
  "dataRetentionDays": 365
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|systemName|body|string|否|系统名称|
|logoText|body|string|否|Logo 文案|
|defaultTheme|body|string|否|默认主题|
|uploadLimitMb|body|integer|否|上传限制 MB|
|apiTimeoutSeconds|body|integer|否|接口超时秒数|
|dataRetentionDays|body|integer|否|数据保留天数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "示例ID",
    "name": "示例数据"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 系统公告列表
GET /api/admin/super/notices

获取系统公告列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## POST 创建系统公告
POST /api/admin/super/notices

创建新的系统公告。

> Body 请求示例

```json
{
  "title": "设备固件升级通知",
  "type": "notice",
  "status": "draft"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|title|body|string|是|公告标题|
|type|body|string|否|公告类型|
|status|body|string|否|公告状态：draft/published|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

## GET 审计与安全日志
GET /api/admin/super/security/logs

获取后台登录、安全事件和操作审计日志。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|无|-|-|-|该接口不需要额外参数|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "list": [
      {
        "id": "示例ID",
        "name": "示例数据"
      }
    ]
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "未登录或登录已失效"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|请求成功|
|400|Bad Request|请求参数错误|
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|接口返回数据，字段见返回示例|

# 前端实际使用接口总表

|方法|接口|说明|
|---|---|---|
|POST|$(@{Group=web后台登录/认证; Method=POST; Path=/api/admin/login; Title=账号密码登录; Desc=后台管理员使用用户名和密码登录，成功后返回 token 和管理员信息。}.Path)|账号密码登录|
|POST|$(@{Group=web后台登录/认证; Method=POST; Path=/api/admin/wechat-login; Title=微信快捷登录; Desc=后台微信快捷登录，前端传入微信登录 code。}.Path)|微信快捷登录|
|GET|$(@{Group=web后台登录/认证; Method=GET; Path=/api/admin/profile; Title=获取当前管理员信息; Desc=根据 Authorization token 获取当前登录管理员资料。}.Path)|获取当前管理员信息|
|POST|$(@{Group=web后台登录/认证; Method=POST; Path=/api/admin/logout; Title=退出登录; Desc=清理后台登录态，前端调用后会移除本地 token。}.Path)|退出登录|
|GET|$(@{Group=超级管理员数据总览; Method=GET; Path=/api/admin/super/overview/user-count; Title=用户数量概览; Desc=获取总用户数、新增用户数等用户指标。}.Path)|用户数量概览|
|GET|$(@{Group=超级管理员数据总览; Method=GET; Path=/api/admin/super/overview/device-count; Title=设备数量概览; Desc=获取设备总数、在线设备数等设备指标。}.Path)|设备数量概览|
|GET|$(@{Group=超级管理员数据总览; Method=GET; Path=/api/admin/super/overview/sales-amount; Title=销售金额概览; Desc=获取销售额和订单数量统计。}.Path)|销售金额概览|
|GET|$(@{Group=超级管理员数据总览; Method=GET; Path=/api/admin/super/overview/activity-rate; Title=活跃度概览; Desc=获取活跃用户数和活跃率。}.Path)|活跃度概览|
|GET|$(@{Group=超级管理员数据总览; Method=GET; Path=/api/admin/super/monitor; Title=系统监控; Desc=获取 Web API、MySQL、MongoDB 等服务健康状态和异常信息。}.Path)|系统监控|
|GET|$(@{Group=趋势与决策分析; Method=GET; Path=/api/admin/super/trend/growth; Title=增长趋势; Desc=获取用户、设备、销售或留存趋势。}.Path)|增长趋势|
|GET|$(@{Group=趋势与决策分析; Method=GET; Path=/api/admin/super/decision/summary; Title=超级管理员决策汇总; Desc=获取超级管理员视角的决策卡片、趋势和风险提示。}.Path)|超级管理员决策汇总|
|GET|$(@{Group=趋势与决策分析; Method=GET; Path=/api/admin/market/decision/summary; Title=市场管理员决策汇总; Desc=获取市场分析管理员视角的决策卡片、趋势和风险提示。}.Path)|市场管理员决策汇总|
|GET|$(@{Group=区域热力图; Method=GET; Path=/api/admin/super/region/sales-heatmap; Title=超级管理员销售热力图; Desc=获取各地区销售金额和订单数量。}.Path)|超级管理员销售热力图|
|GET|$(@{Group=区域热力图; Method=GET; Path=/api/admin/super/region/user-heatmap; Title=超级管理员用户热力图; Desc=获取各地区用户数和活跃用户数。}.Path)|超级管理员用户热力图|
|GET|$(@{Group=区域热力图; Method=GET; Path=/api/admin/market/region/sales-heatmap; Title=市场管理员销售热力图; Desc=获取市场视角各地区销售金额和订单数量。}.Path)|市场管理员销售热力图|
|GET|$(@{Group=区域热力图; Method=GET; Path=/api/admin/market/region/user-heatmap; Title=市场管理员用户热力图; Desc=获取市场视角各地区用户数和活跃用户数。}.Path)|市场管理员用户热力图|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/super/user-profile/age-distribution; Title=超级管理员年龄分布; Desc=获取用户年龄段分布。}.Path)|超级管理员年龄分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/super/user-profile/region-distribution; Title=超级管理员地区分布; Desc=获取用户地区分布。}.Path)|超级管理员地区分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/super/user-profile/activity-distribution; Title=超级管理员活跃分布; Desc=获取用户活跃层级分布。}.Path)|超级管理员活跃分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/super/user-profile/music-service-distribution; Title=超级管理员音乐服务分布; Desc=获取用户绑定音乐平台分布。}.Path)|超级管理员音乐服务分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/market/user-profile/age-distribution; Title=市场管理员年龄分布; Desc=获取市场视角用户年龄段分布。}.Path)|市场管理员年龄分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/market/user-profile/region-distribution; Title=市场管理员地区分布; Desc=获取市场视角用户地区分布。}.Path)|市场管理员地区分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/market/user-profile/activity-distribution; Title=市场管理员活跃分布; Desc=获取市场视角用户活跃层级分布。}.Path)|市场管理员活跃分布|
|GET|$(@{Group=用户画像; Method=GET; Path=/api/admin/market/user-profile/music-service-distribution; Title=市场管理员音乐服务分布; Desc=获取市场视角用户绑定音乐平台分布。}.Path)|市场管理员音乐服务分布|
|GET|$(@{Group=用户价值; Method=GET; Path=/api/admin/super/user-value/normal-users; Title=超级管理员普通用户统计; Desc=获取普通用户数量及占比。}.Path)|超级管理员普通用户统计|
|GET|$(@{Group=用户价值; Method=GET; Path=/api/admin/super/user-value/high-active-users; Title=超级管理员高活跃用户统计; Desc=获取高活跃用户数量及占比。}.Path)|超级管理员高活跃用户统计|
|GET|$(@{Group=用户价值; Method=GET; Path=/api/admin/market/user-value/normal-users; Title=市场管理员普通用户统计; Desc=获取市场视角普通用户数量及占比。}.Path)|市场管理员普通用户统计|
|GET|$(@{Group=用户价值; Method=GET; Path=/api/admin/market/user-value/high-active-users; Title=市场管理员高活跃用户统计; Desc=获取市场视角高活跃用户数量及占比。}.Path)|市场管理员高活跃用户统计|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/market/top-songs; Title=热歌排行; Desc=获取播放量、用户数和平台来源排行榜。}.Path)|热歌排行|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/market/retention/device-purchase; Title=设备购买留存; Desc=获取购买设备后的用户留存数据。}.Path)|设备购买留存|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/market/segments; Title=用户分群; Desc=获取按活跃、留存、绑定和偏好建立的运营人群。}.Path)|用户分群|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/market/insights; Title=营销洞察; Desc=获取转化漏斗和运营建议。}.Path)|营销洞察|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/market/reports; Title=市场决策报表; Desc=获取市场日报、周报或月报列表。}.Path)|市场决策报表|
|GET|$(@{Group=市场分析; Method=GET; Path=/api/admin/super/reports; Title=超级管理员决策报表; Desc=获取超级管理员视角的决策报表列表。}.Path)|超级管理员决策报表|
|GET|$(@{Group=用户反馈; Method=GET; Path=/api/admin/super/feedback/list; Title=超级管理员反馈列表; Desc=分页获取用户反馈列表。}.Path)|超级管理员反馈列表|
|GET|$(@{Group=用户反馈; Method=GET; Path=/api/admin/super/feedback/detail; Title=超级管理员反馈详情; Desc=根据反馈 ID 获取反馈、用户和处理信息。}.Path)|超级管理员反馈详情|
|GET|$(@{Group=用户反馈; Method=GET; Path=/api/admin/operator/feedback/list; Title=运营管理员反馈列表; Desc=分页获取运营管理员可处理的用户反馈列表。}.Path)|运营管理员反馈列表|
|GET|$(@{Group=用户反馈; Method=GET; Path=/api/admin/operator/feedback/detail; Title=运营管理员反馈详情; Desc=根据反馈 ID 获取反馈详情。}.Path)|运营管理员反馈详情|
|POST|$(@{Group=用户反馈; Method=POST; Path=/api/admin/operator/feedback/handle; Title=处理用户反馈; Desc=运营管理员修改反馈处理状态和备注。}.Path)|处理用户反馈|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/list; Title=设备列表; Desc=获取设备列表、在线状态和归属用户摘要。}.Path)|设备列表|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/runtime-status; Title=设备运行状态; Desc=根据设备 ID 获取电量、音量、网络等实时状态。}.Path)|设备运行状态|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/groups; Title=设备分组; Desc=获取设备分组统计。}.Path)|设备分组|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/alerts; Title=告警列表; Desc=获取设备离线、升级失败等告警。}.Path)|告警列表|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/detail; Title=设备详情; Desc=根据设备 ID 获取设备详情。}.Path)|设备详情|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/bound-user; Title=设备绑定用户; Desc=根据设备 ID 获取当前绑定用户信息。}.Path)|设备绑定用户|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/logs; Title=设备日志列表; Desc=分页获取设备日志。}.Path)|设备日志列表|
|GET|$(@{Group=设备运营管理; Method=GET; Path=/api/admin/operator/device/log-detail; Title=设备日志详情; Desc=根据日志 ID 获取日志原文和追踪信息。}.Path)|设备日志详情|
|POST|$(@{Group=设备运营管理; Method=POST; Path=/api/admin/operator/device/rename; Title=重命名设备; Desc=修改设备展示名称。}.Path)|重命名设备|
|POST|$(@{Group=设备运营管理; Method=POST; Path=/api/admin/operator/device/unbind; Title=解绑设备; Desc=解除设备与当前用户的绑定关系。}.Path)|解绑设备|
|GET|$(@{Group=设备固件; Method=GET; Path=/api/admin/operator/device/firmware-version; Title=当前固件版本; Desc=获取当前固件版本、最新版本和是否需要升级。}.Path)|当前固件版本|
|GET|$(@{Group=设备固件; Method=GET; Path=/api/admin/operator/device/firmware-packages; Title=固件包列表; Desc=获取可上传、已上传或可发布的固件包。}.Path)|固件包列表|
|GET|$(@{Group=设备固件; Method=GET; Path=/api/admin/operator/device/firmware-tasks; Title=固件升级任务列表; Desc=获取固件升级任务进度。}.Path)|固件升级任务列表|
|GET|$(@{Group=设备固件; Method=GET; Path=/api/admin/operator/device/firmware-upload-options; Title=固件上传选项; Desc=获取弹窗中可选择上传的固件包。}.Path)|固件上传选项|
|POST|$(@{Group=设备固件; Method=POST; Path=/api/admin/operator/device/firmware-upload; Title=上传固件包; Desc=将选中的固件包标记为已上传。}.Path)|上传固件包|
|POST|$(@{Group=设备固件; Method=POST; Path=/api/admin/operator/device/firmware-task; Title=创建固件升级任务; Desc=创建固件灰度或全量升级任务。}.Path)|创建固件升级任务|
|GET|$(@{Group=系统管理; Method=GET; Path=/api/admin/super/users; Title=管理员账号列表; Desc=获取后台管理员账号列表。}.Path)|管理员账号列表|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/users/create; Title=新增管理员账号; Desc=创建新的后台管理员账号。}.Path)|新增管理员账号|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/users/update; Title=更新管理员账号; Desc=更新后台管理员账号资料，密码留空则不修改。}.Path)|更新管理员账号|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/users/delete; Title=删除管理员账号; Desc=删除指定后台管理员账号。}.Path)|删除管理员账号|
|GET|$(@{Group=系统管理; Method=GET; Path=/api/admin/super/roles; Title=角色权限列表; Desc=获取角色列表、已分配权限和权限目录。}.Path)|角色权限列表|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/roles/permissions; Title=保存角色权限; Desc=保存指定角色的权限菜单。}.Path)|保存角色权限|
|GET|$(@{Group=系统管理; Method=GET; Path=/api/admin/super/system/config; Title=获取系统配置; Desc=获取系统名称、主题、上传限制、接口超时等配置。}.Path)|获取系统配置|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/system/config; Title=保存系统配置; Desc=保存系统名称、主题、上传限制、接口超时等配置。}.Path)|保存系统配置|
|GET|$(@{Group=系统管理; Method=GET; Path=/api/admin/super/notices; Title=系统公告列表; Desc=获取系统公告列表。}.Path)|系统公告列表|
|POST|$(@{Group=系统管理; Method=POST; Path=/api/admin/super/notices; Title=创建系统公告; Desc=创建新的系统公告。}.Path)|创建系统公告|
|GET|$(@{Group=系统管理; Method=GET; Path=/api/admin/super/security/logs; Title=审计与安全日志; Desc=获取后台登录、安全事件和操作审计日志。}.Path)|审计与安全日志|

> 以上接口来自 `index.html` 加载的 `src/App.vue` 与 `src/api.js` 实际调用路径；未在前端调用的后端兼容接口未列入本表。