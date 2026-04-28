import json
import os

from mongo_native import MongoNativeClient


def main() -> None:
    uri = os.environ["MONGO_URI"]
    with MongoNativeClient(uri) as client:
        print(f"Database: {client.uri.database}")
        collections = client.list_collection_names()
        print(json.dumps({"collections": collections}, ensure_ascii=False, indent=2))
        for name in collections:
            print(f"\n=== {name} ===")
            rows = client.find_sample(name, limit=3)
            print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
