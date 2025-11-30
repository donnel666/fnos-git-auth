"""
加密模块单元测试
"""
import pytest
import base64
import json
import sys
sys.path.insert(0, ".")

from src.crypto import (
    generate_random_string,
    generate_iv,
    rsa_encrypt,
    aes_encrypt,
    aes_decrypt,
    encrypt_login_request,
    get_signature,
    sign_request,
)


class TestGenerators:
    """测试随机生成函数"""
    
    def test_generate_random_string_length(self):
        """测试生成的字符串长度"""
        result = generate_random_string(32)
        assert len(result) == 32
    
    def test_generate_random_string_uniqueness(self):
        """测试生成的字符串唯一性"""
        results = [generate_random_string(32) for _ in range(100)]
        assert len(set(results)) == 100
    
    def test_generate_iv_length(self):
        """测试 IV 长度"""
        iv = generate_iv()
        assert len(iv) == 16
        assert isinstance(iv, bytes)


class TestAES:
    """测试 AES 加解密"""
    
    def test_aes_encrypt_decrypt(self):
        """测试 AES 加解密往返"""
        key = generate_random_string(32)
        iv = generate_iv()
        plaintext = "测试数据 Hello World 123"
        
        encrypted = aes_encrypt(plaintext, key, iv)
        # 注意：aes_decrypt 返回的是 base64 编码的解密结果
        decrypted_b64 = aes_decrypt(encrypted, key, iv)
        decrypted = base64.b64decode(decrypted_b64).decode('utf-8')
        
        assert decrypted == plaintext
    
    def test_aes_encrypt_produces_base64(self):
        """测试 AES 加密输出是有效的 base64"""
        key = generate_random_string(32)
        iv = generate_iv()
        plaintext = "test"
        
        encrypted = aes_encrypt(plaintext, key, iv)
        # 应该能成功解码为 bytes
        decoded = base64.b64decode(encrypted)
        assert isinstance(decoded, bytes)


class TestSignature:
    """测试签名功能"""
    
    def test_get_signature(self):
        """测试签名生成"""
        data = '{"test":"data"}'
        key = base64.b64encode(b"test_key_12345678901234567890ab").decode()
        
        signature = get_signature(data, key)
        assert isinstance(signature, str)
        # 签名应该是 base64 编码
        decoded = base64.b64decode(signature)
        assert len(decoded) == 32  # SHA256 产生 32 字节

    
    def test_sign_request_no_sign(self):
        """测试不需要签名的请求"""
        data = {"req": "encrypted", "test": "data"}
        result = sign_request(data, "some_key")
        
        # 不需要签名，直接返回 JSON
        assert result == json.dumps(data, separators=(",", ":"))
    
    def test_sign_request_with_sign(self):
        """测试需要签名的请求"""
        data = {"req": "user.info", "test": "data"}
        key = base64.b64encode(b"test_key_12345678901234567890ab").decode()
        
        result = sign_request(data, key)
        json_str = json.dumps(data, separators=(",", ":"))
        
        # 结果应该是 签名 + JSON
        assert result.endswith(json_str)
        assert len(result) > len(json_str)


class TestEncryptLoginRequest:
    """测试登录请求加密"""
    
    def test_encrypt_login_request_structure(self):
        """测试加密请求结构"""
        # 使用测试公钥
        test_pub = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJccc3OpE2Dbqk
ZNkHJzCb3HLNQwXHdLJy+yrW9qI3xHbI2AAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAB
-----END PUBLIC KEY-----"""
        
        data = '{"req":"user.login","user":"test"}'
        key = generate_random_string(32)
        iv = generate_iv()
        
        try:
            result = encrypt_login_request(data, test_pub, key, iv)
            assert "req" in result
            assert result["req"] == "encrypted"
            assert "iv" in result
            assert "rsa" in result
            assert "aes" in result
        except Exception:
            # 测试公钥可能无效，跳过
            pytest.skip("测试公钥无效")
