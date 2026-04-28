import hashlib
import socket
import struct
from typing import Any, Dict, List, Optional, Sequence


CLIENT_LONG_PASSWORD = 0x00000001
CLIENT_LONG_FLAG = 0x00000004
CLIENT_CONNECT_WITH_DB = 0x00000008
CLIENT_PROTOCOL_41 = 0x00000200
CLIENT_TRANSACTIONS = 0x00002000
CLIENT_SECURE_CONNECTION = 0x00008000
CLIENT_MULTI_RESULTS = 0x00020000
CLIENT_PLUGIN_AUTH = 0x00080000
CLIENT_DEPRECATE_EOF = 0x01000000

COM_QUERY = 0x03


class MySQLNativeError(RuntimeError):
    pass


def _sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _pack_lenenc_int(value: int) -> bytes:
    if value < 251:
        return struct.pack("<B", value)
    if value < 2**16:
        return b"\xfc" + struct.pack("<H", value)
    if value < 2**24:
        return b"\xfd" + value.to_bytes(3, "little")
    return b"\xfe" + struct.pack("<Q", value)


def _read_lenenc_int(payload: bytes, offset: int) -> tuple[Optional[int], int]:
    first = payload[offset]
    offset += 1
    if first < 0xfb:
        return first, offset
    if first == 0xfb:
        return None, offset
    if first == 0xfc:
        return struct.unpack_from("<H", payload, offset)[0], offset + 2
    if first == 0xfd:
        return int.from_bytes(payload[offset:offset + 3], "little"), offset + 3
    if first == 0xfe:
        return struct.unpack_from("<Q", payload, offset)[0], offset + 8
    raise MySQLNativeError("Unsupported length-encoded integer marker")


def _read_lenenc_str(payload: bytes, offset: int) -> tuple[Optional[bytes], int]:
    length, offset = _read_lenenc_int(payload, offset)
    if length is None:
        return None, offset
    return payload[offset:offset + length], offset + length


def _read_cstring(payload: bytes, offset: int) -> tuple[bytes, int]:
    end = payload.index(0, offset)
    return payload[offset:end], end + 1


def _scramble_native_password(password: str, seed: bytes) -> bytes:
    password_bytes = password.encode("utf-8")
    stage1 = _sha1(password_bytes)
    stage2 = _sha1(stage1)
    stage3 = _sha1(seed + stage2)
    return _xor_bytes(stage1, stage3)


def _scramble_caching_sha2(password: str, seed: bytes) -> bytes:
    password_bytes = password.encode("utf-8")
    stage1 = _sha256(password_bytes)
    stage2 = _sha256(stage1)
    stage3 = _sha256(stage2 + seed)
    return _xor_bytes(stage1, stage3)


class MySQLNativeClient:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: Optional[str] = None,
        connect_timeout: float = 8.0,
        charset_id: int = 45,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connect_timeout = connect_timeout
        self.charset_id = charset_id
        self.socket: Optional[socket.socket] = None
        self.sequence_id = 0
        self.server_capabilities = 0
        self.auth_plugin_name = "mysql_native_password"
        self.auth_seed = b""

    def connect(self) -> None:
        self.socket = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        self.socket.settimeout(self.connect_timeout)
        self.sequence_id = 0
        handshake = self._read_packet()
        self._parse_handshake(handshake)
        self._send_handshake_response()
        self._finish_auth()

    def close(self) -> None:
        if self.socket is not None:
            try:
                self.socket.close()
            finally:
                self.socket = None

    def __enter__(self) -> "MySQLNativeClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        self._send_command(COM_QUERY, sql.encode("utf-8"))
        first = self._read_packet()
        if not first:
            return []
        header = first[0]
        if header == 0x00:
            return []
        if header == 0xff:
            self._raise_error(first)

        column_count, _ = _read_lenenc_int(first, 0)
        if column_count is None:
            raise MySQLNativeError("Failed to read result set column count")

        columns = [self._read_column_definition() for _ in range(column_count)]

        rows: List[Dict[str, Any]] = []
        packet = self._read_packet()
        if not self._is_resultset_boundary(packet):
            rows.append(self._read_row(packet, columns))

        while True:
            if self._is_resultset_boundary(packet):
                break
            packet = self._read_packet()
            if self._is_resultset_boundary(packet):
                break
            rows.append(self._read_row(packet, columns))
        return rows

    def execute(self, sql: str) -> Dict[str, Any]:
        self._send_command(COM_QUERY, sql.encode("utf-8"))
        packet = self._read_packet()
        if packet[0] == 0xff:
            self._raise_error(packet)
        if packet[0] != 0x00:
            raise MySQLNativeError("Unexpected response for execute command")

        affected_rows, offset = _read_lenenc_int(packet, 1)
        last_insert_id, offset = _read_lenenc_int(packet, offset)
        status_flags = struct.unpack_from("<H", packet, offset)[0]
        offset += 2
        warnings = struct.unpack_from("<H", packet, offset)[0]
        return {
            "affected_rows": affected_rows or 0,
            "last_insert_id": last_insert_id or 0,
            "status_flags": status_flags,
            "warnings": warnings,
        }

    def escape_value(self, value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bytes):
            return "0x" + value.hex()

        text = str(value)
        escaped = (
            text.replace("\\", "\\\\")
            .replace("\x00", "\\0")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\x1a", "\\Z")
        )
        return f"'{escaped}'"

    def _parse_handshake(self, payload: bytes) -> None:
        offset = 0
        protocol_version = payload[offset]
        offset += 1
        if protocol_version < 10:
            raise MySQLNativeError("Unsupported MySQL protocol version")

        _, offset = _read_cstring(payload, offset)
        offset += 4
        seed_part1 = payload[offset:offset + 8]
        offset += 8
        offset += 1
        capability_lower = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
        offset += 1
        offset += 2
        capability_upper = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
        self.server_capabilities = capability_lower | (capability_upper << 16)

        auth_plugin_data_length = payload[offset]
        offset += 1
        offset += 10

        seed_part2_len = max(13, auth_plugin_data_length - 8)
        seed_part2 = payload[offset:offset + seed_part2_len]
        offset += seed_part2_len
        self.auth_seed = seed_part1 + seed_part2.rstrip(b"\x00")

        if self.server_capabilities & CLIENT_PLUGIN_AUTH and offset < len(payload):
            plugin_name, _ = _read_cstring(payload, offset)
            if plugin_name:
                self.auth_plugin_name = plugin_name.decode("ascii", errors="ignore")

    def _build_auth_response(self, plugin_name: str) -> bytes:
        if not self.password:
            return b""
        if plugin_name == "mysql_native_password":
            return _scramble_native_password(self.password, self.auth_seed)
        if plugin_name == "caching_sha2_password":
            return _scramble_caching_sha2(self.password, self.auth_seed)
        raise MySQLNativeError(f"Unsupported auth plugin: {plugin_name}")

    def _send_handshake_response(self) -> None:
        capabilities = (
            CLIENT_LONG_PASSWORD
            | CLIENT_LONG_FLAG
            | CLIENT_PROTOCOL_41
            | CLIENT_TRANSACTIONS
            | CLIENT_SECURE_CONNECTION
            | CLIENT_MULTI_RESULTS
            | CLIENT_PLUGIN_AUTH
            | CLIENT_DEPRECATE_EOF
        )
        if self.database:
            capabilities |= CLIENT_CONNECT_WITH_DB

        auth_response = self._build_auth_response(self.auth_plugin_name)
        payload = bytearray()
        payload.extend(struct.pack("<I", capabilities))
        payload.extend(struct.pack("<I", 1024 * 1024 * 16))
        payload.extend(struct.pack("<B", self.charset_id))
        payload.extend(b"\x00" * 23)
        payload.extend(self.user.encode("utf-8") + b"\x00")
        payload.extend(_pack_lenenc_int(len(auth_response)))
        payload.extend(auth_response)
        if self.database:
            payload.extend(self.database.encode("utf-8") + b"\x00")
        payload.extend(self.auth_plugin_name.encode("ascii") + b"\x00")
        self._write_packet(bytes(payload))

    def _finish_auth(self) -> None:
        while True:
            packet = self._read_packet()
            marker = packet[0]
            if marker == 0x00:
                return
            if marker == 0xff:
                self._raise_error(packet)
            if marker == 0xfe:
                plugin_name, offset = _read_cstring(packet, 1)
                self.auth_plugin_name = plugin_name.decode("ascii", errors="ignore")
                self.auth_seed = packet[offset:]
                auth_response = self._build_auth_response(self.auth_plugin_name)
                self._write_packet(auth_response)
                continue
            if marker == 0x01 and packet[1] == 0x03:
                continue
            raise MySQLNativeError(f"Unsupported authentication packet: {packet[:8].hex()}")

    def _read_column_definition(self) -> str:
        packet = self._read_packet()
        offset = 0
        for _ in range(4):
            _, offset = _read_lenenc_str(packet, offset)
        name, offset = _read_lenenc_str(packet, offset)
        if name is None:
            raise MySQLNativeError("Column name is missing")
        _, offset = _read_lenenc_str(packet, offset)
        return name.decode("utf-8", errors="replace")

    def _read_row(self, packet: bytes, columns: Sequence[str]) -> Dict[str, Any]:
        offset = 0
        row: Dict[str, Any] = {}
        for column in columns:
            value, offset = _read_lenenc_str(packet, offset)
            row[column] = None if value is None else value.decode("utf-8", errors="replace")
        return row

    def _is_resultset_boundary(self, packet: bytes) -> bool:
        if len(packet) < 9 and packet[0] == 0xfe:
            return True
        return packet[0] == 0x00 and len(packet) >= 7

    def _send_command(self, command: int, payload: bytes) -> None:
        self.sequence_id = 0
        self._write_packet(struct.pack("<B", command) + payload)

    def _write_packet(self, payload: bytes) -> None:
        if self.socket is None:
            raise MySQLNativeError("MySQL socket is not connected")
        header = struct.pack("<I", len(payload))[:3] + struct.pack("<B", self.sequence_id)
        self.socket.sendall(header + payload)
        self.sequence_id = (self.sequence_id + 1) % 256

    def _read_packet(self) -> bytes:
        if self.socket is None:
            raise MySQLNativeError("MySQL socket is not connected")
        header = self._recv_exact(4)
        length = header[0] | (header[1] << 8) | (header[2] << 16)
        self.sequence_id = (header[3] + 1) % 256
        return self._recv_exact(length)

    def _recv_exact(self, size: int) -> bytes:
        if self.socket is None:
            raise MySQLNativeError("MySQL socket is not connected")
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.socket.recv(size - len(chunks))
            if not chunk:
                raise MySQLNativeError("MySQL connection closed unexpectedly")
            chunks.extend(chunk)
        return bytes(chunks)

    def _raise_error(self, packet: bytes) -> None:
        code = struct.unpack_from("<H", packet, 1)[0]
        message = packet[9:].decode("utf-8", errors="replace") if len(packet) >= 9 else "Unknown MySQL error"
        raise MySQLNativeError(f"MySQL error {code}: {message}")
