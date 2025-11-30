"""
Git Hooks 模块测试
"""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.git_hooks import (
    HOOKS_DIR,
    setup_global_hooks,
    remove_global_hooks,
    has_global_hooks,
    get_hooks_status,
    _get_hook_script,
)


class TestHookScript:
    """测试 hook 脚本生成"""
    
    def test_hook_script_not_empty(self):
        """测试 hook 脚本不为空"""
        script = _get_hook_script()
        assert len(script) > 0
    
    def test_hook_script_has_shebang(self):
        """测试 Unix hook 脚本有 shebang"""
        import platform
        if platform.system() != 'Windows':
            script = _get_hook_script()
            assert script.startswith('#!/bin/sh')
    
    def test_hook_script_has_refresh_command(self):
        """测试 hook 脚本包含 refresh 命令"""
        script = _get_hook_script()
        assert 'refresh' in script


class TestHooksStatus:
    """测试 hooks 状态查询"""
    
    def test_get_hooks_status_returns_dict(self):
        """测试 get_hooks_status 返回字典"""
        status = get_hooks_status()
        assert isinstance(status, dict)
        assert 'enabled' in status
        assert 'hooks_dir' in status
        assert 'hooks' in status
    
    def test_hooks_dir_is_correct(self):
        """测试 hooks 目录路径正确"""
        status = get_hooks_status()
        assert '.fnos-git-auth' in status['hooks_dir']
        assert 'hooks' in status['hooks_dir']


class TestHooksSetupRemove:
    """测试 hooks 设置和移除（需要 git 环境）"""
    
    @pytest.fixture(autouse=True)
    def save_and_restore_hooks_config(self):
        """保存并恢复用户原有的 git hooks 配置"""
        import subprocess
        
        # 保存原有配置
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'core.hooksPath'],
            capture_output=True, text=True
        )
        original_hooks_path = result.stdout.strip() if result.returncode == 0 else None
        
        yield
        
        # 恢复原有配置
        remove_global_hooks()
        if original_hooks_path:
            subprocess.run(
                ['git', 'config', '--global', 'core.hooksPath', original_hooks_path],
                capture_output=True, text=True
            )
    
    def test_setup_creates_hooks_dir(self):
        """测试 setup 创建 hooks 目录"""
        # 先移除可能存在的配置
        remove_global_hooks()
        
        # 设置 hooks
        result = setup_global_hooks()
        assert result is True
        assert HOOKS_DIR.exists()
    
    def test_setup_creates_hook_files(self):
        """测试 setup 创建 hook 文件"""
        setup_global_hooks()
        
        # 检查 hook 文件
        hooks = list(HOOKS_DIR.glob('*'))
        assert len(hooks) > 0
    
    def test_has_global_hooks_after_setup(self):
        """测试 setup 后 has_global_hooks 返回 True"""
        setup_global_hooks()
        assert has_global_hooks() is True
    
    def test_remove_clears_hooks(self):
        """测试 remove 清除 hooks 配置"""
        setup_global_hooks()
        assert has_global_hooks() is True
        
        remove_global_hooks()
        assert has_global_hooks() is False
