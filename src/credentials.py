"""
凭据管理模块（单用户模式）

凭据文件: ~/.fnos-git-auth/credentials.json
密钥文件: ~/.fnos-git-auth/.key
使用 AES-256-CBC 加密存储密码。
"""
import json
import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, TypedDict
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64


logger = logging.getLogger(__name__)

# 支持环境变量自定义配置目录（与 config.py 保持一致）
CONFIG_DIR = Path(os.environ.get("FNOS_GIT_AUTH_CONFIG_DIR", Path.home() / ".fnos-git-auth"))
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
KEY_FILE = CONFIG_DIR / ".key"


class Credentials(TypedDict):
    """凭据类型"""
    username: str
    password: str


def _set_file_permissions(filepath: Path) -> None:
    """
    设置文件权限（跨平台）
    
    Unix: chmod 600
    Windows: icacls 仅限当前用户
    """
    if platform.system() == 'Windows':
        try:
            username = os.environ.get('USERNAME', os.environ.get('USER', ''))
            if username:
                subprocess.run(
                    ['icacls', str(filepath), '/inheritance:r', '/grant:r', f'{username}:F'],
                    capture_output=True, check=False
                )
        except Exception as e:
            logger.debug(f"设置 Windows 文件权限失败: {e}")
    else:
        try:
            os.chmod(filepath, 0o600)
        except Exception as e:
            logger.debug(f"设置 Unix 文件权限失败: {e}")


def _set_dir_permissions(dirpath: Path) -> None:
    """
    设置目录权限（跨平台）
    
    Unix: chmod 700
    Windows: icacls 仅限当前用户
    """
    if platform.system() == 'Windows':
        try:
            username = os.environ.get('USERNAME', os.environ.get('USER', ''))
            if username:
                subprocess.run(
                    ['icacls', str(dirpath), '/inheritance:r', '/grant:r', f'{username}:F'],
                    capture_output=True, check=False
                )
        except Exception as e:
            logger.debug(f"设置 Windows 目录权限失败: {e}")
    else:
        try:
            os.chmod(dirpath, 0o700)
        except Exception as e:
            logger.debug(f"设置 Unix 目录权限失败: {e}")


def _get_or_create_key() -> bytes:
    """
    获取或创建加密密钥
    
    :return: 32 字节 AES 密钥
    """
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _set_dir_permissions(CONFIG_DIR)
    
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
        if len(key) == 32:
            return key
        # 密钥损坏，重新生成
        logger.warning("密钥文件损坏，重新生成")
    
    key = get_random_bytes(32)
    KEY_FILE.write_bytes(key)
    _set_file_permissions(KEY_FILE)
    return key


def _encrypt(data: str) -> str:
    """加密"""
    key = _get_or_create_key()
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode('utf-8')


def _decrypt(encrypted: str) -> str:
    """解密"""
    key = _get_or_create_key()
    data = base64.b64decode(encrypted)
    iv = data[:16]
    ciphertext = data[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode('utf-8')


def _read_credentials_file() -> dict:
    """读取凭据文件"""
    try:
        if CREDENTIALS_FILE.exists():
            return json.loads(CREDENTIALS_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def _save_credentials_file(data: dict) -> None:
    """保存凭据文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    _set_file_permissions(CREDENTIALS_FILE)


def save_credentials(username: str, password: str) -> None:
    """保存凭据"""
    data = {
        "username": username,
        "password": _encrypt(password)
    }
    _save_credentials_file(data)


def get_credentials() -> Optional[Credentials]:
    """
    获取凭据
    
    :return: 凭据字典或 None（如果不存在或解密失败）
    """
    data = _read_credentials_file()
    
    if not data.get("username") or not data.get("password"):
        return None
    
    try:
        password = _decrypt(data["password"])
        return {
            "username": data["username"],
            "password": password
        }
    except Exception as e:
        logger.debug(f"解密凭据失败: {e}")
        return None


def delete_credentials() -> None:
    """删除凭据"""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
