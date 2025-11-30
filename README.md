# fnos-git-auth

fnOS Git 认证工具 - 自动配置 git extraHeader 实现通过 fn connect 服务免密访问 fnOS NAS 上的 Git 仓库。

## 功能特性

- 🔐 WebSocket 加密认证登录 fnOS
- 🔑 自动获取并配置 entry-token
- 🔄 **智能自动刷新** - 通过 Git Hooks 在 push 前自动刷新 token
- 💾 默认保存凭据实现完全无感使用
- 🌐 支持子域名通配符配置
- 🖥️ 跨平台支持 (Linux/Windows/macOS)

## 安装

### 方式一：一键安装（推荐）

**Linux / macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.sh | bash
```

**Windows (PowerShell):**

```powershell
iwr -useb https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.ps1 | iex
```

### 方式二：下载预编译二进制

从 [Releases](../../releases) 页面下载对应平台的二进制文件。

### 方式三：从源码运行

```bash
git clone https://github.com/donnel666/fnos-git-auth.git
cd fnos-git-auth
uv sync
uv run python main.py --help
```

## 快速开始

```bash
# 首次登录（交互式输入）
fnos-git-auth login

# 再次登录（已保存凭据，直接登录）
fnos-git-auth login

# 切换用户
fnos-git-auth login -u newuser

# 切换服务器
fnos-git-auth login -s other.fnos.net
```

登录成功后，直接使用 git（token 会在 push 前自动刷新）：

```bash
git clone https://your-server.fnos.net/repo.git
git push origin main  # 自动刷新 token，无需手动操作
```

> 只要不执行 `logout`，就可以一直无感使用 git，无需关心 token 过期问题。

## 命令参考

### login - 登录

```bash
fnos-git-auth login [OPTIONS]

选项：
  -s, --server TEXT    服务器地址
  -u, --username TEXT  用户名
  -p, --password TEXT  密码
  -n, --no-save        不保存凭据
  -h, --help           显示帮助
```

**智能登录逻辑：**
- 首次登录：交互式输入服务器、用户名、密码
- 已保存凭据：直接登录（无需输入）
- 切换用户（`-u`）：提示输入密码
- 切换服务器（`-s`）：提示输入用户名和密码

### logout - 登出

```bash
fnos-git-auth logout
```

登出会清除 token 和自动刷新 hooks，保留凭据方便下次快速登录。

### status - 查看状态

```bash
fnos-git-auth status
```

输出示例：
```
服务器: your-server.fnos.net
用户名: your_username
状态: 已登录
Git 配置: 已配置
自动刷新: 已启用
```

### refresh - 刷新 Token

```bash
fnos-git-auth refresh
```

### update - 检查更新

```bash
fnos-git-auth update [OPTIONS]

选项：
  -c, --check   仅检查，不下载
  -f, --force   强制更新
```

### config - 配置管理

```bash
fnos-git-auth config [OPTIONS]

选项：
  -k, --key TEXT    配置项名称
  -v, --value TEXT  配置值
  -r, --reset       重置所有配置

示例：
  config              # 显示所有配置
  config -k timeout   # 显示单个配置
  config -k timeout -v 60  # 设置配置
  config -r           # 重置所有配置
```

### git - Git 配置管理

```bash
fnos-git-auth git [OPTIONS]

选项：
  -s, --show             显示 extraHeader 配置
  -c, --clear            清除所有配置
  -r, --remove TEXT      清除指定服务器配置
  -t, --timeout INTEGER  设置凭证缓存时间（秒）

示例：
  git             # 显示配置
  git -c          # 清除所有配置
  git -r xxx.fnos.net  # 清除指定服务器
  git -t 3600     # 设置凭证缓存1小时
```

### diagnostic - 生成诊断包

```bash
fnos-git-auth diagnostic [OPTIONS]

选项：
  -o, --output PATH  输出目录
  -p, --print        仅打印到控制台
```

生成诊断信息包用于提交 Issue，敏感信息自动脱敏。

## 注意事项

### 不支持开启 2FA 的账号

本工具**不支持开启了两步验证（2FA）的账号**登录。如果您的 fnOS 账号开启了 2FA，建议：

1. **新建一个专用 Git 账号**：在 fnOS 中创建一个不开启 2FA 的账号，专门用于 Git 访问
2. **授予仓库权限**：为该账号授予需要访问的 Git 仓库权限
3. **使用专用账号登录**：使用该账号进行 `fnos-git-auth login`

> 本工具的作用仅是获取访问 Git 服务的认证 token，实际的仓库读写权限仍由 Git 账号权限控制。

## 问题反馈

遇到问题？

1. 生成诊断包：`fnos-git-auth diagnostic`
2. 前往 [GitHub Issues](https://github.com/donnel666/fnos-git-auth/issues/new) 提交问题

**常见问题：**

- **登录超时**：检查网络，尝试 `config -k timeout -v 60`
- **Git clone 403**：运行 `status` 检查 token，`refresh` 刷新
- **Git 未安装**：请先安装 [Git](https://git-scm.com/)

## 许可证

MIT License

## 相关链接

- [fnOS 官网](https://www.fnnas.com)
- [fnnas-api](https://github.com/FNOSP/fnnas-api) - 参考实现
