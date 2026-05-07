import pymysql
from pymongo import MongoClient
from pymysql.cursors import DictCursor

from config import MYSQL_CONFIG, MONGO_URI, MONGO_DB


def get_mysql_conn():
    return pymysql.connect(
        **MYSQL_CONFIG,
        cursorclass=DictCursor,
        autocommit=False
    )


mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
