"""
配置管理模块（单服务器单用户模式）
配置文件: ~/.fnos-git-auth/config.json
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import TypedDict, Optional

# 配置目录
CONFIG_DIR = Path(os.environ.get("FNOS_GIT_AUTH_CONFIG_DIR", Path.home() / ".fnos-git-auth"))
CONFIG_FILE = CONFIG_DIR / "config.json"


# ========== 默认用户偏好 ==========
DEFAULT_PREFERENCES = {
    "timeout": 30.0,
    "device_type": "Browser",
    "device_name": "fnos-git-auth",
    "language": "zh",
    "token_expire_hours": 24,
    "token_refresh_threshold_hours": 1.0,
    "fn_connect_cookie": "mode=relay; language=zh",
    "use_ssl": True,
    "auto_save_credentials": True,
    "auto_refresh_token": True,
}


class ServerConfig(TypedDict, total=False):
    """服务器配置"""
    url: str
    username: str
    # Token 相关
    fnos_token: str  # 短期会话token，用于 authToken 验证
    fnos_token_expires_at: str  # fnos_token 过期时间
    long_token: str  # 长期token，用于刷新 fnos_token
    long_token_expires_at: str  # long_token 过期时间（通常30天）
    entry_token: str  # HTTP认证token，git使用
    entry_token_expires_at: str  # entry_token 过期时间
    sign_key: str  # 签名密钥（Base64编码），用于签名WebSocket请求
    # 用户信息
    uid: int
    admin: bool
    back_id: str  # WebSocket请求的backId
    # 时间戳
    last_login: str  # 最后登录时间
    # 兼容旧字段
    expires_at: str  # 已废弃，保留兼容


class Config(TypedDict, total=False):
    """主配置"""
    server: ServerConfig
    preferences: dict


def ensure_config_dir() -> None:
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def read_config() -> Config:
    """读取配置"""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"读取配置文件失败: {e}")
    return {}


def save_config(config: Config) -> None:
    """保存配置"""
    try:
        ensure_config_dir()
        CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        raise


# ========== 服务器配置 ==========

def get_server() -> Optional[str]:
    """获取当前服务器地址"""
    config = read_config()
    server = config.get("server", {})
    return server.get("url")


def get_server_config() -> Optional[ServerConfig]:
    """获取服务器配置"""
    config = read_config()
    return config.get("server")


def save_server_config(url: str, update_last_login: bool = True, **kwargs) -> None:
    """
    保存服务器配置
    
    :param url: 服务器地址
    :param update_last_login: 是否更新 last_login（刷新 token 时应为 False）
    """
    config = read_config()
    server = config.get("server", {})
    server["url"] = url
    if update_last_login:
        server["last_login"] = datetime.now().isoformat()
    server.update(kwargs)
    config["server"] = server
    # 确保 preferences 对象存在
    if "preferences" not in config:
        config["preferences"] = {}
    save_config(config)


def delete_server_config() -> None:
    """删除服务器配置（保留 url）"""
    config = read_config()
    server = config.get("server", {})
    url = server.get("url")
    if url:
        config["server"] = {"url": url}
    else:
        config.pop("server", None)
    save_config(config)


def _check_expires_at(expires_at_str: Optional[str]) -> bool:
    """
    检查给定的过期时间是否已过期
    
    :param expires_at_str: ISO格式的过期时间字符串
    :return: True 表示已过期或无效
    """
    if not expires_at_str:
        return True
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        return datetime.now() > expires_at
    except (ValueError, TypeError):
        return True


def is_entry_token_expired() -> bool:
    """检查 entry_token 是否已过期"""
    config = get_server_config()
    if not config:
        return True
    # 优先使用新字段，兼容旧字段
    expires_at = config.get("entry_token_expires_at") or config.get("expires_at")
    return _check_expires_at(expires_at)


def is_fnos_token_expired() -> bool:
    """检查 fnos_token 是否已过期"""
    config = get_server_config()
    if not config:
        return True
    expires_at = config.get("fnos_token_expires_at")
    # 如果没有专门的fnos_token过期时间，使用通用的expires_at
    if not expires_at:
        expires_at = config.get("expires_at")
    return _check_expires_at(expires_at)


def is_long_token_expired() -> bool:
    """检查 long_token 是否已过期"""
    config = get_server_config()
    if not config:
        return True
    return _check_expires_at(config.get("long_token_expires_at"))


def is_token_expired() -> bool:
    """
    检查 token 是否过期（兼容旧API）
    
    :return: True 表示 entry_token 已过期或无效配置
    """
    return is_entry_token_expired()


def token_needs_refresh() -> bool:
    """
    检查 entry_token 是否需要刷新（即将过期）
    
    :return: True 表示 token 即将过期，建议刷新
    """
    config = get_server_config()
    if not config:
        return False
    
    # 优先使用新字段，兼容旧字段
    expires_at_str = config.get("entry_token_expires_at") or config.get("expires_at")
    if not expires_at_str:
        return False
    
    threshold_hours = get_preference("token_refresh_threshold_hours", 1.0)
    
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        threshold = timedelta(hours=threshold_hours)
        return datetime.now() > (expires_at - threshold)
    except (ValueError, TypeError):
        return False


def get_token_status() -> dict:
    """
    获取所有token的状态
    
    :return: 包含各token过期状态的字典
    """
    config = get_server_config()
    if not config:
        return {"logged_in": False}
    
    return {
        "logged_in": bool(config.get("fnos_token") or config.get("long_token")),
        "entry_token_expired": is_entry_token_expired(),
        "fnos_token_expired": is_fnos_token_expired(),
        "long_token_expired": is_long_token_expired(),
        "has_credentials": bool(config.get("username")),
    }


# ========== 用户偏好 ==========

def get_preferences() -> dict:
    """获取所有用户偏好"""
    config = read_config()
    prefs = config.get("preferences", {})
    return {**DEFAULT_PREFERENCES, **prefs}


def get_preference(key: str, default=None):
    """获取单个用户偏好"""
    prefs = get_preferences()
    return prefs.get(key, DEFAULT_PREFERENCES.get(key, default))


def set_preference(key: str, value) -> None:
    """设置单个用户偏好"""
    config = read_config()
    if "preferences" not in config:
        config["preferences"] = {}
    config["preferences"][key] = value
    save_config(config)


def reset_preferences() -> None:
    """重置用户偏好"""
    config = read_config()
    config["preferences"] = {}
    save_config(config)


# ========== 兼容旧 API（供其他模块调用）==========

def get_current_server() -> Optional[str]:
    """获取当前服务器（兼容旧 API）"""
    return get_server()


def set_current_server(server: str) -> None:
    """设置当前服务器（兼容旧 API）"""
    config = read_config()
    if "server" not in config:
        config["server"] = {}
    config["server"]["url"] = server
    save_config(config)
