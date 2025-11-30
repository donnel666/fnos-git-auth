"""
配置模块单元测试（单服务器单用户模式）
"""
import pytest
import sys
sys.path.insert(0, ".")

from src.config import (
    read_config,
    save_config,
    get_server_config,
    save_server_config,
    delete_server_config,
    is_token_expired,
    token_needs_refresh,
)
from datetime import datetime, timedelta


class TestConfig:
    """测试配置管理"""
    
    def test_save_and_read_config(self, temp_config_dir):
        """测试保存和读取配置"""
        config = {"server": {"url": "test.server", "username": "test"}}
        save_config(config)
        
        loaded = read_config()
        assert loaded == config
    
    def test_get_server_config(self, temp_config_dir):
        """测试获取服务器配置"""
        save_server_config("test.server", username="testuser", fnos_token="abc123")
        
        result = get_server_config()
        assert result["url"] == "test.server"
        assert result["username"] == "testuser"
        assert result["fnos_token"] == "abc123"
    
    def test_delete_server_config(self, temp_config_dir):
        """测试删除服务器配置"""
        save_server_config("test.server", username="test")
        assert get_server_config() is not None
        
        delete_server_config()
        # delete_server_config 保留 url，所以仍有配置
        config = get_server_config()
        assert config is not None
        assert config.get("url") == "test.server"
        assert config.get("username") is None
    
    def test_preferences_auto_created(self, temp_config_dir):
        """测试保存服务器配置时自动创建 preferences 对象"""
        save_server_config("test.server", username="test")
        
        config = read_config()
        assert "preferences" in config
        assert isinstance(config["preferences"], dict)


class TestTokenExpiration:
    """测试 token 过期检查"""
    
    def test_is_token_expired_true(self, temp_config_dir):
        """测试已过期的 token"""
        expired_time = (datetime.now() - timedelta(hours=1)).isoformat()
        save_server_config("test.server",
            username="test",
            expires_at=expired_time
        )
        
        assert is_token_expired() is True
    
    def test_is_token_expired_false(self, temp_config_dir):
        """测试未过期的 token"""
        future_time = (datetime.now() + timedelta(hours=24)).isoformat()
        save_server_config("test.server",
            username="test",
            expires_at=future_time
        )
        
        assert is_token_expired() is False
    
    def test_token_needs_refresh(self, temp_config_dir):
        """测试 token 需要刷新"""
        # 30 分钟后过期（小于 1 小时阈值）
        near_expiry = (datetime.now() + timedelta(minutes=30)).isoformat()
        save_server_config("test.server",
            username="test",
            expires_at=near_expiry
        )
        
        assert token_needs_refresh() is True
    
    def test_token_not_needs_refresh(self, temp_config_dir):
        """测试 token 不需要刷新"""
        # 2 小时后过期（大于 1 小时阈值）
        far_expiry = (datetime.now() + timedelta(hours=2)).isoformat()
        save_server_config("test.server",
            username="test",
            expires_at=far_expiry
        )
        
        assert token_needs_refresh() is False
