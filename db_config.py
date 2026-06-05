# db_config.py
import os

import pymysql
from pymysql.cursors import DictCursor

try:
    from storage_backends import get_mysql_config as get_reachable_mysql_config
except Exception:
    get_reachable_mysql_config = None

try:
    from dotenv import load_dotenv
    load_dotenv(".env.db_api")
except Exception:
    pass


def get_mysql_connection():
    if get_reachable_mysql_config is not None:
        config = get_reachable_mysql_config()
        config["autocommit"] = False
        config["cursorclass"] = DictCursor
        return pymysql.connect(**config)

    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "smart_speaker"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
