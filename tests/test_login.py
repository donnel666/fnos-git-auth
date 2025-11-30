#!/usr/bin/env python3
"""
登录功能集成测试脚本（单服务器单用户模式）

这是一个需要真实服务器的集成测试脚本，不作为 pytest 自动测试运行。

用法:
  uv run python tests/test_login.py <server> <username> <password>

示例:
  uv run python tests/test_login.py your-server.fnos.net your_username your_password
"""
import sys
import asyncio
import pytest

# 添加项目根目录到路径
sys.path.insert(0, ".")

from src.ws_client import FnOsClient
from src.auth import do_login, show_status, do_logout
from src.config import get_server_config, get_server
from src.git_config import get_git_extra_header


# 这些测试需要真实服务器，标记为跳过
pytestmark = pytest.mark.skip(reason="需要真实服务器，作为独立脚本运行: python tests/test_login.py <server> <username> <password>")


async def _test_ws_connection(server: str):
    """测试 WebSocket 连接"""
    print("\n[1/5] 测试 WebSocket 连接...")
    client = FnOsClient()
    try:
        await client.connect(server)
        print(f"  ✅ 连接成功")
        return client
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        raise


async def _test_get_pub_key(client: FnOsClient):
    """测试获取公钥"""
    print("\n[2/5] 测试获取 RSA 公钥...")
    try:
        response = await client.get_rsa_pub()
        print(f"  ✅ 公钥获取成功")
        print(f"  SI: {client.si}")
        print(f"  公钥: {client.pub[:50]}...")
    except Exception as e:
        print(f"  ❌ 获取公钥失败: {e}")
        raise


async def _test_login(client: FnOsClient, username: str, password: str):
    """测试登录"""
    print("\n[3/5] 测试登录...")
    try:
        response = await client.login(username, password, stay=True)
        print(f"  ✅ 登录成功")
        print(f"  Token: {'已获取' if client.token else '无'}")
        print(f"  UID: {client.uid}")
        print(f"  BackId: {client.back_id}")
        return response
    except Exception as e:
        print(f"  ❌ 登录失败: {e}")
        raise


async def _test_full_login_flow(server: str, username: str, password: str):
    """测试完整登录流程（通过 CLI 模块）"""
    print("\n[4/5] 测试完整登录流程...")
    try:
        await do_login(server, username, password, save_creds=False)
        print(f"  ✅ 完整登录流程成功")
    except Exception as e:
        print(f"  ❌ 完整登录流程失败: {e}")
        raise


def _test_config_saved(server: str):
    """测试配置是否保存"""
    print("\n[5/5] 测试配置保存...")
    
    # 单服务器模式：不需要传入 server 参数
    config = get_server_config()
    saved_server = get_server()
    
    if config and saved_server == server:
        print(f"  ✅ 配置已保存")
        print(f"  服务器: {saved_server}")
        print(f"  用户名: {config.get('username')}")
        print(f"  entry_token: {'已配置' if config.get('entry_token') else '无'}")
        print(f"  过期时间: {config.get('expires_at')}")
    else:
        print(f"  ❌ 配置未保存")
    
    # 检查 git 配置
    header = get_git_extra_header(server)
    if header:
        print(f"  ✅ Git extraHeader 已配置")
    else:
        print(f"  ⚠️ Git extraHeader 未配置")


async def main():
    if len(sys.argv) < 4:
        print("用法: uv run python tests/test_login.py <server> <username> <password>")
        print("例如: uv run python tests/test_login.py your-server.fnos.net your_user your_pass")
        sys.exit(1)
    
    server = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    print("=" * 50)
    print("fnOS 登录功能测试")
    print("=" * 50)
    print(f"服务器: {server}")
    print(f"用户名: {username}")
    
    client = None
    try:
        # 测试 1-3: WebSocket 连接和登录
        client = await _test_ws_connection(server)
        await _test_get_pub_key(client)
        await _test_login(client, username, password)
        await client.close()
        client = None
        
        # 测试 4-5: 完整流程和配置保存
        await _test_full_login_flow(server, username, password)
        _test_config_saved(server)
        
        print("\n" + "=" * 50)
        print("所有测试通过! ✅")
        print("=" * 50)
        
        # 显示状态（单服务器模式，不需要参数）
        print("\n当前认证状态:")
        show_status()
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if client:
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
