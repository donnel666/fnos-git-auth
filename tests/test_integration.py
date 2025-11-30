#!/usr/bin/env python3
"""
集成测试脚本（不依赖真实服务器）

注意：需要真实服务器的测试（login, clone, push 等）已移除，
可在本地环境单独运行 tests/test_login.py 进行完整测试。
"""
import subprocess
import sys
import os
import tempfile
import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 临时配置目录（避免污染真实环境）
_temp_config_dir = None


@pytest.fixture(scope="module", autouse=True)
def temp_config_environment():
    """使用临时配置目录，避免污染真实环境"""
    global _temp_config_dir
    _temp_config_dir = tempfile.mkdtemp(prefix="fnos-git-auth-test-")
    os.environ["FNOS_GIT_AUTH_CONFIG_DIR"] = _temp_config_dir
    yield
    # 清理
    import shutil
    if _temp_config_dir and os.path.exists(_temp_config_dir):
        shutil.rmtree(_temp_config_dir, ignore_errors=True)
    os.environ.pop("FNOS_GIT_AUTH_CONFIG_DIR", None)
    _temp_config_dir = None


def run_cmd(cmd: str, check: bool = True) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    env = os.environ.copy()
    if _temp_config_dir:
        env["FNOS_GIT_AUTH_CONFIG_DIR"] = _temp_config_dir
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env
    )
    if check and result.returncode != 0:
        print(f"命令失败: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
    return result.returncode, result.stdout, result.stderr


def test_config_show():
    """测试显示配置"""
    code, out, _ = run_cmd("python main.py config", check=False)
    assert code == 0
    assert "auto_save_credentials" in out
    assert "auto_refresh_token" in out


def test_config_set_and_get():
    """测试设置和获取配置"""
    # 设置配置
    code, _, _ = run_cmd("python main.py config -k timeout -v 45.0", check=False)
    assert code == 0
    
    # 验证设置
    code, out, _ = run_cmd("python main.py config -k timeout", check=False)
    assert code == 0
    assert "45" in out
    
    # 恢复默认值
    run_cmd("python main.py config -k timeout -v 30.0", check=False)


def test_config_invalid_key():
    """测试设置无效配置项"""
    code, out, err = run_cmd("python main.py config -k invalid_key_xxx -v test", check=False)
    assert code != 0
    assert "未知配置项" in err or "未知配置项" in out


def test_config_reset():
    """测试重置配置"""
    # 先设置一个值
    run_cmd("python main.py config -k timeout -v 99.0", check=False)
    
    # 重置
    code, out, _ = run_cmd("python main.py config -r", check=False)
    assert code == 0
    
    # 验证重置
    code, out, _ = run_cmd("python main.py config -k timeout", check=False)
    assert code == 0
    assert "30" in out  # 默认值


def test_status_not_logged_in():
    """测试未登录状态"""
    code, out, _ = run_cmd("python main.py status", check=False)
    assert code == 0
    assert "未登录" in out


def test_refresh_not_logged_in():
    """测试未登录时刷新"""
    code, out, err = run_cmd("python main.py refresh", check=False)
    assert code != 0
    assert "未登录" in err or "未登录" in out


def test_logout_not_logged_in():
    """测试未登录时登出"""
    code, out, err = run_cmd("python main.py logout", check=False)
    assert code != 0
    assert "未登录" in err or "未登录" in out


def test_git_show():
    """测试显示 git 配置"""
    code, out, _ = run_cmd("python main.py git -s", check=False)
    assert code == 0
    # 可能显示 "未配置" 或已有配置
    assert "extraHeader" in out or "未配置" in out


def test_auto_options_default():
    """测试自动化选项默认值"""
    code, out, _ = run_cmd("python main.py config -k auto_save_credentials", check=False)
    assert code == 0
    assert "True" in out
    
    code, out, _ = run_cmd("python main.py config -k auto_refresh_token", check=False)
    assert code == 0
    assert "True" in out


def test_diagnostic_print():
    """测试诊断信息打印"""
    code, out, _ = run_cmd("python main.py diagnostic -p", check=False)
    assert code == 0
    assert "system" in out
    assert "tool" in out
