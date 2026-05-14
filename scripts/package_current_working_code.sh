#!/usr/bin/env bash
set -e
cd /www/wwwroot/mysite

mkdir -p runtime/current_working_code_for_github/api_pkg runtime/current_working_code_for_github/runtime

cp app.py runtime/current_working_code_for_github/app.py
cp c_observe_routes.py runtime/current_working_code_for_github/c_observe_routes.py
cp api_pkg/player.py runtime/current_working_code_for_github/api_pkg/player.py
cp runtime/c_observe_snapshot_writer.py runtime/current_working_code_for_github/runtime/c_observe_snapshot_writer.py

if [ -f runtime/final_db_write_check.py ]; then
  cp runtime/final_db_write_check.py runtime/current_working_code_for_github/runtime/final_db_write_check.py
fi

cat > runtime/current_working_code_for_github/README.txt <<'TXT'
这些文件来自服务器当前已验证通过版本：
- app.py
- c_observe_routes.py
- api_pkg/player.py
- runtime/c_observe_snapshot_writer.py
- runtime/final_db_write_check.py

验证标准：MongoDB 数量变化验证通过；观察台 MySQL/Mongo API 正常返回。
TXT

cd runtime/current_working_code_for_github
zip -r ../current_working_code_for_github.zip . >/dev/null
cd /www/wwwroot/mysite

ls -lh runtime/current_working_code_for_github.zip
