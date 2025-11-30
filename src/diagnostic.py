"""
诊断信息收集模块
用于收集环境信息打包成 tar，方便用户提交 issue
所有敏感数据会自动脱敏
"""
import json
import os
import platform
import subprocess
import tarfile
import tempfile
import re
from pathlib import Path
from datetime import datetime
from typing import Any


# 敏感字段列表（需要脱敏）
SENSITIVE_FIELDS = [
    "password", "token", "secret", "key", "credential",
    "fnos_token", "long_token", "entry_token", "sign_key"
]

# 敏感字段值的最小长度（短于此长度的不脱敏，避免误脱敏）
MIN_SENSITIVE_LENGTH = 8


def mask_sensitive_value(value: str, show_prefix: int = 4) -> str:
    """
    脱敏敏感值
    
    :param value: 原始值
    :param show_prefix: 显示的前缀字符数
    :return: 脱敏后的值
    """
    if not value or len(value) < MIN_SENSITIVE_LENGTH:
        return value
    
    if len(value) <= show_prefix * 2:
        return "*" * len(value)
    
    return value[:show_prefix] + "*" * (len(value) - show_prefix * 2) + value[-show_prefix:]


def sanitize_dict(data: dict, mask_keys: list[str] = None) -> dict:
    """
    递归脱敏字典中的敏感数据
    
    :param data: 原始数据
    :param mask_keys: 需要脱敏的键列表
    :return: 脱敏后的数据
    """
    if mask_keys is None:
        mask_keys = SENSITIVE_FIELDS
    
    result = {}
    for key, value in data.items():
        # 检查键名是否包含敏感字段
        is_sensitive = any(s in key.lower() for s in mask_keys)
        
        if isinstance(value, dict):
            result[key] = sanitize_dict(value, mask_keys)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(v, mask_keys) if isinstance(v, dict) else v
                for v in value
            ]
        elif isinstance(value, str) and is_sensitive:
            result[key] = mask_sensitive_value(value)
        else:
            result[key] = value
    
    return result


def get_system_info() -> dict:
    """收集系统信息"""
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def get_git_info() -> dict:
    """收集 Git 信息"""
    info = {"installed": False, "version": None, "config": {}}
    
    try:
        # Git 版本
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["installed"] = True
            info["version"] = result.stdout.strip()
        
        # Git 配置（脱敏）
        result = subprocess.run(
            ["git", "config", "--global", "--list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    # 脱敏 extraheader 中的 token
                    if "extraheader" in key.lower() and "token" in value.lower():
                        # 替换 token 值
                        value = re.sub(
                            r'(entry-token=)([a-zA-Z0-9]+)',
                            lambda m: m.group(1) + mask_sensitive_value(m.group(2)),
                            value
                        )
                    info["config"][key] = value
    except Exception as e:
        info["error"] = str(e)
    
    return info


def get_tool_info() -> dict:
    """收集工具信息"""
    from . import __version__
    from .config import CONFIG_DIR, CONFIG_FILE
    
    return {
        "version": __version__,
        "config_dir": str(CONFIG_DIR),
        "config_file_exists": CONFIG_FILE.exists(),
    }


def get_config_info() -> dict:
    """收集配置信息（脱敏）"""
    from .config import read_config, get_preferences
    
    config = read_config()
    
    # 脱敏服务器配置
    sanitized_config = sanitize_dict(config)
    
    # 添加用户偏好
    sanitized_config["preferences_merged"] = get_preferences()
    
    return sanitized_config


def get_environment_info() -> dict:
    """收集环境变量信息（只收集相关的，脱敏）"""
    relevant_vars = [
        "PATH", "HOME", "USER", "SHELL",
        "LANG", "LC_ALL", "TERM",
        "FNOS_GIT_AUTH_CONFIG_DIR",
        "FNOS_GIT_AUTH_DIR", "FNOS_GIT_AUTH_BIN"
    ]
    
    env_info = {}
    for var in relevant_vars:
        value = os.environ.get(var)
        if value:
            # 脱敏 PATH 中的用户名
            if var == "PATH":
                value = re.sub(r'/home/[^/:]+', '/home/****', value)
                value = re.sub(r'/Users/[^/:]+', '/Users/****', value)
                # Windows 路径需要特殊处理
                value = re.sub(r'C:\\\\Users\\\\[^\\\\:]+', 'C:\\\\Users\\\\****', value)
            env_info[var] = value
    
    return env_info


def collect_diagnostic_info() -> dict:
    """收集所有诊断信息"""
    return {
        "generated_at": datetime.now().isoformat(),
        "system": get_system_info(),
        "git": get_git_info(),
        "tool": get_tool_info(),
        "config": get_config_info(),
        "environment": get_environment_info(),
    }


def create_diagnostic_package(output_path: str = None) -> str:
    """
    创建诊断信息包
    
    :param output_path: 输出路径（None 则使用当前目录）
    :return: 生成的 tar 文件路径
    """
    # 收集信息
    info = collect_diagnostic_info()
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tar_name = f"fnos-git-auth-diagnostic-{timestamp}.tar.gz"
    
    if output_path:
        tar_path = Path(output_path) / tar_name
    else:
        tar_path = Path.cwd() / tar_name
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 写入诊断信息
        info_file = temp_path / "diagnostic_info.json"
        info_file.write_text(
            json.dumps(info, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # 写入 README
        readme = temp_path / "README.txt"
        readme.write_text(
            "fnos-git-auth 诊断信息包\n"
            "========================\n\n"
            "此文件包含您的系统环境和工具配置信息，用于帮助排查问题。\n\n"
            "注意：所有敏感信息（token、密码等）已自动脱敏。\n\n"
            "请将此文件上传到 GitHub Issue 或发送给开发者。\n\n"
            f"生成时间: {info['generated_at']}\n",
            encoding="utf-8"
        )
        
        # 创建 tar.gz
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(info_file, arcname="diagnostic_info.json")
            tar.add(readme, arcname="README.txt")
    
    return str(tar_path)


def print_diagnostic_info() -> None:
    """打印诊断信息到控制台"""
    info = collect_diagnostic_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))
