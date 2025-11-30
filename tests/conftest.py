"""
pytest 配置文件

提供测试隔离的 fixture，避免污染真实环境。
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_config_dir(tmp_path):
    """临时配置目录（隔离 config.py 和 credentials.py）"""
    import src.config as config_module
    import src.credentials as credentials_module
    import src.git_hooks as git_hooks_module
    
    # 保存原始值
    original_config_dir = config_module.CONFIG_DIR
    original_config_file = config_module.CONFIG_FILE
    original_cred_dir = credentials_module.CONFIG_DIR
    original_cred_file = credentials_module.CREDENTIALS_FILE
    original_key_file = credentials_module.KEY_FILE
    original_hooks_dir = git_hooks_module.HOOKS_DIR
    
    # 使用临时目录
    config_module.CONFIG_DIR = tmp_path
    config_module.CONFIG_FILE = tmp_path / "config.json"
    credentials_module.CONFIG_DIR = tmp_path
    credentials_module.CREDENTIALS_FILE = tmp_path / "credentials.json"
    credentials_module.KEY_FILE = tmp_path / ".key"
    git_hooks_module.HOOKS_DIR = tmp_path / "hooks"
    
    yield tmp_path
    
    # 恢复原始值
    config_module.CONFIG_DIR = original_config_dir
    config_module.CONFIG_FILE = original_config_file
    credentials_module.CONFIG_DIR = original_cred_dir
    credentials_module.CREDENTIALS_FILE = original_cred_file
    credentials_module.KEY_FILE = original_key_file
    git_hooks_module.HOOKS_DIR = original_hooks_dir
