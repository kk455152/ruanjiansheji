import os

from flask import Flask, jsonify, request

from db_api_service import DatabaseApiService, MongoNativeError, MySQLNativeError, build_service


app = Flask(__name__)
service = build_service()


def response_ok(data, message="success", status_code=200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def response_error(message, status_code=400):
    return jsonify({"success": False, "message": message}), status_code


def parse_limit_and_offset():
    limit = int(request.args.get("limit", "20"))
    offset = int(request.args.get("offset", "0"))
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    return limit, offset


def parse_primary_keys(table_name: str):
    schema = service.get_table_schema(table_name)
    primary_keys = schema["primary_keys"]
    values = {}
    for key in primary_keys:
        value = request.args.get(key)
        if value is None:
            raise ValueError(f"Missing query parameter: {key}")
        values[key] = value
    return values


@app.errorhandler(ValueError)
def handle_value_error(error):
    return response_error(str(error), 400)


@app.errorhandler(KeyError)
def handle_key_error(error):
    message = error.args[0] if error.args else str(error)
    return response_error(message, 404)


@app.errorhandler(MySQLNativeError)
def handle_mysql_error(error):
    return response_error(str(error), 500)


@app.errorhandler(MongoNativeError)
def handle_mongo_error(error):
    return response_error(str(error), 500)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unexpected database API error: %s", error)
    return response_error("Internal server error", 500)


@app.get("/db-api/health")
def health():
    mysql_meta = service.get_mysql_metadata()
    mongo_info = service.get_mongo_overview()
    return response_ok(
        {
            "mysql_database": mysql_meta["database"],
            "mysql_table_count": len(mysql_meta["tables"]),
            "mongo_database": mongo_info["database"],
            "mongo_collection_count": len(mongo_info["collections"]),
        }
    )


@app.get("/db-api/mysql/tables")
def mysql_tables():
    return response_ok(service.list_tables())


@app.post("/db-api/mysql/metadata/refresh")
def refresh_mysql_metadata():
    metadata = service.get_mysql_metadata(force_refresh=True)
    return response_ok({"database": metadata["database"], "table_count": len(metadata["tables"])}, "metadata refreshed")


@app.get("/db-api/mysql/tables/<table_name>/schema")
def mysql_schema(table_name: str):
    return response_ok(service.get_table_schema(table_name))


@app.get("/db-api/mysql/tables/<table_name>/rows")
def mysql_list_rows(table_name: str):
    limit, offset = parse_limit_and_offset()
    return response_ok(service.list_rows(table_name, limit=limit, offset=offset))


@app.get("/db-api/mysql/tables/<table_name>/record")
def mysql_get_record(table_name: str):
    primary_key_values = parse_primary_keys(table_name)
    return response_ok(service.get_record(table_name, primary_key_values))


@app.post("/db-api/mysql/tables/<table_name>/record")
def mysql_create_record(table_name: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return response_ok(service.create_record(table_name, payload), "record created", 201)


@app.put("/db-api/mysql/tables/<table_name>/record")
def mysql_update_record(table_name: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    primary_key_values = payload.get("primary_keys")
    update_data = payload.get("data")
    if not isinstance(primary_key_values, dict):
        raise ValueError("primary_keys must be an object")
    if not isinstance(update_data, dict):
        raise ValueError("data must be an object")
    return response_ok(service.update_record(table_name, primary_key_values, update_data), "record updated")


@app.delete("/db-api/mysql/tables/<table_name>/record")
def mysql_delete_record(table_name: str):
    primary_key_values = parse_primary_keys(table_name)
    return response_ok(service.delete_record(table_name, primary_key_values), "record deleted")


@app.get("/db-api/mongo/overview")
def mongo_overview():
    return response_ok(service.get_mongo_overview())


if __name__ == "__main__":
    app.run(
        host=os.environ.get("DB_API_HOST", "0.0.0.0"),
        port=int(os.environ.get("DB_API_PORT", "5001")),
        debug=os.environ.get("DB_API_DEBUG", "false").lower() == "true",
    )
