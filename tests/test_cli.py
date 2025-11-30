"""
CLI 命令测试（单服务器单用户模式）
"""
import pytest
from click.testing import CliRunner
from src.cli import main


@pytest.fixture
def runner():
    """创建 CLI 测试运行器"""
    return CliRunner()


class TestMainCommand:
    """主命令测试"""
    
    def test_help(self, runner):
        """测试 --help"""
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'fnOS Git 认证工具' in result.output
    
    def test_help_short(self, runner):
        """测试 -h"""
        result = runner.invoke(main, ['-h'])
        assert result.exit_code == 0
        assert 'fnOS Git 认证工具' in result.output
    
    def test_version(self, runner):
        """测试 --version"""
        result = runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert 'fnos-git-auth' in result.output
    
    def test_commands_exist(self, runner):
        """测试所有命令存在"""
        result = runner.invoke(main, ['--help'])
        commands = ['login', 'logout', 'status', 'refresh', 'update', 'config', 'git', 'diagnostic']
        for cmd in commands:
            assert cmd in result.output


class TestLoginCommand:
    """login 命令测试"""
    
    def test_login_help(self, runner):
        """测试 login --help"""
        result = runner.invoke(main, ['login', '--help'])
        assert result.exit_code == 0
        assert '-s, --server' in result.output
        assert '-u, --username' in result.output
        assert '-p, --password' in result.output
        assert '-n, --no-save' in result.output
    
    def test_login_help_short(self, runner):
        """测试 login -h"""
        result = runner.invoke(main, ['login', '-h'])
        assert result.exit_code == 0


class TestLogoutCommand:
    """logout 命令测试（单服务器模式：无 server 选项）"""
    
    def test_logout_help(self, runner):
        """测试 logout --help"""
        result = runner.invoke(main, ['logout', '--help'])
        assert result.exit_code == 0
        # 单服务器模式：只有 help 选项
        assert '-h, --help' in result.output


class TestStatusCommand:
    """status 命令测试（单服务器模式：无 server 选项）"""
    
    def test_status_help(self, runner):
        """测试 status --help"""
        result = runner.invoke(main, ['status', '--help'])
        assert result.exit_code == 0
        assert '-h, --help' in result.output


class TestRefreshCommand:
    """refresh 命令测试（单服务器模式：无 server 选项）"""
    
    def test_refresh_help(self, runner):
        """测试 refresh --help"""
        result = runner.invoke(main, ['refresh', '--help'])
        assert result.exit_code == 0
        assert '-h, --help' in result.output


class TestUpdateCommand:
    """update 命令测试"""
    
    def test_update_help(self, runner):
        """测试 update --help"""
        result = runner.invoke(main, ['update', '--help'])
        assert result.exit_code == 0
        assert '-c, --check' in result.output
        assert '-f, --force' in result.output


class TestConfigCommand:
    """config 命令测试"""
    
    def test_config_help(self, runner):
        """测试 config --help"""
        result = runner.invoke(main, ['config', '--help'])
        assert result.exit_code == 0
        assert '-k, --key' in result.output
        assert '-v, --value' in result.output
        assert '-r, --reset' in result.output
    
    def test_config_show_all(self, runner):
        """测试显示所有配置"""
        result = runner.invoke(main, ['config'])
        assert result.exit_code == 0
        assert '当前配置' in result.output


class TestGitCommand:
    """git 命令测试"""
    
    def test_git_help(self, runner):
        """测试 git --help"""
        result = runner.invoke(main, ['git', '--help'])
        assert result.exit_code == 0
        assert '-s, --show' in result.output
        assert '-c, --clear' in result.output
        assert '-r, --remove' in result.output
        assert '-t, --timeout' in result.output


class TestDiagnosticCommand:
    """diagnostic 命令测试"""
    
    def test_diagnostic_help(self, runner):
        """测试 diagnostic --help"""
        result = runner.invoke(main, ['diagnostic', '--help'])
        assert result.exit_code == 0
        assert '-o, --output' in result.output
        assert '-p, --print' in result.output
    
    def test_diagnostic_print(self, runner):
        """测试 diagnostic --print"""
        result = runner.invoke(main, ['diagnostic', '-p'])
        assert result.exit_code == 0
        assert 'system' in result.output
        assert 'tool' in result.output
