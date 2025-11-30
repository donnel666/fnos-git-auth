"""
Git Hooks 管理模块

在登录时设置全局 git hooks，实现自动刷新 token 功能。
登出时移除全局 hooks。
"""
import os
import shutil
import stat
import platform
import subprocess
from pathlib import Path
from typing import Optional

from .config import CONFIG_DIR


# Hooks 目录
HOOKS_DIR = CONFIG_DIR / "hooks"

# Hook 脚本模板 - 在 git 操作前检查并刷新 token
HOOK_SCRIPT_TEMPLATE = '''#!/bin/sh
# fnos-git-auth 自动生成的 hook 脚本
# 作用：在 git 远程操作前自动检查并刷新 token

# 查找 fnos-git-auth 命令
FNOS_GIT_AUTH=""

# 优先使用打包的可执行文件
if command -v fnos-git-auth >/dev/null 2>&1; then
    FNOS_GIT_AUTH="fnos-git-auth"
elif [ -x "$HOME/.local/bin/fnos-git-auth" ]; then
    FNOS_GIT_AUTH="$HOME/.local/bin/fnos-git-auth"
elif [ -x "/usr/local/bin/fnos-git-auth" ]; then
    FNOS_GIT_AUTH="/usr/local/bin/fnos-git-auth"
fi

# 如果找不到命令，静默退出（不阻止 git 操作）
if [ -z "$FNOS_GIT_AUTH" ]; then
    exit 0
fi

# 刷新 token（如果需要）
if ! $FNOS_GIT_AUTH refresh 2>/dev/null; then
    echo "[fnos-git-auth] Token 刷新失败，请检查登录状态" >&2
fi

# 无论刷新是否成功，都允许 git 操作继续
exit 0
'''

def _get_hook_script() -> str:
    """
    获取 hook 脚本内容
    
    注意：Git for Windows 默认使用 Git Bash 运行 hooks，
    因此所有平台统一使用 POSIX shell 脚本。
    """
    return HOOK_SCRIPT_TEMPLATE


def _set_executable(filepath: Path) -> None:
    """设置文件为可执行（Unix）"""
    if platform.system() != 'Windows':
        try:
            current = filepath.stat().st_mode
            filepath.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass


def setup_global_hooks() -> bool:
    """
    设置全局 git hooks
    
    :return: 是否成功
    """
    try:
        # 检查是否有用户自定义的 hooksPath
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'core.hooksPath'],
            capture_output=True, text=True, timeout=10
        )
        current_path = result.stdout.strip()
        
        if current_path:
            hooks_dir_normalized = _normalize_path(str(HOOKS_DIR))
            current_path_normalized = _normalize_path(current_path)
            
            # 如果已经是我们的 hooks 路径，只更新脚本
            if hooks_dir_normalized != current_path_normalized:
                # 用户有自定义 hooks，警告并备份信息
                print(f"警告: 检测到已有自定义 hooks 路径: {current_path}")
                print(f"将被覆盖为: {HOOKS_DIR}")
        
        # 创建 hooks 目录
        HOOKS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 创建 hook 脚本（Git hooks 不需要扩展名）
        hook_script = _get_hook_script()
        
        # 创建多个 hook 来覆盖不同的远程操作场景
        hooks = ['pre-push', 'pre-auto-gc']
        
        for hook_name in hooks:
            hook_file = HOOKS_DIR / hook_name
            hook_file.write_text(hook_script, encoding='utf-8')
            _set_executable(hook_file)
        
        # 设置 git 全局 hooks 路径
        result = subprocess.run(
            ['git', 'config', '--global', 'core.hooksPath', str(HOOKS_DIR)],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print(f"已设置全局 git hooks: {HOOKS_DIR}")
            return True
        else:
            print(f"设置全局 hooks 失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"设置全局 hooks 出错: {e}")
        return False


def _normalize_path(path: str) -> str:
    """
    标准化路径（统一使用正斜杠，便于跨平台比较）
    
    :param path: 原始路径
    :return: 标准化后的路径（小写，正斜杠，去除尾部斜杠）
    """
    # 统一使用正斜杠，去除尾部斜杠，转为小写以忽略大小写差异
    return path.replace('\\', '/').rstrip('/').lower()


def remove_global_hooks() -> bool:
    """
    移除全局 git hooks 配置并删除 hooks 目录
    
    :return: 是否成功
    """
    try:
        # 检查当前 hooksPath 是否是我们设置的
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'core.hooksPath'],
            capture_output=True, text=True, timeout=10
        )
        
        current_path = result.stdout.strip()
        
        # 标准化路径后比较（解决 Windows 路径格式问题）
        hooks_dir_normalized = _normalize_path(str(HOOKS_DIR))
        current_path_normalized = _normalize_path(current_path) if current_path else ""
        
        # 只移除我们自己设置的 hooks（精确匹配）
        if current_path_normalized and hooks_dir_normalized == current_path_normalized:
            subprocess.run(
                ['git', 'config', '--global', '--unset', 'core.hooksPath'],
                capture_output=True, text=True, timeout=10
            )
            print("已移除全局 git hooks 配置")
        
        # 删除 hooks 目录（清理残留脚本）
        if HOOKS_DIR.exists():
            shutil.rmtree(HOOKS_DIR, ignore_errors=True)
            print(f"已删除 hooks 目录: {HOOKS_DIR}")
        
        return True
        
    except Exception as e:
        print(f"移除全局 hooks 出错: {e}")
        return False


def has_global_hooks() -> bool:
    """
    检查是否已配置全局 hooks
    
    :return: 是否已配置
    """
    try:
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'core.hooksPath'],
            capture_output=True, text=True, timeout=10
        )
        current_path = result.stdout.strip()
        if current_path:
            # 标准化路径后精确比较（解决 Windows 路径格式问题）
            hooks_dir_normalized = _normalize_path(str(HOOKS_DIR))
            current_path_normalized = _normalize_path(current_path)
            return hooks_dir_normalized == current_path_normalized
        return False
    except Exception:
        return False


def get_hooks_status() -> dict:
    """
    获取 hooks 状态信息
    
    :return: 状态字典
    """
    status = {
        'enabled': False,
        'hooks_dir': str(HOOKS_DIR),
        'hooks': []
    }
    
    try:
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'core.hooksPath'],
            capture_output=True, text=True, timeout=10
        )
        current_path = result.stdout.strip()
        
        if current_path:
            # 标准化路径后比较（解决 Windows 路径格式问题）
            hooks_dir_normalized = _normalize_path(str(HOOKS_DIR))
            current_path_normalized = _normalize_path(current_path)
            
            if hooks_dir_normalized == current_path_normalized:
                status['enabled'] = True
                
                # 列出已安装的 hooks
                if HOOKS_DIR.exists():
                    for f in HOOKS_DIR.iterdir():
                        if f.is_file() and not f.name.startswith('.'):
                            status['hooks'].append(f.name)
    except Exception:
        pass
    
    return status
