import base64
import hashlib
import json
import os
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# AES-128 passphrase/raw key material used by the project.
SECRET_KEY = b'speaker_key_2026'

# Token salt already used by the current gateway/client flow.
TOKEN_SALT = "smart_speaker_2026_salt"


def generate_token():
    """
    Generate the dynamic token used by the current API gateway.
    """
    timestamp = int(time.time())
    raw_str = f"{TOKEN_SALT}{timestamp}"
    token = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
    return token, timestamp


def _evp_bytes_to_key(passphrase, salt, key_len=16, iv_len=16):
    """
    OpenSSL/CryptoJS-compatible EVP_BytesToKey(MD5) derivation.

    The docx examples use ciphertext beginning with "U2FsdGVkX1",
    which is Base64("Salted__"...), so we align with that format.
    """
    derived = b''
    block = b''
    while len(derived) < key_len + iv_len:
        block = hashlib.md5(block + passphrase + salt).digest()
        derived += block
    return derived[:key_len], derived[key_len:key_len + iv_len]


def encrypt_data(payload_dict):
    """
    Encrypt payload as OpenSSL-compatible salted AES-CBC ciphertext.
    Output format: Base64("Salted__" + salt + ciphertext)
    """
    try:
        salt = os.urandom(8)
        key, iv = _evp_bytes_to_key(SECRET_KEY, salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        json_str = json.dumps(
            payload_dict,
            ensure_ascii=False,
            separators=(',', ':'),
        ).encode('utf-8')
        padded_data = pad(json_str, AES.block_size, style='pkcs7')
        encrypted_bytes = cipher.encrypt(padded_data)
        openssl_blob = b"Salted__" + salt + encrypted_bytes
        return base64.b64encode(openssl_blob).decode('utf-8')
    except Exception as e:
        print(f"Encryption failed: {e}")
        return None


def _decrypt_openssl_salted(decoded_bytes):
    salt = decoded_bytes[8:16]
    ciphertext = decoded_bytes[16:]
    key, iv = _evp_bytes_to_key(SECRET_KEY, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded_bytes = cipher.decrypt(ciphertext)
    json_str = unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7').decode('utf-8')
    return json.loads(json_str)


def _decrypt_legacy_ecb(decoded_bytes):
    """
    Keep backward compatibility with the project's old AES-ECB payloads.
    """
    cipher = AES.new(SECRET_KEY, AES.MODE_ECB)
    decrypted_padded_bytes = cipher.decrypt(decoded_bytes)
    json_str = unpad(decrypted_padded_bytes, AES.block_size).decode('utf-8')
    return json.loads(json_str)


def decrypt_data(encrypted_base64_str):
    """
    Prefer the docx-aligned OpenSSL salted format, with legacy ECB fallback.
    """
    try:
        encrypted_bytes = base64.b64decode(encrypted_base64_str)
        if encrypted_bytes.startswith(b"Salted__") and len(encrypted_bytes) > 16:
            return _decrypt_openssl_salted(encrypted_bytes)
        return _decrypt_legacy_ecb(encrypted_bytes)
    except ValueError:
        print("Warning: invalid payload or key mismatch")
        return None
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None


if __name__ == "__main__":
    token, timestamp = generate_token()
    print(f"token={token}")
    print(f"timestamp={timestamp}")

    sample = {"device_id": "dev_01", "type": "bass_gain", "value": 8}
    encrypted = encrypt_data(sample)
    print(f"encrypted={encrypted}")
    print(f"starts_with_salted={encrypted.startswith('U2FsdGVkX1') if encrypted else False}")
    print(f"decrypted={decrypt_data(encrypted)}")
