"""
加密模块
处理 RSA 和 AES 加密（参考 fnnas-api 项目）
"""
import base64
import json
import secrets
import hmac
import hashlib
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad


def generate_random_string(length: int = 32) -> str:
    """生成指定长度的密码学安全随机字符串"""
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_iv() -> bytes:
    """生成 16 字节的 IV"""
    return os.urandom(16)


def rsa_encrypt(public_key_pem: str, plaintext: str) -> str:
    """
    RSA 加密（使用 PKCS1_v1_5）
    
    :param public_key_pem: PEM 格式的公钥
    :param plaintext: 要加密的明文
    :return: Base64 编码的密文
    """
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_v1_5.new(key)
    ciphertext = cipher.encrypt(plaintext.encode())
    return base64.b64encode(ciphertext).decode()


def aes_encrypt(data: str, key: str, iv: bytes) -> str:
    """
    AES-CBC 加密
    
    :param data: 要加密的数据
    :param key: 32 字符的密钥字符串
    :param iv: 16 字节的 IV
    :return: Base64 编码的密文
    """
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(ciphertext).decode("utf-8")


def aes_decrypt(ciphertext: str, key: str, iv: bytes) -> str:
    """
    AES-CBC 解密
    
    :param ciphertext: Base64 编码的密文
    :param key: 32 字符的密钥字符串
    :param iv: 16 字节的 IV
    :return: 解密后的明文（Base64 编码，用于签名密钥）
    """
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size)
    return base64.b64encode(decrypted).decode("utf-8")


def encrypt_login_request(data: str, public_key: str, aes_key: str, iv: bytes) -> dict:
    """
    加密登录请求
    
    :param data: JSON 字符串格式的登录数据
    :param public_key: RSA 公钥
    :param aes_key: AES 密钥（32字符）
    :param iv: IV（16字节）
    :return: 加密后的请求数据
    """
    # RSA 加密 AES 密钥
    rsa_encrypted = rsa_encrypt(public_key, aes_key)
    
    # AES 加密请求数据
    aes_encrypted = aes_encrypt(data, aes_key, iv)
    
    return {
        "req": "encrypted",
        "iv": base64.b64encode(iv).decode("utf-8"),
        "rsa": rsa_encrypted,
        "aes": aes_encrypted
    }


def get_signature(data: str, key: str) -> str:
    """
    使用 HMAC-SHA256 计算签名
    
    :param data: 要签名的数据
    :param key: Base64 编码的密钥
    :return: Base64 编码的签名
    """
    key_bytes = base64.b64decode(key)
    hmac_obj = hmac.new(key_bytes, data.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(hmac_obj.digest()).decode("utf-8")


# 不需要签名的请求列表
NO_SIGN_REQUESTS = ["encrypted", "util.getSI", "util.crypto.getRSAPub", "ping"]


def sign_request(data: dict, sign_key: str | None) -> str:
    """
    对请求数据签名（如果需要）
    
    :param data: 请求数据字典
    :param sign_key: 签名密钥（Base64 编码），None 表示不签名
    :return: 签名后的 JSON 字符串（签名+JSON）
    """
    req = data.get("req", "")
    json_str = json.dumps(data, separators=(",", ":"))
    
    if req not in NO_SIGN_REQUESTS and sign_key:
        signature = get_signature(json_str, sign_key)
        return signature + json_str
    
    return json_str
