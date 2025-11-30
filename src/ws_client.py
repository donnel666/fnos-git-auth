"""
WebSocket 客户端模块
负责与 fnOS 服务器通信（参考 fnnas-api 项目，优化实现）
"""
import asyncio
import json
import time
import logging
from typing import Optional, Callable, Any
import websockets
from websockets.client import WebSocketClientProtocol

from .crypto import (
    generate_random_string,
    generate_iv,
    encrypt_login_request,
    sign_request,
    aes_decrypt,
)


# 请求 ID 生成器
class ReqIdGenerator:
    """请求 ID 生成器"""
    
    def __init__(self):
        self._index = 0
    
    def generate(self, back_id: str = "0000000000000000") -> str:
        """生成请求 ID: {timestamp_hex}{back_id}{index_hex}"""
        self._index += 1
        timestamp = format(int(time.time()), "x").zfill(8)
        index = format(self._index, "x").zfill(4)
        return f"{timestamp}{back_id}{index}"


_reqid_generator = ReqIdGenerator()


class FnOsClient:
    """fnOS WebSocket 客户端"""
    
    def __init__(self, timeout: float = None, logger: Optional[logging.Logger] = None):
        # 延迟导入避免循环依赖
        from .config import get_preference
        
        self.timeout = timeout if timeout is not None else get_preference("timeout", 30.0)
        self.logger = logger or logging.getLogger(__name__)
        
        # WebSocket 连接
        self._ws: Optional[WebSocketClientProtocol] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._url: Optional[str] = None
        
        # 请求管理
        self._pending: dict[str, asyncio.Future] = {}
        
        # 加密相关（每次连接重新生成）
        self._aes_key: str = ""
        self._iv: bytes = b""
        
        # 服务器信息
        self.si: Optional[str] = None
        self.pub: Optional[str] = None
        
        # 登录信息
        self.back_id: str = "0000000000000000"
        self.token: Optional[str] = None
        self.secret: Optional[str] = None
        self.sign_key: Optional[str] = None
        self.uid: Optional[int] = None
        self.admin: Optional[bool] = None
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        if self._ws is None:
            return False
        # websockets 15+ 使用 state 属性
        try:
            from websockets.protocol import State
            return self._ws.state == State.OPEN
        except (ImportError, AttributeError):
            # 旧版本使用 open 属性
            return getattr(self._ws, 'open', True)

    
    async def connect(self, server: str, use_ssl: bool = None) -> None:
        """
        连接到 fnOS 服务器
        
        :param server: 服务器地址（如 your-server.fnos.net 或 192.168.1.4:5666）
        :param use_ssl: 是否使用 SSL（fn connect 为 True，本地为 False，None 使用配置）
        """
        from .config import get_preference
        
        # 使用配置的 SSL 设置
        if use_ssl is None:
            use_ssl = get_preference("use_ssl", True)
        
        # 判断协议
        protocol = "wss" if use_ssl else "ws"
        self._url = f"{protocol}://{server}/websocket?type=main"
        
        # 重新生成加密密钥
        self._aes_key = generate_random_string(32)
        self._iv = generate_iv()
        
        # fn connect 需要的额外头信息（从配置读取）
        extra_headers = {}
        if use_ssl:
            fn_connect_cookie = get_preference("fn_connect_cookie", "mode=relay; language=zh")
            extra_headers["Cookie"] = fn_connect_cookie
        
        try:
            # 注意：fnOS 服务器不响应 ping，关闭自动 ping
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self._url,
                    ping_interval=None,
                    additional_headers=extra_headers
                ),
                timeout=self.timeout
            )
            # 启动消息监听
            self._listen_task = asyncio.create_task(self._listen())
            self.logger.debug(f"已连接到 {server}")
        except Exception as e:
            raise ConnectionError(f"连接失败: {e}")
    
    async def close(self) -> None:
        """关闭连接"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self.logger.debug("连接已关闭")

    
    async def _listen(self) -> None:
        """监听 WebSocket 消息"""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    self.logger.debug(f"收到: {message[:200]}...")
                    
                    reqid = data.get("reqid")
                    if reqid and reqid in self._pending:
                        future = self._pending.pop(reqid)
                        if not future.done():
                            future.set_result(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"无效的 JSON: {message}")
        except websockets.ConnectionClosed:
            self.logger.debug("WebSocket 连接已关闭")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception(f"监听异常: {e}")
    
    async def request(self, req: str, **kwargs) -> dict:
        """
        发送请求并等待响应
        
        :param req: 请求类型
        :param kwargs: 请求参数
        :return: 响应数据
        """
        if not self.is_connected:
            raise RuntimeError("未连接到服务器")
        
        # 生成请求 ID
        reqid = _reqid_generator.generate(self.back_id)
        data = {"req": req, "reqid": reqid, **kwargs}

        
        # 需要加密的请求
        if req in ["user.login", "user.add"]:
            json_data = json.dumps(data, separators=(",", ":"))
            data = encrypt_login_request(json_data, self.pub, self._aes_key, self._iv)
        
        # 签名请求
        message = sign_request(data, self.sign_key)
        
        # 发送请求
        await self._ws.send(message)
        self.logger.debug(f"发送: {req}")
        
        # 等待响应
        future: asyncio.Future = asyncio.Future()
        self._pending[reqid] = future
        
        try:
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(reqid, None)
            raise TimeoutError(f"请求超时: {req}")
    
    # ========== 公共 API ==========
    
    async def get_rsa_pub(self) -> dict:
        """获取 RSA 公钥"""
        response = await self.request("util.crypto.getRSAPub")
        if "errno" in response:
            raise RuntimeError(f"获取公钥失败: {response}")
        self.pub = response.get("pub")
        self.si = response.get("si")
        return response

    
    async def login(
        self,
        username: str,
        password: str,
        stay: bool = True,
        device_type: str = None,
        device_name: str = None
    ) -> dict:
        """
        登录到 fnOS
        
        :param username: 用户名
        :param password: 密码
        :param stay: 是否保持登录（获取 long-token）
        :param device_type: 设备类型（None 使用配置）
        :param device_name: 设备名称（None 使用配置）
        :return: 登录响应
        """
        from .config import get_preference
        
        # 使用配置的默认值
        if device_type is None:
            device_type = get_preference("device_type", "Browser")
        if device_name is None:
            device_name = get_preference("device_name", "fnos-git-auth")
        
        # 确保已获取公钥
        if not self.pub:
            await self.get_rsa_pub()
        
        response = await self.request(
            "user.login",
            user=username,
            password=password,
            stay=stay,
            deviceType=device_type,
            deviceName=device_name,
            si=self.si
        )
        
        # 检查错误
        if "errno" in response:
            error_msg = response.get("msg") or response.get("error") or f"错误码: {response['errno']}"
            raise RuntimeError(f"登录失败: {error_msg}")
        
        # 保存登录信息
        self.back_id = response.get("backId", self.back_id)
        self.token = response.get("token")
        self.secret = response.get("secret")
        self.uid = response.get("uid")
        self.admin = response.get("admin")
        
        # 解密签名密钥
        if self.secret:
            self.sign_key = aes_decrypt(self.secret, self._aes_key, self._iv)
        
        return response

    
    async def get_si(self) -> dict:
        """获取 SI（用于 authToken）"""
        response = await self.request("util.getSI")
        self.si = response.get("si")
        return response
    
    async def auth_token(self, main: bool = True) -> dict:
        """
        验证 token（用于刷新 entry-token）
        
        :param main: 是否为主连接（默认 True）
        :return: 响应（包含 uid, admin, backId）
        """
        # 使用 getRSAPub 获取 si（与浏览器行为一致）
        if not self.si:
            await self.get_rsa_pub()
        
        response = await self.request(
            "user.authToken",
            token=self.token,
            main=main,
            si=self.si
        )
        
        if "errno" in response:
            raise RuntimeError(f"token 验证失败: {response}")
        
        # 保存返回的信息
        self.uid = response.get("uid")
        self.admin = response.get("admin")
        self.back_id = response.get("backId", self.back_id)
        
        return response
    
    async def exchange_entry_token(self) -> dict:
        """
        获取 entry-token（32字符十六进制格式）
        用于 HTTP 请求认证（包括 Git）
        """
        response = await self.request("appcgi.sac.entry.v1.exchangeEntryToken")
        
        if "errno" in response:
            raise RuntimeError(f"获取 entry-token 失败: {response}")
        
        return response
    
    async def token_login(self, long_token: str) -> dict:
        """
        使用 long-token 登录获取新的 fnos-token
        
        当 fnos-token 过期时，使用此方法刷新
        
        :param long_token: fnos-long-token
        :return: 响应（包含新 token 和 secret）
        """
        from .config import get_preference
        
        device_type = get_preference("device_type", "Browser")
        device_name = get_preference("device_name", "fnos-git-auth")
        
        response = await self.request(
            "user.tokenLogin",
            token=long_token,
            deviceType=device_type,
            deviceName=device_name
        )
        
        if "errno" in response:
            raise RuntimeError(f"token登录失败: {response.get('msg', '未知错误')}")
        
        # 保存新的登录信息
        new_token = response.get("token")
        if new_token:
            self.token = new_token
        
        # 解密新的签名密钥
        secret = response.get("secret")
        if secret:
            self.secret = secret
            self.sign_key = aes_decrypt(secret, self._aes_key, self._iv)
        
        # 保存 backId
        self.back_id = response.get("backId", self.back_id)
        self.uid = response.get("uid")
        self.admin = response.get("admin")
        
        return response
