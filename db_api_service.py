import os
from contextlib import contextmanager
from typing import Any, Dict, List

from db_tools.mongo_native import MongoNativeClient, MongoNativeError
from db_tools.mysql_native import MySQLNativeClient, MySQLNativeError


class ServiceConfigError(RuntimeError):
    pass


class DatabaseApiService:
    def __init__(self) -> None:
        self.mysql_host = os.environ.get("MYSQL_HOST", "127.0.0.1")
        self.mysql_port = int(os.environ.get("MYSQL_PORT", "3306"))
        self.mysql_user = os.environ.get("MYSQL_USER", "root")
        self.mysql_password = os.environ.get("MYSQL_PASSWORD", "change_me")
        self.mysql_database = os.environ.get("MYSQL_DATABASE", "smart_speaker")
        self.mongo_uri = os.environ.get(
            "MONGO_URI",
            "mongodb://username:password@127.0.0.1:27017/musicplayer?authSource=admin",
        )
        self._metadata_cache: Dict[str, Any] | None = None

    @contextmanager
    def mysql_client(self):
        client = MySQLNativeClient(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database,
        )
        client.connect()
        try:
            yield client
        finally:
            client.close()

    def get_mysql_metadata(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self._metadata_cache is not None and not force_refresh:
            return self._metadata_cache

        with self.mysql_client() as client:
            rows = client.query(
                f"""
                SELECT
                    TABLE_NAME,
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    COLUMN_DEFAULT,
                    EXTRA,
                    ORDINAL_POSITION
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.mysql_database}'
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
            )

        tables: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            table_name = row["TABLE_NAME"]
            table = tables.setdefault(
                table_name,
                {
                    "table_name": table_name,
                    "columns": [],
                    "column_names": set(),
                    "primary_keys": [],
                    "required_on_create": [],
                },
            )
            column = {
                "name": row["COLUMN_NAME"],
                "column_type": row["COLUMN_TYPE"],
                "is_nullable": row["IS_NULLABLE"] == "YES",
                "is_primary_key": row["COLUMN_KEY"] == "PRI",
                "default": row["COLUMN_DEFAULT"],
                "extra": row["EXTRA"] or "",
                "ordinal_position": int(row["ORDINAL_POSITION"]),
            }
            table["columns"].append(column)
            table["column_names"].add(column["name"])
            if column["is_primary_key"]:
                table["primary_keys"].append(column["name"])

            has_default = column["default"] is not None or "DEFAULT_GENERATED" in column["extra"]
            is_auto_increment = "auto_increment" in column["extra"]
            if not column["is_nullable"] and not has_default and not is_auto_increment:
                table["required_on_create"].append(column["name"])

        for table in tables.values():
            table["column_names"] = sorted(table["column_names"])

        self._metadata_cache = {
            "database": self.mysql_database,
            "tables": dict(sorted(tables.items())),
        }
        return self._metadata_cache

    def list_tables(self) -> List[Dict[str, Any]]:
        metadata = self.get_mysql_metadata()
        return [
            {
                "table_name": table_name,
                "primary_keys": table_info["primary_keys"],
                "column_count": len(table_info["columns"]),
            }
            for table_name, table_info in metadata["tables"].items()
        ]

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        return {
            "table_name": table_name,
            "primary_keys": table["primary_keys"],
            "required_on_create": table["required_on_create"],
            "columns": table["columns"],
        }

    def list_rows(self, table_name: str, limit: int, offset: int) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        order_columns = table["primary_keys"] or [table["columns"][0]["name"]]
        order_clause = ", ".join(f"`{column}`" for column in order_columns)

        with self.mysql_client() as client:
            rows = client.query(
                f"SELECT * FROM `{table_name}` ORDER BY {order_clause} LIMIT {int(limit)} OFFSET {int(offset)}"
            )
            total_count = client.query(f"SELECT COUNT(*) AS total_count FROM `{table_name}`")[0]["total_count"]

        return {
            "table_name": table_name,
            "limit": limit,
            "offset": offset,
            "total_count": int(total_count),
            "rows": rows,
        }

    def get_record(self, table_name: str, primary_key_values: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        where_clause = self._build_primary_key_where(table, primary_key_values)
        with self.mysql_client() as client:
            rows = client.query(f"SELECT * FROM `{table_name}` WHERE {where_clause} LIMIT 1")
        if not rows:
            raise KeyError(f"Table {table_name} has no matching record")
        return rows[0]

    def create_record(self, table_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        if not payload:
            raise ValueError("Create payload cannot be empty")
        self._validate_payload_fields(table, payload, allow_primary_key=True)

        missing = [name for name in table["required_on_create"] if name not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        columns = list(payload.keys())
        values = list(payload.values())
        column_clause = ", ".join(f"`{name}`" for name in columns)

        with self.mysql_client() as client:
            value_clause = ", ".join(client.escape_value(value) for value in values)
            result = client.execute(f"INSERT INTO `{table_name}` ({column_clause}) VALUES ({value_clause})")

            primary_key_values = self._extract_primary_key_values_after_insert(table, payload, result)
            record = self.get_record(table_name, primary_key_values) if primary_key_values else {}

        return {
            "table_name": table_name,
            "affected_rows": result["affected_rows"],
            "last_insert_id": result["last_insert_id"],
            "record": record,
        }

    def update_record(self, table_name: str, primary_key_values: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        if not payload:
            raise ValueError("Update data cannot be empty")
        self._validate_payload_fields(table, payload, allow_primary_key=False)

        where_clause = self._build_primary_key_where(table, primary_key_values)
        with self.mysql_client() as client:
            set_clause = ", ".join(
                f"`{column}` = {client.escape_value(value)}" for column, value in payload.items()
            )
            result = client.execute(f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause}")
            record = self.get_record(table_name, primary_key_values)

        return {
            "table_name": table_name,
            "affected_rows": result["affected_rows"],
            "record": record,
        }

    def delete_record(self, table_name: str, primary_key_values: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table_metadata(table_name)
        existing_record = self.get_record(table_name, primary_key_values)
        where_clause = self._build_primary_key_where(table, primary_key_values)

        with self.mysql_client() as client:
            result = client.execute(f"DELETE FROM `{table_name}` WHERE {where_clause}")

        return {
            "table_name": table_name,
            "affected_rows": result["affected_rows"],
            "deleted_record": existing_record,
        }

    def get_mongo_overview(self) -> Dict[str, Any]:
        with MongoNativeClient(self.mongo_uri) as client:
            collections = client.list_collection_names()
            samples = {name: client.find_sample(name, limit=3) for name in collections}
            databases = client.command("admin", {"listDatabases": 1, "nameOnly": True})["databases"]

        return {
            "database": parse_database_name_from_uri(self.mongo_uri),
            "collections": collections,
            "sample_documents": samples,
            "visible_databases": [item["name"] for item in databases],
        }

    def _get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        metadata = self.get_mysql_metadata()
        table = metadata["tables"].get(table_name)
        if table is None:
            raise KeyError(f"Unknown table: {table_name}")
        return table

    def _validate_payload_fields(self, table: Dict[str, Any], payload: Dict[str, Any], allow_primary_key: bool) -> None:
        unknown = [name for name in payload if name not in table["column_names"]]
        if unknown:
            raise ValueError(f"Unknown fields: {', '.join(unknown)}")
        if not allow_primary_key:
            pk_overlap = [name for name in payload if name in table["primary_keys"]]
            if pk_overlap:
                raise ValueError(f"Primary key fields cannot be updated: {', '.join(pk_overlap)}")

    def _build_primary_key_where(self, table: Dict[str, Any], primary_key_values: Dict[str, Any]) -> str:
        missing = [name for name in table["primary_keys"] if name not in primary_key_values]
        if missing:
            raise ValueError(f"Missing primary key fields: {', '.join(missing)}")

        return " AND ".join(
            f"`{column}` = {self._escape_value(primary_key_values[column])}"
            for column in table["primary_keys"]
        )

    def _extract_primary_key_values_after_insert(
        self,
        table: Dict[str, Any],
        payload: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        primary_key_values: Dict[str, Any] = {}
        for column_name in table["primary_keys"]:
            column_meta = next(column for column in table["columns"] if column["name"] == column_name)
            if column_name in payload:
                primary_key_values[column_name] = payload[column_name]
            elif "auto_increment" in column_meta["extra"] and result["last_insert_id"]:
                primary_key_values[column_name] = result["last_insert_id"]
        return primary_key_values

    def _escape_value(self, value: Any) -> str:
        temp_client = MySQLNativeClient(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database,
        )
        return temp_client.escape_value(value)


def parse_database_name_from_uri(uri: str) -> str:
    if "/" not in uri:
        return ""
    tail = uri.rsplit("/", 1)[1]
    return tail.split("?", 1)[0]


def build_service() -> DatabaseApiService:
    service = DatabaseApiService()
    if not service.mysql_database:
        raise ServiceConfigError("MYSQL_DATABASE is required")
    return service
