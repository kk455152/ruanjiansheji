import json
import os
from pprint import pprint

from mysql_native import MySQLNativeClient


def main() -> None:
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ["MYSQL_USER"]
    password = os.environ["MYSQL_PASSWORD"]

    with MySQLNativeClient(host=host, port=port, user=user, password=password) as client:
        databases = client.query("SHOW DATABASES")
        print("Databases:")
        pprint(databases)

        for row in databases:
            db_name = row.get("Database")
            if not db_name:
                continue

            print(f"\n=== Database: {db_name} ===")
            client.execute(f"USE `{db_name}`")

            tables = client.query("SHOW TABLES")
            print("Tables:")
            pprint(tables)

            for table_row in tables:
                table_name = next(iter(table_row.values()))
                print(f"\n--- Table: {table_name} ---")
                describe_rows = client.query(f"DESCRIBE `{table_name}`")
                print("Schema:")
                pprint(describe_rows)

                sample_rows = client.query(f"SELECT * FROM `{table_name}` LIMIT 3")
                print("Sample rows:")
                print(json.dumps(sample_rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
