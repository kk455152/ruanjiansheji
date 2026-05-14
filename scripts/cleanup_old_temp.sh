#!/usr/bin/env bash
set -e
cd /www/wwwroot/mysite

pkill -f "runtime/c_observe_db_write_bridge.py" 2>/dev/null || true

rm -f runtime/c_observe_db_write_bridge.py
rm -f runtime/c_observe_db_write_bridge.log
rm -f runtime/c_observe_db_write_bridge.offset
rm -rf runtime/final_code_for_github
rm -f runtime/final_code_for_github.zip

find /www/wwwroot/mysite -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
