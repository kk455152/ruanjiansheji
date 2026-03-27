# 传感器数据上传系统 - API 接口文档

## 1. 接口基本信息
* **接口地址**: `http://[服务器公网IP]:5000/api/upload`
* **请求方式**: `POST`
* **数据格式**: `Content-Type: application/json`

## 2. 请求参数说明 (Payload)
| 字段名 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `user_id` | String | 登录用户名 | "ruanjiansheji" |
| `password` | String | 身份验证密码 | "gaoji" |
| `device_id` | String | 设备唯一标识 | "dev_01" |
| `val` | Float | 传感器数值 (如温度) | 25.5 |

## 3. 请求示例
```json
{
  "user_id": "ruanjiansheji",
  "password": "gaoji",
  "device_id": "dev_01",
  "val": 25.5
}
