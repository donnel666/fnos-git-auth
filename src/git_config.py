"""
Git 配置管理模块
负责设置和管理 git extraHeader
"""
import subprocess
import shlex
from typing import Optional


def run_git_command(args: list[str]) -> tuple[bool, str]:
    """运行 git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def set_git_extra_header(server: str, token: str) -> bool:
    """
    设置 git extraHeader（包括通配符以支持子域名）
    
    :param server: 服务器地址
    :param token: entry-token
    :return: 是否成功
    """
    config_value = f"Cookie: entry-token={token}"
    success = True
    
    # 1. 配置主域名
    config_key = f"http.https://{server}.extraHeader"
    ok, _ = run_git_command([
        "config", "--global", config_key, config_value
    ])
    if ok:
        print(f"已配置 git extraHeader: {server}")
    else:
        print(f"配置 git extraHeader 失败: {server}")
        success = False
    
    # 2. 配置通配符以支持所有子域名 (Git 2.13+)
    # 格式: http.https://*.domain.com/.extraHeader
    wildcard_key = f"http.https://*.{server}/.extraHeader"
    ok, _ = run_git_command([
        "config", "--global", wildcard_key, config_value
    ])
    if ok:
        print(f"已配置 git extraHeader (通配符): *.{server}")
    else:
        # 通配符配置失败不影响主配置
        print(f"通配符配置失败（可能 Git 版本不支持）")
    
    return success


def remove_git_extra_header(server: str) -> bool:
    """
    移除 git extraHeader（包括通配符配置）
    
    :param server: 服务器地址
    :return: 是否成功
    """
    # 1. 移除主域名配置
    config_key = f"http.https://{server}.extraHeader"
    success, _ = run_git_command([
        "config", "--global", "--unset", config_key
    ])
    if success:
        print(f"已移除 git extraHeader: {server}")
    
    # 2. 移除通配符配置
    wildcard_key = f"http.https://*.{server}/.extraHeader"
    ok, _ = run_git_command([
        "config", "--global", "--unset", wildcard_key
    ])
    if ok:
        print(f"已移除 git extraHeader (通配符): *.{server}")
    
    return success


def has_git_extra_header(server: str) -> bool:
    """
    检查是否已配置 extraHeader
    
    :param server: 服务器地址
    :return: 是否已配置
    """
    config_key = f"http.https://{server}.extraHeader"
    success, _ = run_git_command([
        "config", "--global", "--get", config_key
    ])
    return success


def get_git_extra_header(server: str) -> Optional[str]:
    """
    获取当前配置的 extraHeader
    
    :param server: 服务器地址
    :return: extraHeader 值或 None
    """
    config_key = f"http.https://{server}.extraHeader"
    success, value = run_git_command([
        "config", "--global", "--get", config_key
    ])
    return value if success else None



