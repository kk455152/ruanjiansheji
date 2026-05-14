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

# 首页

## POST 微信授权并继续

POST /api/auth/wechat-login

微信授权登录
用户首次进入小程序时，通过微信小程序登录能力完成身份认证。
前端调用 wx.login() 获取临时登录凭证 code，并上传用户加密信息 encryptedData 与解密向量 iv。
后端校验微信身份后：

自动创建或登录用户账号
返回系统登录 Token
返回用户基础信息
返回当前用户是否已绑定智能音箱设备

该接口用于：

小程序首次登录
Token 失效后的重新登录
自动同步用户基础信息

> Body 请求参数

```json
{
  "code": "微信登录code",
  "encryptedData": "用户加密数据",
  "iv": "解密向量"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|body|body|object| 是 |none|
|» code|body|string| 是 |none|
|» encryptedData|body|string| 是 |none|
|» iv|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "token": "登录凭证",
  "userId": 10001,
  "nickname": "用户昵称",
  "avatar": "头像地址",
  "hasDevice": true
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "data": {
    "field": "code",
    "reason": "微信登录 code 不能为空"
  }
}
```

> 403 Response

```json
{
  "code": 403,
  "message": "用户未授权微信登录",
  "data": null
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
|» token|string|true|none||none|
|» userId|integer|true|none||none|
|» nickname|string|true|none||none|
|» avatar|string|true|none||none|
|» hasDevice|boolean|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|
|»» reason|string|true|none||none|

状态码 **403**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## GET 获取首页信息

GET /api/home/overview

获取首页信息
用于获取智能音箱小程序首页展示信息。
用户进入首页后，前端调用该接口，获取当前绑定设备状态、正在播放的歌曲信息以及播放历史数量。

该接口主要用于：

首页初始化加载
刷新当前播放状态
获取设备在线状态
获取设备电量信息
获取当前歌曲信息
获取播放历史统计

首页展示内容包括：

当前绑定设备
设备在线状态
设备电量
正在播放歌曲
音乐来源（QQ 音乐 / 网易云音乐）
当前播放状态
最近播放历史数量

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "device": {
    "deviceId": "dev_001",
    "name": "客厅音箱",
    "model": "SH-Mini A1",
    "online": true,
    "battery": 82
  },
  "playing": {
    "songId": "song_001",
    "songName": "城市夜航",
    "artist": "Luna Echo",
    "source": "netease",
    "isPlaying": true
  },
  "historyCount": 48
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
  "message": "当前用户未绑定设备",
  "data": {
    "hasDevice": false
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
|» device|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» name|string|true|none||none|
|»» model|string|true|none||none|
|»» online|boolean|true|none||none|
|»» battery|integer|true|none||none|
|» playing|object|true|none||none|
|»» songId|string|true|none||none|
|»» songName|string|true|none||none|
|»» artist|string|true|none||none|
|»» source|string|true|none||none|
|»» isPlaying|boolean|true|none||none|
|» historyCount|integer|true|none||none|

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
|»» hasDevice|boolean|true|none||none|

## POST 播放控制

POST /api/player/control

播放控制
action 可选：
play
pause
previous
next
用于控制智能音箱的音乐播放状态。

用户在首页播放器区域点击：

播放
暂停
上一首
下一首

时，前端调用该接口向指定设备发送播放控制指令。

该接口会：

校验用户登录状态
校验用户设备权限
检查设备在线状态
向设备发送播放控制命令
返回当前播放状态

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "action": "pause",
  "source": "netease"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» action|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "播放控制成功",
  "data": {
    "deviceId": "dev_001",
    "action": "pause",
    "isPlaying": false,
    "currentSong": {
      "songId": "song_001",
      "songName": "城市夜航",
      "artist": "Luna Echo"
    }
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "无效的播放控制动作",
  "data": {
    "action": "stop"
  }
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
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» action|string|true|none||none|
|»» isPlaying|boolean|true|none||none|
|»» currentSong|object|true|none||none|
|»»» songId|string|true|none||none|
|»»» songName|string|true|none||none|
|»»» artist|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» action|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|

## POST 调节音量

POST /api/player/volume

调节音量
用于调节智能音箱当前播放音量。

用户拖动首页播放器音量滑块后，前端调用该接口向指定设备发送音量调整指令。

该接口会：

校验用户登录状态
校验用户设备权限
检查设备在线状态
修改设备当前音量
返回最新音量状态

音量范围：

0 - 100

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "volume": 60,
  "source": "netease"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» volume|body|integer| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "音量设置成功",
  "data": {
    "deviceId": "dev_001",
    "volume": 60,
    "isMuted": false
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

# 听歌好友模块/听歌好友首页

## GET 获取听歌好友首页

GET /api/friends/listening

获取听歌好友首页
用于获取“听歌好友”页面的首页数据。
用户进入好友页面时，前端调用该接口，获取当前一起听房间信息、房间成员、最近听歌好友列表以及好友当前听歌状态。

该接口主要用于：

显示一起听进行中的房间
显示当前房间人数和成员
显示最近听歌好友
显示好友分享歌曲或正在听歌状态

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "room": {
    "roomId": "room_001",
    "roomName": "雨后电台",
    "songName": "城市夜航",
    "memberCount": 3,
    "members": ["我", "阿青", "小北"]
  },
  "recentFriends": [
    {
      "friendId": "u_002",
      "name": "阿青",
      "status": "刚分享了《晨光》"
    },
    {
      "friendId": "u_003",
      "name": "小北",
      "status": "正在听轻音乐歌单"
    }
  ]
}
```

> 404 Response

```json
{
  "code": 200,
  "message": "获取听歌好友首页成功",
  "data": {
    "room": null,
    "recentFriends": []
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
|» room|object|true|none||none|
|»» roomId|string|true|none||none|
|»» roomName|string|true|none||none|
|»» songName|string|true|none||none|
|»» memberCount|integer|true|none||none|
|»» members|[string]|true|none||none|
|» recentFriends|[object]|true|none||none|
|»» friendId|string|true|none||none|
|»» name|string|true|none||none|
|»» status|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» room|null|true|none||none|
|»» recentFriends|[string]|true|none||none|

## GET 搜索好友

GET /api/friends/search

搜索好友
用于搜索当前用户的听歌好友。

用户在“听歌好友”页面输入好友昵称关键词后，前端调用该接口获取匹配的好友列表。

该接口主要用于：

搜索好友昵称
搜索最近听歌好友
查找一起听好友
获取好友当前听歌状态

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|keyword|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "搜索好友成功",
  "data": {
    "total": 2,
    "page": 1,
    "pageSize": 10,
    "list": [
      {
        "friendId": "u_002",
        "nickname": "阿青",
        "avatar": "https://cdn.musicplayer.cn/avatar/u002.jpg",
        "status": "刚分享了《晨光》",
        "isOnline": true
      },
      {
        "friendId": "u_003",
        "nickname": "阿青同学",
        "avatar": "https://cdn.musicplayer.cn/avatar/u003.jpg",
        "status": "正在听轻音乐歌单",
        "isOnline": false
      }
    ]
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» total|integer|true|none||none|
|»» page|integer|true|none||none|
|»» pageSize|integer|true|none||none|
|»» list|[object]|true|none||none|
|»»» friendId|string|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»»» status|string|true|none||none|
|»»» isOnline|boolean|true|none||none|

## POST 创建一起听房间

POST /api/listen-room/create

创建一起听房间
用于创建一个“一起听歌”房间。

用户在“听歌好友”页面点击“一起听歌”后，前端调用该接口，根据当前播放歌曲和当前设备创建一起听房间。创建成功后，当前用户默认为房主或主控成员，好友可以通过分享链接或房间 ID 加入一起听。

该接口主要用于：

创建一起听房间
绑定当前播放歌曲
绑定播放设备
设置当前用户为房主
返回房间 ID，供后续加入、分享、查看房间详情使用

> Body 请求参数

```json
{
  "songId": "song_001",
  "deviceId": "dev_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» songId|body|string| 是 |none|
|» deviceId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "一起听房间创建成功",
  "data": {
    "roomId": "room_001",
    "roomName": "城市夜航一起听",
    "songId": "song_001",
    "songName": "城市夜航",
    "deviceId": "dev_001",
    "ownerUserId": 10001,
    "memberCount": 1,
    "role": "owner",
    "status": "active"
  }
}
```

> 408 Response

```json
{
  "code": 408,
  "message": "设备当前离线，无法创建一起听房间",
  "data": {
    "deviceId": "dev_001",
    "online": false
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|408|[Request Timeout](https://tools.ietf.org/html/rfc7231#section-6.5.7)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|
|»» roomName|string|true|none||none|
|»» songId|string|true|none||none|
|»» songName|string|true|none||none|
|»» deviceId|string|true|none||none|
|»» ownerUserId|integer|true|none||none|
|»» memberCount|integer|true|none||none|
|»» role|string|true|none||none|
|»» status|string|true|none||none|

状态码 **408**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» online|boolean|true|none||none|

## POST 加入一起听房间

POST /api/listen-room/join

加入一起听房间

> Body 请求参数

```json
{
  "roomId": "room_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» roomId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "加入一起听房间成功",
  "data": {
    "roomId": "room_001",
    "roomName": "雨后电台",
    "songId": "song_001",
    "songName": "城市夜航",
    "memberCount": 4,
    "members": [
      {
        "userId": 10001,
        "nickname": "我",
        "role": "owner"
      },
      {
        "userId": 10002,
        "nickname": "阿青",
        "role": "member"
      },
      {
        "userId": 10003,
        "nickname": "小北",
        "role": "member"
      },
      {
        "userId": 10004,
        "nickname": "当前用户",
        "role": "member"
      }
    ],
    "syncDelay": 0.2,
    "status": "active"
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
|»» songId|string|true|none||none|
|»» songName|string|true|none||none|
|»» memberCount|integer|true|none||none|
|»» members|[object]|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» role|string|true|none||none|
|»» syncDelay|number|true|none||none|
|»» status|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|

# 听歌好友模块/一起听歌房间页

## GET 获取房间详情

GET /api/listen-room/detail

获取房间详情
用于获取指定一起听房间的详细信息。

用户进入“一起听歌”房间页面后，前端调用该接口获取房间当前状态，包括当前播放歌曲、音乐来源、同步延迟、房间成员、成员在线状态和当前用户在房间中的角色。

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

## POST 发送评论

POST /api/listen-room/comment

发送评论

> Body 请求参数

```json
{
  "roomId": "room_001",
  "content": "这首歌很好听"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» roomId|body|string| 是 |none|
|» content|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "评论发送成功",
  "data": {
    "commentId": "comment_001",
    "roomId": "room_001",
    "content": "这首歌很好听",
    "sender": {
      "userId": 10001,
      "nickname": "我",
      "avatar": "https://cdn.musicplayer.cn/avatar/me.jpg"
    },
    "createdAt": "2026-05-08 21:30:00"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "评论内容不能为空",
  "data": {
    "field": "content"
  }
}
```

> 410 Response

```json
{
  "code": 410,
  "message": "一起听房间已结束，无法发送评论",
  "data": {
    "roomId": "room_001",
    "status": "ended"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|410|[Gone](https://tools.ietf.org/html/rfc7231#section-6.5.9)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» commentId|string|true|none||none|
|»» roomId|string|true|none||none|
|»» content|string|true|none||none|
|»» sender|object|true|none||none|
|»»» userId|integer|true|none||none|
|»»» nickname|string|true|none||none|
|»»» avatar|string|true|none||none|
|»» createdAt|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|

状态码 **410**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|
|»» status|string|true|none||none|

## POST 退出一起听

POST /api/listen-room/leave

退出一起听
用于退出当前一起听歌房间。

用户在一起听页面点击“退出一起听”后，前端调用该接口，将当前用户从房间成员列表中移除。

退出成功后：

当前用户离开房间
房间成员数量减少
若当前用户为房主，则自动转移房主或关闭房间
返回退出后的房间状态

该接口主要用于：

主动退出一起听
结束当前听歌同步
更新房间成员状态

> Body 请求参数

```json
{
  "roomId": "room_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» roomId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "退出一起听成功",
  "data": {
    "roomId": "room_001",
    "leftUserId": 10001,
    "memberCount": 2,
    "roomStatus": "active",
    "isRoomClosed": false
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "房间 ID 不能为空",
  "data": {
    "field": "roomId"
  }
}
```

> 410 Response

```json
{
  "code": 410,
  "message": "一起听房间已结束",
  "data": {
    "roomId": "room_001",
    "status": "ended"
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|410|[Gone](https://tools.ietf.org/html/rfc7231#section-6.5.9)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|
|»» leftUserId|integer|true|none||none|
|»» memberCount|integer|true|none||none|
|»» roomStatus|string|true|none||none|
|»» isRoomClosed|boolean|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|

状态码 **410**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» roomId|string|true|none||none|
|»» status|string|true|none||none|

# 听歌好友模块/分享歌曲页

## POST 生成分享链接

POST /api/share/song-link

生成分享链接
用于生成歌曲或一起听房间的分享链接。

用户在“分享歌曲”页面点击“复制链接”或“分享歌曲”时，前端调用该接口生成可分享链接。好友打开链接后，可以查看歌曲信息，或进入对应的一起听房间。

> Body 请求参数

```json
{
  "songId": "song_001",
  "roomId": "room_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» songId|body|string| 是 |none|
|» roomId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "分享链接生成成功",
  "data": {
    "shareId": "share_001",
    "songId": "song_001",
    "roomId": "room_001",
    "shareUrl": "https://api.musicplayer.cn/share/share_001",
    "expireAt": "2026-05-16 23:59:59"
  }
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "歌曲不存在",
  "data": {
    "songId": "song_001"
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
|»» shareId|string|true|none||none|
|»» songId|string|true|none||none|
|»» roomId|string|true|none||none|
|»» shareUrl|string|true|none||none|
|»» expireAt|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» songId|string|true|none||none|

## POST 生成分享卡片

POST /api/share/song-card

生成分享卡片
用于生成歌曲或一起听房间的分享卡片。

用户在“分享歌曲”页面点击“生成分享卡片”后，前端调用该接口，后端根据歌曲信息、封面、房间信息等内容生成可分享图片卡片。

生成的分享卡片可用于：

微信好友分享
微信朋友圈分享
保存到本地相册
一起听邀请卡片

> Body 请求参数

```json
{
  "songId": "song_001",
  "roomId": "room_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» songId|body|string| 是 |none|
|» roomId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "分享卡片生成成功",
  "data": {
    "cardId": "card_001",
    "songId": "song_001",
    "roomId": "room_001",
    "imageUrl": "https://cdn.musicplayer.cn/share/card_001.png",
    "previewUrl": "https://cdn.musicplayer.cn/share/preview/card_001.png",
    "expireAt": "2026-05-16 23:59:59"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "歌曲 ID 不能为空",
  "data": {
    "field": "songId"
  }
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "歌曲不存在",
  "data": {
    "songId": "song_001"
  }
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
|»» cardId|string|true|none||none|
|»» songId|string|true|none||none|
|»» roomId|string|true|none||none|
|»» imageUrl|string|true|none||none|
|»» previewUrl|string|true|none||none|
|»» expireAt|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» songId|string|true|none||none|

# 听歌数据模块/听歌数据首页

## GET 获取听歌数据总结

GET /api/listening-data/summary

获取听歌数据总结
用于获取用户当前周期的听歌数据总结。

用户进入“听歌总结”页面后，前端调用该接口获取当前用户的听歌统计，包括听歌时长、歌曲数量、偏好风格、常听时间段以及听歌排名等信息。

该接口主要用于：

周报总结
月度总结
年度总结
听歌卡片展示
分享长图生成前的数据获取

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|period|query|string| 否 |统计周期：week / month / year|
|value|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "minutes": 428,
    "songCount": 96,
    "favoriteStyle": "华语流行",
    "activeTime": "21:00-23:00",
    "topPercent": "Top 12%"
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
  "message": "当前周期暂无听歌数据",
  "data": {
    "period": "week",
    "value": 19
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
|» data|object|true|none||none|
|»» minutes|integer|true|none||none|
|»» songCount|integer|true|none||none|
|»» favoriteStyle|string|true|none||none|
|»» activeTime|string|true|none||none|
|»» topPercent|string|true|none||none|

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
|»» period|string|true|none||none|
|»» value|integer|true|none||none|

## GET 获取歌曲信息

GET /api/song-info

获取歌曲信息
用于根据歌曲 ID 获取歌曲详细信息。

用户在播放历史、歌曲操作页、分享歌曲页或正在播放区域点击歌曲时，前端调用该接口获取歌曲名称、专辑、歌手、封面、时长和音乐来源等信息。

该接口主要用于：

展示歌曲详情
播放历史歌曲详情页
分享歌曲前获取歌曲信息
一起听房间展示当前歌曲

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|songId|query|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "data": {
    "songId": "1491830535",
    "name": "？？",
    "album": "？？",
    "artistText": "茶北°Ciper",
    "artists": ["茶北°Ciper"],
    "coverUrl": "https://p1.music.126.net/wALGdwxVNZrCY1n8-7oKaw==/109951165430592176.jpg",
    "durationMs": 262060,
    "durationSeconds": 262,
    "source": "netease"
  }
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "歌曲不存在",
  "data": {
    "songId": "1491830535"
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
|» data|object|true|none||none|
|»» songId|string|true|none||none|
|»» name|string|true|none||none|
|»» album|string|true|none||none|
|»» artistText|string|true|none||none|
|»» artists|[string]|true|none||none|
|»» coverUrl|string|true|none||none|
|»» durationMs|integer|true|none||none|
|»» durationSeconds|integer|true|none||none|
|»» source|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» songId|string|true|none||none|

# 听歌数据模块/播放历史页

## GET 获取播放历史

GET /api/play-history/list

获取播放历史
用户进入“播放历史”页面后，前端调用该接口获取历史播放记录。支持按音乐来源筛选、关键词搜索和分页查询。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|source|query|string| 否 |none|
|keyword|query|string| 否 |none|
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
        "historyId": 1,
        "songName": "城市夜航",
        "artist": "Luna Echo",
        "source": "netease",
        "playedAt": "2026-05-08 22:14",
        "coverUrl": "https://xxx.jpg"
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
|» data|object|true|none||none|
|»» list|[object]|true|none||none|
|»»» historyId|integer|false|none||none|
|»»» songName|string|false|none||none|
|»»» artist|string|false|none||none|
|»»» source|string|false|none||none|
|»»» playedAt|string|false|none||none|
|»»» coverUrl|string|false|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

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

## DELETE 删除单条历史

DELETE /api/play-history/delete

删除单条历史
用于删除当前用户的一条播放历史记录。

用户在播放历史页面长按或点击“删除”按钮后，前端调用该接口删除指定历史记录。

该操作仅删除当前用户的播放历史，不影响歌曲数据本身。

> Body 请求参数

```json
{
  "historyId": "his_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» historyId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "播放历史删除成功",
  "data": {
    "historyId": "his_001"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "历史记录 ID 不能为空",
  "data": {
    "field": "historyId"
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
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» historyId|string|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

# 听歌数据模块/歌曲操作页

## POST 在音箱上播放歌曲

POST /api/player/play-song

在音箱上播放歌曲

> Body 请求参数

```json
{
  "deviceId": "dev_01",
  "songId": "1491830535"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» songId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "歌曲播放成功",
  "data": {
    "deviceId": "dev_01",
    "songId": "1491830535",
    "songName": "？",
    "artist": "茶北Ciper",
    "source": "netease",
    "isPlaying": true,
    "playTime": 0
  }
}
```

> 404 Response

```json
{
  "code": 0,
  "message": "string",
  "data": {
    "deviceId": "string"
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
|»» deviceId|string|true|none||none|
|»» songId|string|true|none||none|
|»» songName|string|true|none||none|
|»» artist|string|true|none||none|
|»» source|string|true|none||none|
|»» isPlaying|boolean|true|none||none|
|»» playTime|integer|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|

## POST 加入下一首播放

POST /api/player/add-next

加入下一首播放
用于把指定歌曲加入智能音箱的下一首播放队列。

用户在“歌曲操作页”点击“加入下一首播放”后，前端调用该接口，将歌曲添加到当前设备播放队列的下一首位置。该接口不会立即打断当前播放歌曲。

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "songId": "song_001"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» songId|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "已加入下一首播放",
  "data": {
    "deviceId": "dev_001",
    "songId": "song_001",
    "songName": "城市夜航",
    "artist": "Luna Echo",
    "queuePosition": 1
  }
}
```

> 409 Response

```json
{
  "code": 409,
  "message": "该歌曲已在下一首播放队列中",
  "data": {
    "deviceId": "dev_001",
    "songId": "song_001",
    "queuePosition": 1
  }
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|
|409|[Conflict](https://tools.ietf.org/html/rfc7231#section-6.5.8)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» songId|string|true|none||none|
|»» songName|string|true|none||none|
|»» artist|string|true|none||none|
|»» queuePosition|integer|true|none||none|

状态码 **409**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» songId|string|true|none||none|
|»» queuePosition|integer|true|none||none|

# 听歌数据模块/个人听歌总结页

## GET 获取个人总结

GET /api/listening-data/weekly-report

获取个人总结
用于获取用户的个人听歌周总结详情。

用户进入“个人听歌总结”页面后，前端调用该接口获取本周听歌报告，包括周数、排名、听歌时长、与上周对比、最常听艺人、高频歌单等内容。

该接口主要用于：

展示个人听歌周报
生成个人总结长图
展示最常听艺人
展示高频歌单
展示本周听歌分析文案

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|year|query|string| 否 |none|
|week|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取个人听歌总结成功",
  "data": {
    "year": 2026,
    "week": 19,
    "rank": "Top 12%",
    "minutes": 428,
    "compareLastWeek": "比上周多听 23%",
    "summaryText": "夜间播放和轻音乐占比明显上升。",
    "topArtist": {
      "artistName": "Luna Echo",
      "songCount": 12
    },
    "topPlaylist": {
      "playlistName": "夜间专注",
      "playCount": 18
    }
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数错误",
  "data": {
    "field": "week",
    "reason": "week 必须是 1-53 之间的整数"
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
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|none|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» year|integer|true|none||none|
|»» week|integer|true|none||none|
|»» rank|string|true|none||none|
|»» minutes|integer|true|none||none|
|»» compareLastWeek|string|true|none||none|
|»» summaryText|string|true|none||none|
|»» topArtist|object|true|none||none|
|»»» artistName|string|true|none||none|
|»»» songCount|integer|true|none||none|
|»» topPlaylist|object|true|none||none|
|»»» playlistName|string|true|none||none|
|»»» playCount|integer|true|none||none|

状态码 **400**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» field|string|true|none||none|
|»» reason|string|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## POST 生成总结长图

POST /api/listening-data/generate-card

生成总结长图
用户在“个人听歌总结”页面点击“保存总结长图”或“生成总结长图”时，前端调用该接口。后端根据用户指定周期的听歌数据生成图片，并返回图片地址，前端可用于预览、保存到相册或分享。

> Body 请求参数

```json
{
  "year": 2026,
  "week": 19,
  "cardType": "weekly"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» year|body|integer| 是 |none|
|» week|body|integer| 是 |none|
|» cardType|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "总结长图生成成功",
  "data": {
    "imageUrl": "https://xxx.com/report/week19.png",
    "year": 2026,
    "week": 19,
    "cardType": "weekly"
  }
}
```

> 404 Response

```json
{
  "code": 404,
  "message": "当前周期暂无听歌数据，无法生成总结长图",
  "data": {
    "year": 2026,
    "week": 19
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
|» imageUrl|string|true|none||none|

状态码 **404**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» year|integer|true|none||none|
|»» week|integer|true|none||none|

# 设备管理模块/设备管理首页

## GET 获取设备详情

GET /api/device/detail

获取设备详情
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

## GET 获取设备列表

GET /device/list

1. 功能概述
本接口用于查询当前登录用户名下已绑定的所有智能音箱。支持展示设备的基础信息、自定义名称及当前实时状态。

2. 核心业务逻辑（对齐 PD 物理模型）

多表关联查询：后端（C同学）需通过 Authorization 提取 user_id。

查询路径：

首先在 user_device_binding 表中通过 user_id 筛选出该用户拥有的所有 device_id。

接着关联 device 表获取对应设备的 device_number、model_name 等出厂属性。

状态读取：status 字段应结合硬件上报的最新心跳包进行逻辑判断。

3. 安全与鉴权

认证要求：本接口为受保护资源。必须在 Headers 中携带有效的 Bearer Token。

越权防护：后端必须强制校验绑定关系。严禁通过修改请求参数查看非本人名下的设备。

4. 响应字段详解

device_number: 硬件唯一标识符，对应 PD 图中的 device 主表字段。

custom_device_name: 用户在绑定时或后期设置的个性化昵称。

status:

1: 设备在线且正常连接。

0: 设备离线。
补充：关于 is_primary：标注“该字段由后端逻辑自动计算，前端仅做展示，不可手动修改”
关于 last_active：标注“该时间对应 MySQL 表中的最后心跳更新时间”

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "msg": "成功",
  "data": [
    {
      "device_id": "@integer(1, 100)",
      "device_number": "SN@string('number', 8)",
      "custom_device_name": "我的智能小音箱",
      "is_primary": "@integer(0, 1)",
      "model_name": "A1-Standard",
      "status": "@integer(0, 1)",
      "last_active": "@datetime('yyyy-MM-dd HH:mm:ss')"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|none|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» msg|string|true|none||none|
|» data|[object]|true|none||none|
|»» device_id|string|true|none||none|
|»» device_number|string|true|none||none|
|»» custom_device_name|string|true|none||none|
|»» model_name|string|true|none||none|
|»» status|string|true|none||none|
|»» last_active|string|true|none||none|

# 设备管理模块/设备电量页

## GET 获取电量信息

GET /api/device/battery

获取电量信息
用户进入“设备电量页”后，前端调用该接口获取当前设备电量、预计可播放时长、低电量提醒阈值、省电模式状态等信息。

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
  "message": "获取电量信息成功",
  "data": {
    "deviceId": "dev_001",
    "battery": 82,
    "estimatedPlayTime": "11小时20分钟",
    "lowBatteryThreshold": 20,
    "powerSaveEnabled": false,
    "isCharging": false,
    "fullChargeNotice": true
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
|»» battery|integer|true|none||none|
|»» estimatedPlayTime|string|true|none||none|
|»» lowBatteryThreshold|integer|true|none||none|
|»» powerSaveEnabled|boolean|true|none||none|
|»» isCharging|boolean|true|none||none|
|»» fullChargeNotice|boolean|true|none||none|

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

## POST 设置省电模式

POST /api/device/power-save

设置省电模式
用于开启或关闭指定智能音箱的省电模式。

开启后，设备会降低后台功耗、减少待机耗电；关闭后恢复正常运行模式。

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "enabled": true
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» enabled|body|boolean| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "省电模式设置成功",
  "data": {
    "deviceId": "dev_001",
    "powerSaveEnabled": true
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
|» message|string|true|none||none|
|» data|object|true|none||none|
|»» deviceId|string|true|none||none|
|»» powerSaveEnabled|boolean|true|none||none|

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

# 设备管理模块/电量通知设置页

## POST 电量通知设置

POST /api/device/battery-notice

电量通知设置
用于设置智能音箱的电量通知规则。

用户在“电量通知设置页”修改低电量提醒、提醒阈值、充电完成提醒后，前端调用该接口保存设置。

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "lowBatteryEnabled": true,
  "threshold": 20,
  "fullChargeNotice": true
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» lowBatteryEnabled|body|boolean| 是 |none|
|» threshold|body|integer| 是 |none|
|» fullChargeNotice|body|boolean| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "电量通知设置成功",
  "data": {
    "deviceId": "dev_001",
    "lowBatteryEnabled": true,
    "threshold": 20,
    "fullChargeNotice": true
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
|»» lowBatteryEnabled|boolean|true|none||none|
|»» threshold|integer|true|none||none|
|»» fullChargeNotice|boolean|true|none||none|

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

# 设备管理模块/自定义设备名页

## POST 自定义设备名

POST /POST /api/device/rename

自定义设备名
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

# 设备管理模块/高级设置页

## POST 高级设置

POST /api/device/advanced-settings

高级设置
用于保存指定智能音箱的高级设置。

用户在“高级设置页”修改音量上限、夜间勿扰时间、固件自动更新后，前端调用该接口保存设置。

> Body 请求参数

```json
{
  "deviceId": "dev_001",
  "volumeLimit": 80,
  "nightModeEnabled": true,
  "nightStart": "23:00",
  "nightEnd": "07:00",
  "autoFirmwareUpdate": true
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceId|body|string| 是 |none|
|» volumeLimit|body|integer| 是 |none|
|» nightModeEnabled|body|boolean| 是 |none|
|» nightStart|body|string| 是 |none|
|» nightEnd|body|string| 是 |none|
|» autoFirmwareUpdate|body|boolean| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "高级设置保存成功",
  "data": {
    "deviceId": "dev_001",
    "volumeLimit": 80,
    "nightModeEnabled": true,
    "nightStart": "23:00",
    "nightEnd": "07:00",
    "autoFirmwareUpdate": true
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
|»» volumeLimit|integer|true|none||none|
|»» nightModeEnabled|boolean|true|none||none|
|»» nightStart|string|true|none||none|
|»» nightEnd|string|true|none||none|
|»» autoFirmwareUpdate|boolean|true|none||none|

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

# 设备管理模块/绑定新设备页

## GET 搜索附近设备

GET /api/device/search-nearby

搜索附近设备

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|keyword|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "搜索成功",
  "data": {
    "total": 2,
    "list": [
      {
        "deviceId": "dev_001",
        "deviceName": "客厅音箱",
        "modelName": "SH-Mini A1",
        "signalStrength": -65,
        "online": true,
        "binded": false
      },
      {
        "deviceId": "dev_002",
        "deviceName": "卧室音箱",
        "modelName": "SH-Pro X",
        "signalStrength": -72,
        "online": true,
        "binded": true
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

> 404 Response

```json
{
  "code": 200,
  "message": "未发现附近设备",
  "data": {
    "total": 0,
    "list": []
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
|»» total|integer|true|none||none|
|»» list|[object]|true|none||none|
|»»» deviceId|string|true|none||none|
|»»» deviceName|string|true|none||none|
|»»» modelName|string|true|none||none|
|»»» signalStrength|integer|true|none||none|
|»»» online|boolean|true|none||none|
|»»» binded|boolean|true|none||none|

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
|»» total|integer|true|none||none|
|»» list|[string]|true|none||none|

## POST 开始绑定

POST /api/device/bind

开始绑定

> Body 请求参数

```json
{
  "deviceSn": "SHMINI-A1-0001",
  "wifiName": "Home-5G",
  "wifiPassword": "12345678"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» deviceSn|body|string| 是 |none|
|» wifiName|body|string| 是 |none|
|» wifiPassword|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "开始绑定设备",
  "data": {
    "taskId": "bind_001",
    "deviceSn": "SHMINI-A1-0001",
    "deviceName": "声盒 Mini A1",
    "status": "binding",
    "progress": 0
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
  "message": "未发现该设备",
  "data": {
    "deviceSn": "SHMINI-A1-0001"
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
|»» taskId|string|true|none||none|
|»» deviceSn|string|true|none||none|
|»» deviceName|string|true|none||none|
|»» status|string|true|none||none|
|»» progress|integer|true|none||none|

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
|»» deviceSn|string|true|none||none|

## GET 查询配网进度

GET /api/device/bind-progress

查询配网进度
用于查询设备绑定与配网进度。

客户端在调用“开始绑定设备”接口后，使用返回的 taskId 周期性轮询该接口，获取当前配网进度和步骤状态。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|taskId|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "progress": 70,
  "steps": [
    {
      "name": "发现声盒 Mini A1",
      "status": "done"
    },
    {
      "name": "写入 Wi-Fi 信息",
      "status": "doing"
    },
    {
      "name": "绑定到微信账号",
      "status": "waiting"
    }
  ]
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
|» progress|integer|true|none||none|
|» steps|[object]|true|none||none|
|»» name|string|true|none||none|
|»» status|string|true|none||none|

状态码 **401**

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

# 音乐服务管理

## POST 绑定音乐服务

POST /api/music-service/bind

绑定音乐服务
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

## GET 获取同步进度

GET /api/music-service/sync-progress

获取同步进度
用于查询第三方音乐服务的数据同步进度。

用户绑定音乐平台后，系统会同步：

收藏歌曲
歌单
最近播放
喜欢的音乐

前端可轮询该接口，用于展示同步状态和进度条。

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|service|query|string| 否 |none|
|Authorization|header|string| 否 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "获取同步进度成功",
  "data": {
    "service": "qq",
    "status": "syncing",
    "progress": 65,
    "currentTask": "正在同步收藏歌曲",
    "totalSongs": 1200,
    "syncedSongs": 780
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
|»» service|string|true|none||none|
|»» status|string|true|none||none|
|»» progress|integer|true|none||none|
|»» currentTask|string|true|none||none|
|»» totalSongs|integer|true|none||none|
|»» syncedSongs|integer|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## POST 修改权限

POST /api/music-service/permissions

修改权限
用于修改已绑定音乐服务的授权权限。

用户在“授权权限”页面开启或关闭某项权限后，前端调用该接口保存设置。关闭某项权限后，对应功能会停止同步或不可用

> Body 请求参数

```json
{
  "service": "qq",
  "permissions": {
    "readPlaylist": true,
    "syncHistory": true,
    "personalRecommend": true
  }
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» service|body|string| 是 |none|
|» permissions|body|object| 是 |none|
|»» readPlaylist|body|boolean| 是 |none|
|»» syncHistory|body|boolean| 是 |none|
|»» personalRecommend|body|boolean| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "权限修改成功",
  "data": {
    "service": "qq",
    "permissions": {
      "readPlaylist": true,
      "syncHistory": true,
      "personalRecommend": true
    }
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
|»» service|string|true|none||none|
|»» permissions|object|true|none||none|
|»»» readPlaylist|boolean|true|none||none|
|»»» syncHistory|boolean|true|none||none|
|»»» personalRecommend|boolean|true|none||none|

状态码 **401**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» message|string|true|none||none|
|» data|null|true|none||none|

## POST 解除账号绑定

POST /api/music-service/unbind

解除账号绑定
用于解除当前用户与第三方音乐平台账号的绑定关系。
解绑后：
停止同步歌单与播放记录
清除对应平台授权信息
智能音箱无法继续使用该音乐平台播放服务

> Body 请求参数

```json
{
  "service": "qq"
}
```

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|Authorization|header|string| 否 |none|
|body|body|object| 是 |none|
|» service|body|string| 是 |none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "解绑成功",
  "data": {
    "service": "qq",
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
  "message": "当前音乐服务未绑定",
  "data": {
    "service": "qq"
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
|»» service|string|true|none||none|

# 数据模型

