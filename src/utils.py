"""
工具函数模块
"""
import subprocess
import shutil
import sys


def check_git_installed() -> tuple[bool, str]:
    """
    检查 Git 是否已安装
    
    :return: (是否安装, 版本信息或错误消息)
    """
    # 方法1: 使用 shutil.which（跨平台）
    git_path = shutil.which("git")
    if not git_path:
        return False, "Git 未安装或不在 PATH 中"
    
    # 方法2: 尝试执行 git --version
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Git 执行失败: {result.stderr}"
    except FileNotFoundError:
        return False, "Git 未安装"
    except subprocess.TimeoutExpired:
        return False, "Git 响应超时"
    except Exception as e:
        return False, f"检测 Git 时出错: {e}"


def require_git() -> None:
    """
    要求 Git 必须安装，否则退出程序
    """
    installed, message = check_git_installed()
    if not installed:
        print(f"错误: {message}")
        print()
        print("本工具需要 Git 才能工作。请先安装 Git:")
        print()
        print("  Linux (Debian/Ubuntu):")
        print("    sudo apt install git")
        print()
        print("  Linux (RHEL/CentOS):")
        print("    sudo yum install git")
        print()
        print("  macOS:")
        print("    brew install git")
        print("    # 或安装 Xcode Command Line Tools")
        print()
        print("  Windows:")
        print("    https://git-scm.com/download/win")
        print("    # 或使用 winget: winget install Git.Git")
        print()
        sys.exit(1)


def get_git_version() -> str | None:
    """获取 Git 版本号（如果已安装）"""
    installed, message = check_git_installed()
    if installed:
        # 解析版本号，如 "git version 2.34.1" -> "2.34.1"
        parts = message.split()
        if len(parts) >= 3:
            return parts[2]
        return message
    return None
