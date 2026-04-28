import base64
import datetime as dt
import hashlib
import hmac
import os
import socket
import struct
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class MongoNativeError(RuntimeError):
    pass


@dataclass
class MongoUri:
    username: str
    password: str
    host: str
    port: int
    database: str
    auth_source: str


class Binary:
    def __init__(self, data: bytes, subtype: int = 0) -> None:
        self.data = data
        self.subtype = subtype


def parse_mongo_uri(uri: str) -> MongoUri:
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "mongodb":
        raise MongoNativeError("Only mongodb:// URIs are supported")
    if not parsed.username or parsed.password is None:
        raise MongoNativeError("MongoDB URI must include username and password")

    database = parsed.path.lstrip("/") or "admin"
    query = urllib.parse.parse_qs(parsed.query)
    auth_source = query.get("authSource", [database])[0]

    return MongoUri(
        username=urllib.parse.unquote(parsed.username),
        password=urllib.parse.unquote(parsed.password),
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 27017,
        database=database,
        auth_source=auth_source,
    )


def _cstring(text: str) -> bytes:
    return text.encode("utf-8") + b"\x00"


def _encode_document(document: Dict[str, Any]) -> bytes:
    elements = bytearray()
    for key, value in document.items():
        elements.extend(_encode_element(key, value))
    total = len(elements) + 5
    return struct.pack("<i", total) + elements + b"\x00"


def _encode_array(values: List[Any]) -> bytes:
    return _encode_document({str(index): value for index, value in enumerate(values)})


def _encode_element(key: str, value: Any) -> bytes:
    if isinstance(value, Binary):
        data = value.data
        return b"\x05" + _cstring(key) + struct.pack("<i", len(data)) + struct.pack("<B", value.subtype) + data
    if isinstance(value, bool):
        return b"\x08" + _cstring(key) + (b"\x01" if value else b"\x00")
    if value is None:
        return b"\x0A" + _cstring(key)
    if isinstance(value, int):
        if -(2**31) <= value < 2**31:
            return b"\x10" + _cstring(key) + struct.pack("<i", value)
        return b"\x12" + _cstring(key) + struct.pack("<q", value)
    if isinstance(value, float):
        return b"\x01" + _cstring(key) + struct.pack("<d", value)
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        return b"\x02" + _cstring(key) + struct.pack("<i", len(encoded) + 1) + encoded + b"\x00"
    if isinstance(value, dict):
        return b"\x03" + _cstring(key) + _encode_document(value)
    if isinstance(value, list):
        return b"\x04" + _cstring(key) + _encode_array(value)
    raise MongoNativeError(f"Unsupported BSON type for key {key}: {type(value)!r}")


def _decode_cstring(payload: bytes, offset: int) -> tuple[str, int]:
    end = payload.index(0, offset)
    return payload[offset:end].decode("utf-8", errors="replace"), end + 1


def _decode_document(payload: bytes, offset: int = 0) -> tuple[Dict[str, Any], int]:
    total = struct.unpack_from("<i", payload, offset)[0]
    end = offset + total - 1
    cursor = offset + 4
    result: Dict[str, Any] = {}

    while cursor < end:
        element_type = payload[cursor]
        cursor += 1
        key, cursor = _decode_cstring(payload, cursor)
        value, cursor = _decode_value(payload, cursor, element_type)
        result[key] = value

    return result, offset + total


def _decode_array(payload: bytes, offset: int) -> tuple[List[Any], int]:
    document, next_offset = _decode_document(payload, offset)
    values = [document[str(index)] for index in range(len(document))]
    return values, next_offset


def _decode_value(payload: bytes, offset: int, element_type: int) -> tuple[Any, int]:
    if element_type == 0x01:
        return struct.unpack_from("<d", payload, offset)[0], offset + 8
    if element_type == 0x02:
        length = struct.unpack_from("<i", payload, offset)[0]
        offset += 4
        text = payload[offset:offset + length - 1].decode("utf-8", errors="replace")
        return text, offset + length
    if element_type == 0x03:
        return _decode_document(payload, offset)
    if element_type == 0x04:
        return _decode_array(payload, offset)
    if element_type == 0x05:
        length = struct.unpack_from("<i", payload, offset)[0]
        subtype = payload[offset + 4]
        data = payload[offset + 5:offset + 5 + length]
        if subtype == 0:
            return data, offset + 5 + length
        return {"$binary": data.hex(), "$subtype": f"{subtype:02x}"}, offset + 5 + length
    if element_type == 0x07:
        data = payload[offset:offset + 12]
        return {"$oid": data.hex()}, offset + 12
    if element_type == 0x08:
        return payload[offset] == 1, offset + 1
    if element_type == 0x09:
        millis = struct.unpack_from("<q", payload, offset)[0]
        value = dt.datetime.fromtimestamp(millis / 1000, tz=dt.timezone.utc).isoformat()
        return value, offset + 8
    if element_type == 0x0A:
        return None, offset
    if element_type == 0x10:
        return struct.unpack_from("<i", payload, offset)[0], offset + 4
    if element_type == 0x12:
        return struct.unpack_from("<q", payload, offset)[0], offset + 8
    raise MongoNativeError(f"Unsupported BSON element type: 0x{element_type:02x}")


def _hi(data: bytes, salt: bytes, iterations: int, algorithm: str) -> bytes:
    return hashlib.pbkdf2_hmac(algorithm, data, salt, iterations)


def _hmac_digest(key: bytes, data: bytes, algorithm: str) -> bytes:
    return hmac.new(key, data, algorithm).digest()


def _hash_digest(data: bytes, algorithm: str) -> bytes:
    return hashlib.new(algorithm, data).digest()


class MongoNativeClient:
    def __init__(self, uri: str, connect_timeout: float = 8.0) -> None:
        self.uri = parse_mongo_uri(uri)
        self.connect_timeout = connect_timeout
        self.socket: Optional[socket.socket] = None
        self.request_id = 1

    def connect(self) -> None:
        self.socket = socket.create_connection((self.uri.host, self.uri.port), timeout=self.connect_timeout)
        self.socket.settimeout(self.connect_timeout)
        self.command("admin", {"hello": 1, "helloOk": True})
        self._authenticate()

    def close(self) -> None:
        if self.socket is not None:
            try:
                self.socket.close()
            finally:
                self.socket = None

    def __enter__(self) -> "MongoNativeClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def command(self, database: str, document: Dict[str, Any]) -> Dict[str, Any]:
        if self.socket is None:
            raise MongoNativeError("MongoDB socket is not connected")

        command_doc = {**document, "$db": database}
        payload = struct.pack("<i", 0) + b"\x00" + _encode_document(command_doc)
        request_id = self.request_id
        self.request_id += 1
        message = struct.pack("<iiii", 16 + len(payload), request_id, 0, 2013) + payload
        self.socket.sendall(message)

        header = self._recv_exact(16)
        length, _, _, opcode = struct.unpack("<iiii", header)
        if opcode != 2013:
            raise MongoNativeError(f"Unexpected MongoDB opcode: {opcode}")
        body = self._recv_exact(length - 16)
        flag_bits = struct.unpack_from("<i", body, 0)[0]
        if flag_bits & 0x02:
            raise MongoNativeError("MongoDB command response contains moreToCome flag unexpectedly")
        if body[4] != 0:
            raise MongoNativeError("Only BSON body section responses are supported")
        response, _ = _decode_document(body, 5)
        if response.get("ok") not in (1, 1.0, True):
            message = response.get("errmsg", "MongoDB command failed")
            raise MongoNativeError(str(message))
        return response

    def list_collection_names(self) -> List[str]:
        response = self.command(self.uri.database, {"listCollections": 1, "nameOnly": True})
        first_batch = response["cursor"]["firstBatch"]
        return [entry["name"] for entry in first_batch]

    def find_sample(self, collection: str, limit: int = 3) -> List[Dict[str, Any]]:
        response = self.command(
            self.uri.database,
            {
                "find": collection,
                "filter": {},
                "limit": limit,
                "batchSize": limit,
            },
        )
        return response["cursor"]["firstBatch"]

    def _authenticate(self) -> None:
        errors: List[str] = []
        for mechanism in ("SCRAM-SHA-256", "SCRAM-SHA-1"):
            try:
                self._authenticate_scram(mechanism)
                return
            except Exception as exc:
                errors.append(f"{mechanism}: {exc}")
        raise MongoNativeError(" ; ".join(errors))

    def _authenticate_scram(self, mechanism: str) -> None:
        username = self.uri.username
        password = self.uri.password
        nonce = base64.b64encode(os.urandom(18)).decode("ascii")
        bare = f"n={username},r={nonce}"
        initial_payload = f"n,,{bare}".encode("utf-8")

        start = self.command(
            self.uri.auth_source,
            {
                "saslStart": 1,
                "mechanism": mechanism,
                "payload": Binary(initial_payload),
                "autoAuthorize": 1,
                "options": {"skipEmptyExchange": True},
            },
        )

        conversation_id = start["conversationId"]
        server_first = start["payload"].decode("utf-8")
        parsed = dict(item.split("=", 1) for item in server_first.split(","))
        salt = base64.b64decode(parsed["s"])
        iterations = int(parsed["i"])
        combined_nonce = parsed["r"]
        if not combined_nonce.startswith(nonce):
            raise MongoNativeError("Server SCRAM nonce does not extend the client nonce")

        if mechanism == "SCRAM-SHA-256":
            algorithm = "sha256"
            salted_input = password.encode("utf-8")
        else:
            algorithm = "sha1"
            salted_input = hashlib.md5(f"{username}:mongo:{password}".encode("utf-8")).hexdigest().encode("utf-8")

        salted_password = _hi(salted_input, salt, iterations, algorithm)
        client_key = _hmac_digest(salted_password, b"Client Key", algorithm)
        stored_key = _hash_digest(client_key, algorithm)
        without_proof = f"c=biws,r={combined_nonce}"
        auth_message = f"{bare},{server_first},{without_proof}".encode("utf-8")
        client_signature = _hmac_digest(stored_key, auth_message, algorithm)
        client_proof = _xor_bytes(client_key, client_signature)
        final_payload = f"{without_proof},p={base64.b64encode(client_proof).decode('ascii')}".encode("utf-8")

        cont = self.command(
            self.uri.auth_source,
            {
                "saslContinue": 1,
                "conversationId": conversation_id,
                "payload": Binary(final_payload),
            },
        )

        server_final = cont["payload"].decode("utf-8")
        verification = dict(item.split("=", 1) for item in server_final.split(",") if "=" in item)
        server_key = _hmac_digest(salted_password, b"Server Key", algorithm)
        expected_server_signature = base64.b64encode(_hmac_digest(server_key, auth_message, algorithm)).decode("ascii")
        if verification.get("v") != expected_server_signature:
            raise MongoNativeError("MongoDB SCRAM server signature verification failed")

        if not cont.get("done", False):
            self.command(
                self.uri.auth_source,
                {
                    "saslContinue": 1,
                    "conversationId": conversation_id,
                    "payload": Binary(b""),
                },
            )

    def _recv_exact(self, size: int) -> bytes:
        if self.socket is None:
            raise MongoNativeError("MongoDB socket is not connected")
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.socket.recv(size - len(chunks))
            if not chunk:
                raise MongoNativeError("MongoDB connection closed unexpectedly")
            chunks.extend(chunk)
        return bytes(chunks)


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))
