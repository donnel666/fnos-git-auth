"""
认证模块（单服务器单用户模式）

负责登录、登出、状态显示、token 刷新等核心认证功能。
"""
from datetime import datetime, timedelta
from typing import Optional

from .ws_client import FnOsClient
from .config import (
    get_server,
    get_server_config,
    save_server_config,
    delete_server_config,
    is_token_expired,
    is_fnos_token_expired,
    is_long_token_expired,
    token_needs_refresh,
    get_preference
)
from .git_config import set_git_extra_header, remove_git_extra_header, has_git_extra_header
from .credentials import get_credentials
from .git_hooks import setup_global_hooks, remove_global_hooks, has_global_hooks


async def do_login(
    server: str,
    username: str,
    password: str,
    save_creds: Optional[bool] = None
) -> None:
    """
    执行登录
    
    :param server: 服务器地址
    :param username: 用户名
    :param password: 密码
    :param save_creds: 是否保存凭据（None 使用配置默认值）
    :raises RuntimeError: 登录失败时抛出
    """
    if save_creds is None:
        save_creds = get_preference("auto_save_credentials", True)
    
    client: Optional[FnOsClient] = None
    
    try:
        client = FnOsClient()
        print(f"正在连接到 {server}...")
        await client.connect(server)
        
        print("正在获取公钥...")
        await client.get_rsa_pub()
        
        print("正在验证凭据...")
        response = await client.login(username, password, stay=True)
        
        fnos_token = client.token
        long_token = response.get("longToken")
        
        # 获取 entry-token
        entry_token = None
        entry_token_warning = False
        try:
            print("正在获取 entry-token...")
            entry_response = await client.exchange_entry_token()
            entry_data = entry_response.get("data", {})
            entry_token = entry_data.get("token") if isinstance(entry_data, dict) else None
            if entry_token:
                print("成功获取 entry-token")
        except Exception as e:
            print(f"获取 entry-token 失败: {e}")
        
        if not entry_token:
            print("警告: 使用 fnos-token 作为备选，git push 可能会遇到 403 错误")
            entry_token = fnos_token
            entry_token_warning = True
        
        if not fnos_token:
            raise RuntimeError("登录失败: 服务器未返回 token")
        
        # 计算各token的过期时间
        now = datetime.now()
        # entry_token 过期时间（默认8小时）
        entry_token_expire_hours = get_preference("entry_token_expire_hours", 8)
        entry_token_expires_at = (now + timedelta(hours=entry_token_expire_hours)).isoformat()
        # fnos_token 过期时间（默认8小时）
        fnos_token_expire_hours = get_preference("fnos_token_expire_hours", 8)
        fnos_token_expires_at = (now + timedelta(hours=fnos_token_expire_hours)).isoformat()
        # long_token 过期时间（默认25天）
        long_token_expire_days = get_preference("long_token_expire_days", 25)
        long_token_expires_at = (now + timedelta(days=long_token_expire_days)).isoformat() if long_token else None
        
        # 保存配置
        save_server_config(
            server,
            username=username,
            # Token
            fnos_token=fnos_token,
            fnos_token_expires_at=fnos_token_expires_at,
            long_token=long_token,
            long_token_expires_at=long_token_expires_at,
            entry_token=entry_token,
            entry_token_expires_at=entry_token_expires_at,
            sign_key=client.sign_key,
            # 用户信息
            uid=client.uid,
            admin=client.admin,
            back_id=client.back_id,
            # 兼容旧字段
            expires_at=entry_token_expires_at
        )
        
        # 配置 git
        print("正在配置 git...")
        git_configured = set_git_extra_header(server, entry_token)
        if not git_configured:
            print("警告: git extraHeader 配置失败，可能需要手动配置")
        
        # 注意：凭据保存由 CLI 在登录成功后处理，这里不再保存
        # save_creds 参数保留用于兼容，但不再使用
        
        # 设置全局 git hooks（实现自动刷新）
        hooks_configured = setup_global_hooks()
        if not hooks_configured:
            print("警告: 自动刷新 hooks 设置失败，token 过期后需手动执行 refresh")
        
        # 登录成功提示
        print(f"登录成功! 用户: {username}, UID: {client.uid}")
        if entry_token_warning:
            print("提示: entry-token 获取失败，如遇 git 403 错误请重新登录")
        
    finally:
        if client is not None:
            await client.close()


def do_logout() -> bool:
    """
    执行登出
    
    清除 token、移除 git 配置和全局 hooks。
    保留服务器地址和凭据方便下次快速登录。
    
    :return: True 表示成功登出，False 表示未登录
    """
    config = get_server_config()
    
    # 检查是否有有效的登录
    if not config or not config.get("fnos_token"):
        print("当前未登录")
        return False
    
    server = config.get("url")
    
    # 移除 git 配置
    if server:
        remove_git_extra_header(server)
    
    # 移除全局 hooks
    remove_global_hooks()
    
    # 删除 token（保留服务器地址）
    delete_server_config()
    
    print(f"已登出 {server}")
    return True


def show_status() -> None:
    """
    显示认证状态
    
    显示当前服务器、用户名、登录状态、过期时间、git 配置状态等信息。
    """
    config = get_server_config()
    
    # 检查是否有有效的登录（需要有 token，而不仅仅是 url）
    if not config or not config.get("fnos_token"):
        print("当前未登录")
        # 如果有保存的服务器地址，显示提示
        if config and config.get("url"):
            print(f"上次服务器: {config.get('url')}")
        return
    
    server = config.get("url")
    expired = is_token_expired()
    needs_refresh = token_needs_refresh()
    
    print(f"服务器: {server}")
    print(f"用户名: {config.get('username', '未知')}")
    print(f"状态: {'已过期' if expired else '已登录'}")
    
    if needs_refresh and not expired:
        print("提示: Token 即将过期，建议刷新")
    if config.get("expires_at"):
        print(f"过期时间: {config['expires_at']}")
    if config.get("last_login"):
        print(f"最后登录: {config['last_login']}")
    
    # 显示 git config 状态
    git_configured = has_git_extra_header(server) if server else False
    print(f"Git 配置: {'已配置' if git_configured else '未配置'}")
    
    # 显示 hooks 状态
    hooks_enabled = has_global_hooks()
    print(f"自动刷新: {'已启用' if hooks_enabled else '未启用'}")


async def do_refresh() -> None:
    """
    刷新 entry-token
    
    刷新策略（根据过期状态）：
    1. fnos_token 未过期 → 用 fnos_token 刷新 entry_token
    2. fnos_token 已过期，long_token 未过期 → 用 long_token 获取新的 fnos_token，再刷新 entry_token
    3. long_token 已过期，有保存凭据 → 重新登录
    4. 都失败 → 抛出异常
    
    :raises RuntimeError: 无法刷新时抛出
    """
    config = get_server_config()
    
    if not config or not config.get("url"):
        raise RuntimeError("当前未登录")
    
    server = config["url"]
    fnos_token = config.get("fnos_token")
    long_token = config.get("long_token")
    sign_key = config.get("sign_key")
    
    # 检查是否有有效的 token 可刷新
    if not fnos_token and not long_token:
        raise RuntimeError("当前未登录")
    
    # 检查各token的过期状态
    fnos_expired = is_fnos_token_expired()
    long_expired = is_long_token_expired()
    
    # 策略1: fnos_token 未过期，直接用它刷新 entry_token
    if fnos_token and sign_key and not fnos_expired:
        try:
            await _refresh_with_fnos_token(server, fnos_token, sign_key)
            return
        except Exception as e:
            print(f"fnos_token 验证失败: {e}")
            # 可能实际已过期，尝试下一种方式
    
    # 策略2: 用 long_token 获取新的 fnos_token
    if long_token and not long_expired:
        try:
            await _refresh_with_long_token(server, long_token)
            return
        except Exception as e:
            print(f"long_token 刷新失败: {e}")
    
    # 策略3: 检查是否有保存的凭据可用于重新登录
    creds = get_credentials()
    if creds and creds.get("username") and creds.get("password"):
        print("Token 已失效，使用保存的凭据重新登录...")
        await do_login(server, creds["username"], creds["password"], save_creds=False)
        return
    
    # 所有方式都失败
    raise RuntimeError("Token 已失效且未保存凭据，请重新登录")


async def _refresh_with_fnos_token(server: str, fnos_token: str, sign_key: str) -> None:
    """
    使用 fnos_token 刷新 entry-token
    
    流程：
    1. 连接 WebSocket
    2. 获取 RSA 公钥和 si
    3. 使用 authToken 验证 fnos_token
    4. 调用 exchangeEntryToken 获取新的 entry-token
    
    :param server: 服务器地址
    :param fnos_token: fnos-token
    :param sign_key: 签名密钥
    :raises RuntimeError: 刷新失败时抛出
    """
    client: Optional[FnOsClient] = None
    
    try:
        client = FnOsClient()
        print("正在刷新 token...")
        await client.connect(server)
        
        # 设置 token 和 sign_key 用于 authToken 验证
        client.token = fnos_token
        client.sign_key = sign_key
        
        # 验证 token（会自动获取 RSA 公钥和 si）
        await client.auth_token(main=True)
        
        # 获取 entry-token
        entry_token = await _get_entry_token(client)
        
        # 更新配置（只更新 entry_token 和过期时间）
        config = get_server_config() or {}
        now = datetime.now()
        entry_token_expire_hours = get_preference("entry_token_expire_hours", 8)
        entry_token_expires_at = (now + timedelta(hours=entry_token_expire_hours)).isoformat()
        
        save_server_config(
            server,
            update_last_login=False,
            username=config.get("username"),
            # Token（fnos_token 和 long_token 保持不变）
            fnos_token=fnos_token,
            fnos_token_expires_at=config.get("fnos_token_expires_at"),
            long_token=config.get("long_token"),
            long_token_expires_at=config.get("long_token_expires_at"),
            entry_token=entry_token,
            entry_token_expires_at=entry_token_expires_at,
            sign_key=sign_key,
            # 用户信息
            uid=config.get("uid"),
            admin=config.get("admin"),
            back_id=config.get("back_id"),
            # 兼容旧字段
            expires_at=entry_token_expires_at
        )
        
        # 更新 git 配置
        set_git_extra_header(server, entry_token)
        
        print("Token 已刷新")
        
    finally:
        if client is not None:
            await client.close()


async def _refresh_with_long_token(server: str, long_token: str) -> None:
    """
    使用 long_token 刷新（fnos_token 过期时使用）
    
    流程：
    1. 连接 WebSocket
    2. 使用 tokenLogin 获取新的 fnos_token 和 sign_key
    3. 调用 exchangeEntryToken 获取新的 entry-token
    
    :param server: 服务器地址
    :param long_token: fnos-long-token
    :raises RuntimeError: 刷新失败时抛出
    """
    client: Optional[FnOsClient] = None
    
    try:
        client = FnOsClient()
        print("正在使用 long_token 刷新...")
        await client.connect(server)
        
        # 获取 RSA 公钥（tokenLogin 需要加密）
        await client.get_rsa_pub()
        
        # 使用 long_token 登录获取新的 fnos_token
        response = await client.token_login(long_token)
        
        new_fnos_token = response.get("token") or client.token
        new_sign_key = client.sign_key
        
        if not new_fnos_token:
            raise RuntimeError("刷新失败: 未获取到新的 fnos_token")
        
        # 获取 entry-token
        entry_token = await _get_entry_token(client)
        
        # 更新配置（更新 fnos_token、sign_key、entry_token）
        config = get_server_config() or {}
        now = datetime.now()
        # fnos_token 是新获取的，重新计算过期时间
        fnos_token_expire_hours = get_preference("fnos_token_expire_hours", 8)
        fnos_token_expires_at = (now + timedelta(hours=fnos_token_expire_hours)).isoformat()
        # entry_token 是新获取的
        entry_token_expire_hours = get_preference("entry_token_expire_hours", 8)
        entry_token_expires_at = (now + timedelta(hours=entry_token_expire_hours)).isoformat()
        
        save_server_config(
            server,
            update_last_login=False,
            username=config.get("username"),
            # Token
            fnos_token=new_fnos_token,
            fnos_token_expires_at=fnos_token_expires_at,
            long_token=long_token,
            long_token_expires_at=config.get("long_token_expires_at"),  # 保持不变
            entry_token=entry_token,
            entry_token_expires_at=entry_token_expires_at,
            sign_key=new_sign_key,
            # 用户信息
            uid=client.uid or config.get("uid"),
            admin=client.admin or config.get("admin"),
            back_id=client.back_id or config.get("back_id"),
            # 兼容旧字段
            expires_at=entry_token_expires_at
        )
        
        # 更新 git 配置
        set_git_extra_header(server, entry_token)
        
        print("Token 已刷新")
        
    finally:
        if client is not None:
            await client.close()


async def _get_entry_token(client: FnOsClient) -> str:
    """
    获取 entry-token
    
    :param client: 已连接并验证的客户端
    :return: entry-token
    :raises RuntimeError: 获取失败时抛出
    """
    print("正在获取 entry-token...")
    entry_response = await client.exchange_entry_token()
    entry_data = entry_response.get("data", {})
    
    if isinstance(entry_data, dict) and entry_data.get("token"):
        entry_token = entry_data["token"]
        print("成功获取 entry-token")
        return entry_token
    
    raise RuntimeError("刷新失败: 未能获取 entry-token")
