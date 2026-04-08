# security_utils.py (核心安全工具包 - 请直接发给组员C)
import json
import hashlib
import time
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ==========================================
# 1. 秘钥与盐值配置
# ==========================================
# AES 加密秘钥 (完美 16 字节，直接使用 AES-128)
SECRET_KEY = b'speaker_key_2026'

# 队友 C 指定的独立盐值 (用于 Token 生成)
TOKEN_SALT = "smart_speaker_2026_salt"

# ==========================================
# 2. 鉴权 Token 生成逻辑 (已严格对齐队友 C)
# ==========================================
def generate_token():
    """
    【供模拟器使用】生成鉴权 Token
    规则严格对齐队友 C：MD5(salt + 时间戳)
    """
    timestamp = int(time.time()) 
    raw_str = f"{TOKEN_SALT}{timestamp}"
    token = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
    
    return token, timestamp

# ==========================================
# 3. AES 加解密核心逻辑 (AES-128-ECB)
# ==========================================
def encrypt_data(payload_dict):
    """
    【供 B 模拟器使用】将字典数据转为 JSON 并进行 AES 加密
    """
    try:
        cipher = AES.new(SECRET_KEY, AES.MODE_ECB) 
        json_str = json.dumps(payload_dict).encode('utf-8')
        padded_data = pad(json_str, AES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        print(f"❌ 加密失败: {e}")
        return None

def decrypt_data(encrypted_base64_str):
    """
    【供 C 网关使用】将收到的加密字符串解密回原始的字典
    """
    try:
        cipher = AES.new(SECRET_KEY, AES.MODE_ECB)
        encrypted_bytes = base64.b64decode(encrypted_base64_str)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        json_str = unpad(decrypted_padded_bytes, AES.block_size).decode('utf-8')
        return json.loads(json_str)
    except ValueError:
        print("⚠️ 警告：检测到非法数据或秘钥不匹配，解密被拒绝！")
        return None
    except Exception as e:
        print(f"❌ 解密发生未知错误: {e}")
        return None

# ==========================================
# 本地防呆测试 (直接运行此文件时触发)
# ==========================================
if __name__ == "__main__":
    print(f"🔒 当前秘钥长度: {len(SECRET_KEY)} 字节 (符合 AES-128 规范)")
    
    # 1. 测试 Token 生成
    my_token, my_timestamp = generate_token()
    print(f"\n⏱️ 当前生成的时间戳: {my_timestamp}")
    print(f"🎫 生成的鉴权 Token: {my_token}")
    
    # 2. 测试 AES 加解密
    test_data = {"device_id": "dev_01", "type": "bass_gain", "value": 8}
    print(f"\n📦 原始数据: {test_data}")
    
    encrypted_str = encrypt_data(test_data)
    print(f"🔐 加密结果: {encrypted_str}")
    
    decrypted_dict = decrypt_data(encrypted_str)
    print(f"🔓 解密结果: {decrypted_dict}")