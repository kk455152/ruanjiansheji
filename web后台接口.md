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

> 通用认证说明：除登录接口外，前端请求会携带后台登录 token：`Authorization: Bearer <admin_token>`。
>
> 通用返回结构：`{"code": 200, "message": "success", "data": {}}`
# 登录接口
## GET 获取机器人验证码
GET /api/admin/captcha

生成后台登录前的人机验证凭证。前端用户点击“我不是机器人”后获取 `captchaToken`，登录时连同验证标识一起提交。

### 请求参数

无

> 返回示例

```json
{
  "code": 200,
  "message": "验证码已生成",
  "data": {
    "captchaToken": "signed-captcha-token",
    "expiresIn": 300
  }
}
```

## POST 账号密码登录
POST /api/admin/login

后台管理员使用用户名、密码和机器人验证码登录，成功后返回 token 和管理员信息。

> Body 请求示例

```json
{
  "username": "admin",
  "password": "123456",
  "loginType": "password",
  "captchaToken": "signed-captcha-token",
  "captchaAnswer": "not_robot_checked"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|username|body|string|是|登录用户名|
|password|body|string|是|登录密码|
|loginType|body|string|否|登录方式，前端固定传 password|
|captchaToken|body|string|是|`GET /api/admin/captcha` 返回的人机验证 token|
|captchaAnswer|body|string|是|前端点选验证通过后提交的验证标识|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

## GET 获取当前管理员信息
GET /api/admin/profile

根据 Authorization token 获取当前登录管理员资料。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "adminId": 1,
    "username": "admin",
    "role": "super_admin",
    "roleName": "超级管理员",
    "realName": "系统管理员"
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

## POST 修改当前管理员密码
POST /api/admin/password

四种后台角色均可修改自己的登录密码。

> Body 请求示例

```json
{
  "currentPassword": "123456",
  "newPassword": "newPass123",
  "confirmPassword": "newPass123"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
|currentPassword|body|string|是|当前密码|
|newPassword|body|string|是|新密码，6 到 32 位|
|confirmPassword|body|string|是|确认新密码|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "密码已更新",
  "data": {
    "username": "admin",
    "role": "super_admin"
  }
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "修改失败",
  "error_details": "当前密码错误，请重新输入。"
}
```

### 返回结果

|状态码|含义|说明|
|---|---|---|
|200|OK|修改成功|
|400|Bad Request|参数错误或两次密码不一致|
|401|Unauthorized|未登录、token 失效或当前密码错误|
|403|Forbidden|当前角色无权限访问|

### 返回数据结构

状态码 **200**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，成功为 200|
|message|string|否|返回消息|
|data|object|否|当前管理员资料|

# 超级管理员 / 老板概览
## GET 用户数量概览
GET /api/admin/super/overview/user-count

获取总用户数、新增用户数等用户指标。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

## GET 增长趋势
GET /api/admin/super/trend/growth

获取用户、设备、销售或留存趋势。参数：type、dimension。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

# 决策看板
## GET 超级管理员决策汇总
GET /api/admin/super/decision/summary

获取超级管理员视角的决策卡片、趋势和风险提示。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

# 用户价值分析
## GET 超级管理员普通用户统计
GET /api/admin/super/user-value/normal-users

获取普通用户数量及占比。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "noticeId": "notice.20260612123000",
    "title": "设备维护通知",
    "type": "notice",
    "status": "published",
    "createdAt": "2026-06-12 12:30:00"
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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

# 反馈管理
## GET 超级管理员反馈列表
GET /api/admin/super/feedback/list

分页获取用户反馈列表。列表参数：page、pageSize。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

根据 feedbackId 获取反馈、用户和处理信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

## GET 运营管理员反馈列表
GET /api/admin/operator/feedback/list

分页获取运营管理员可处理的用户反馈列表。列表参数：page、pageSize。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

根据 feedbackId 获取反馈详情。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

# 设备管理
## GET 设备列表
GET /api/admin/operator/device/list

获取设备列表、在线状态和归属用户摘要。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

根据 deviceId 获取电量、音量、网络等实时状态。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

## GET 设备分组
GET /api/admin/operator/device/groups

获取设备分组统计。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

根据 deviceId 获取设备详情。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

## GET 设备绑定用户
GET /api/admin/operator/device/bound-user

根据 deviceId 获取当前绑定用户信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

## GET 设备日志列表
GET /api/admin/operator/device/logs

分页获取设备日志。常用参数：page、pageSize。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

根据 logId 获取日志原文和追踪信息。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

## POST 重命名设备
POST /api/admin/operator/device/rename

根据 deviceId 修改设备展示名称。

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

根据 deviceId 解除设备与当前用户的绑定关系。

> Body 请求示例

```json
{
  "deviceId": "1"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

# 管理员用户管理
## GET 管理员账号列表
GET /api/admin/super/users

获取后台管理员账号列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

# 角色权限
## GET 角色权限列表
GET /api/admin/super/roles

获取角色列表、已分配权限和权限目录。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
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

# 系统配置 / 公告 / 安全日志
## GET 获取系统配置
GET /api/admin/super/system/config

获取系统名称、主题、上传限制、接口超时等配置。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

## POST 修改系统配置（已禁用）
POST /api/admin/super/system/config

系统全局配置当前为只读，后台不再提供编辑权限。调用该接口会返回 403，不会写入 `system_config` 或本地持久化状态。

> 返回示例

```json
{
  "code": 403,
  "message": "无权限修改",
  "error_details": "系统全局配置已设为只读，不支持后台修改。"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
|401|Unauthorized|未登录或 token 失效|
|403|Forbidden|系统全局配置为只读，不允许修改|

### 返回数据结构

状态码 **403**

|名称|类型|必选|说明|
|---|---|---|---|
|code|integer|是|业务状态码，固定为 403|
|message|string|是|返回消息|
|error_details|string|否|只读原因说明|

## GET 系统公告列表
GET /api/admin/super/notices

获取系统公告列表。

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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

创建新的系统公告。公告创建后直接为已发布状态，不再提供草稿状态。

> Body 请求示例

```json
{
  "title": "设备维护通知",
  "type": "notice"
}
```

### 请求参数

|名称|位置|类型|必填|说明|
|---|---|---|---|---|
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|
|title|body|string|是|公告标题|
|type|body|string|否|公告类型|

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
|Authorization|header|string|是|Bearer {{access_token}}，登录后返回的后台访问 token|

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
