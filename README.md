# 小程序 API 拆分版代码

这版把原来很大的 `api_routes.py` 拆成多个小文件，方便手动加到 GitHub。

## 需要新增/替换的文件

```text
api_routes.py
api_pkg/__init__.py
api_pkg/common.py
api_pkg/auth_home.py
api_pkg/player.py
api_pkg/friends_rooms.py
api_pkg/share_data_history.py
api_pkg/device.py
api_pkg/music_service.py
runtime/test_all_api_mock.py
```

## 还要确认 app.py

看 `APP_PATCH.md`，确认 `app.py` 已 import 并 register `api_bp`。

## 测试

```bash
cd /www/wwwroot/mysite
python3 -m py_compile app.py api_routes.py api_pkg/*.py
python3 runtime/test_all_api_mock.py
```

## 说明

这是 database-first-with-mock-fallback 版本：
- 优先尝试 MySQL / MongoDB 查询。
- 查询失败、表不存在、无数据时，自动用 mock fallback 保证接口不断。
- 接口路径和返回结构保持原样。
