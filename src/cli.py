"""
CLI 命令行接口模块（单服务器单用户模式）

提供 8 个命令: login, logout, status, refresh, update, config, git, diagnostic
"""
import click
import asyncio
import subprocess
from typing import Optional, Tuple
from . import __version__


# 启用 -h 作为 --help 的别名
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def _run_git_command(args: list[str]) -> Tuple[bool, str]:
    """
    运行 git 命令
    
    :param args: git 命令参数
    :return: (是否成功, 输出内容)
    """
    try:
        result = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def _normalize_server(server: Optional[str]) -> Optional[str]:
    """
    标准化服务器地址（去除协议前缀和路径）
    
    :param server: 原始服务器地址
    :return: 标准化后的服务器地址
    """
    if not server:
        return None
    
    server = server.strip()
    if not server:
        return None
    
    # 去除协议前缀
    for prefix in ["https://", "http://", "wss://", "ws://"]:
        if server.lower().startswith(prefix):
            server = server[len(prefix):]
            break
    
    # 去除路径，只保留主机名
    server = server.split("/")[0]
    return server if server else None


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="fnos-git-auth", message="%(prog)s %(version)s")
def main():
    """飞牛 fnOS Git 认证工具
    
    自动配置 git extraHeader 实现免密访问 NAS Git 仓库。
    """
    pass


def _get_login_credentials(
    server: Optional[str],
    username: Optional[str], 
    password: Optional[str]
) -> Tuple[str, str, str, bool]:
    """
    获取登录凭据（交互式补全缺失的参数）
    
    :return: (server, username, password, need_password_prompt)
    """
    from .config import get_server
    from .credentials import get_credentials
    
    # 获取已保存的配置
    saved_server = get_server()
    saved_creds = get_credentials()
    saved_username = saved_creds.get("username") if saved_creds else None
    saved_password = saved_creds.get("password") if saved_creds else None
    
    # 服务器地址：参数 > 配置 > 询问
    if server is None:
        server = saved_server or click.prompt("服务器地址")
    server = _normalize_server(server)
    while not server:
        server = _normalize_server(click.prompt("服务器地址"))
    
    # 用户名：参数 > 保存凭据 > 询问
    if username is None:
        if saved_username and saved_password:
            username = saved_username
        else:
            username = click.prompt("用户名")
    
    # 密码：参数 > 保存凭据（仅当用户名匹配时）> 询问
    need_password_prompt = False
    if password is None:
        if saved_password and username == saved_username:
            password = saved_password
        else:
            password = click.prompt("密码", hide_input=True)
            need_password_prompt = True
    
    return server, username, password, need_password_prompt


@main.command()
@click.option("-s", "--server", default=None, help="fnOS 服务器地址 (如: xxx.fnos.net)")
@click.option("-u", "--username", default=None, help="用户名")
@click.option("-p", "--password", default=None, help="密码")
@click.option("-n", "--no-save", is_flag=True, default=False, help="不保存凭据")
def login(server: Optional[str], username: Optional[str], password: Optional[str], no_save: bool):
    """登录到 fnOS 服务器
    
    支持交互式输入，首次使用无需参数。
    """
    from .utils import require_git
    from .auth import do_login
    from .credentials import save_credentials
    
    require_git()
    
    # 获取登录凭据
    server, username, password, need_password_prompt = _get_login_credentials(server, username, password)
    
    # 登录时不保存凭据，登录成功后再询问
    try:
        asyncio.run(do_login(server, username, password, save_creds=False))
    except Exception as e:
        click.echo(f"登录失败: {e}", err=True)
        raise SystemExit(1)
    
    # 登录成功后，询问是否保存凭据
    if no_save:
        return
    
    if need_password_prompt:
        # 新输入的密码，询问是否保存
        if click.confirm("是否保存账号密码?", default=True):
            save_credentials(username, password)
            click.echo("已保存凭据")
    else:
        # 使用已保存的凭据，保持不变（不需要重新保存）
        pass


@main.command()
@click.option("-a", "--all", "clear_all", is_flag=True, help="同时删除保存的凭据")
def logout(clear_all: bool):
    """登出并清除 token
    
    默认保留凭据方便下次快速登录，使用 -a 可同时删除凭据。
    """
    from .utils import require_git
    from .auth import do_logout
    from .credentials import delete_credentials
    
    require_git()
    success = do_logout()
    
    if clear_all:
        delete_credentials()
        click.echo("已删除保存的凭据")
    
    if not success and not clear_all:
        raise SystemExit(1)


@main.command()
def status():
    """查看认证状态"""
    from .auth import show_status
    show_status()


@main.command()
def refresh():
    """刷新 token"""
    from .utils import require_git
    from .auth import do_refresh
    
    require_git()
    try:
        asyncio.run(do_refresh())
    except Exception as e:
        click.echo(f"刷新失败: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("-c", "--check", "check_only", is_flag=True, help="仅检查，不下载")
@click.option("-f", "--force", is_flag=True, help="强制更新")
def update(check_only: bool, force: bool):
    """检查并更新工具"""
    from .update import check_for_updates, perform_update, get_current_version
    
    click.echo(f"当前版本: {get_current_version()}")
    
    update_info = check_for_updates()
    
    if update_info['latest_version']:
        click.echo(f"最新版本: {update_info['latest_version']}")
    else:
        click.echo("无法获取最新版本信息")
        return
    
    if update_info['has_update']:
        click.echo("✓ 发现新版本!")
        if update_info['release_notes']:
            click.echo(f"\n更新说明:\n{update_info['release_notes'][:300]}...\n")
        
        if not check_only:
            perform_update(force=False)
    else:
        click.echo("✓ 当前已是最新版本")
        if force:
            click.echo("强制重新下载...")
            perform_update(force=True)


@main.command()
@click.option("-k", "--key", default=None, help="配置项名称")
@click.option("-v", "--value", default=None, help="配置值")
@click.option("-r", "--reset", is_flag=True, help="重置所有配置")
def config(key: Optional[str], value: Optional[str], reset: bool):
    """查看或设置配置
    
    \b
    示例：
      config              # 显示所有配置
      config -k timeout   # 显示单个配置
      config -k timeout -v 60  # 设置配置
      config -r           # 重置所有配置
    """
    from .config import get_preferences, get_preference, set_preference, reset_preferences, DEFAULT_PREFERENCES
    
    if reset:
        reset_preferences()
        click.echo("已重置所有配置为默认值")
        return
    
    if key is None:
        prefs = get_preferences()
        click.echo("当前配置:")
        for k, v in prefs.items():
            default = DEFAULT_PREFERENCES.get(k)
            is_default = " (默认)" if v == default else ""
            click.echo(f"  {k}: {v}{is_default}")
    elif value is None:
        v = get_preference(key)
        if v is not None:
            click.echo(f"{key}: {v}")
        else:
            click.echo(f"未知配置项: {key}")
    else:
        default = DEFAULT_PREFERENCES.get(key)
        if default is None:
            # 未知配置项，显示有效的配置项列表
            click.echo(f"错误: 未知配置项 '{key}'", err=True)
            click.echo("有效的配置项:")
            for k in DEFAULT_PREFERENCES.keys():
                click.echo(f"  {k}")
            raise SystemExit(1)
        
        # 类型转换
        if isinstance(default, bool):
            value = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(default, int):
            value = int(value)
        elif isinstance(default, float):
            value = float(value)
        
        set_preference(key, value)
        click.echo(f"已设置 {key} = {value}")


def _show_git_extra_headers() -> None:
    """显示 git extraHeader 配置"""
    ok, out = _run_git_command(["config", "--global", "--list"])
    if ok:
        lines = [l for l in out.split("\n") if "extraheader" in l.lower()]
        if lines:
            click.echo("Git extraHeader 配置:")
            for line in lines:
                click.echo(f"  {line}")
        else:
            click.echo("未配置 extraHeader")
    else:
        click.echo(f"获取配置失败: {out}")


def _clear_all_git_extra_headers() -> None:
    """清除所有 git extraHeader 配置"""
    ok, out = _run_git_command(["config", "--global", "--list"])
    if ok:
        lines = [l for l in out.split("\n") if "extraheader" in l.lower()]
        for line in lines:
            key = line.split("=")[0]
            _run_git_command(["config", "--global", "--unset", key])
            click.echo(f"已清除: {key}")
        if not lines:
            click.echo("没有需要清除的配置")


@main.command()
@click.option("-s", "--show", is_flag=True, help="显示 extraHeader 配置")
@click.option("-c", "--clear", is_flag=True, help="清除所有配置")
@click.option("-r", "--remove", default=None, help="清除指定服务器配置")
@click.option("-t", "--timeout", type=int, default=None, help="设置凭证缓存时间（秒）")
def git(show: bool, clear: bool, remove: Optional[str], timeout: Optional[int]):
    """管理 git 配置
    
    \b
    示例：
      git             # 显示配置
      git -s          # 显示配置
      git -c          # 清除所有配置
      git -r xxx.fnos.net  # 清除指定服务器
      git -t 3600     # 设置凭证缓存1小时
    """
    from .utils import require_git
    
    require_git()
    
    # 默认显示配置
    if show or (not clear and not remove and timeout is None):
        _show_git_extra_headers()
        return
    
    if clear:
        _clear_all_git_extra_headers()
        return
    
    if remove:
        from .git_config import remove_git_extra_header
        remove_git_extra_header(remove)
        click.echo(f"已清除服务器 {remove} 的配置")
        return
    
    if timeout is not None:
        if timeout == 0:
            ok, _ = _run_git_command(["config", "--global", "--unset", "credential.helper"])
            if ok:
                click.echo("已禁用 git 凭证缓存")
            else:
                click.echo("警告: 禁用凭证缓存可能失败（配置项可能不存在）")
        else:
            ok, _ = _run_git_command(["config", "--global", "credential.helper", f"cache --timeout={timeout}"])
            if ok:
                click.echo(f"已设置凭证缓存: {timeout} 秒")
            else:
                click.echo("错误: 设置凭证缓存失败", err=True)
                raise SystemExit(1)


@main.command()
@click.option("-o", "--output", type=click.Path(), help="输出目录")
@click.option("-p", "--print", "print_only", is_flag=True, help="仅打印到控制台")
def diagnostic(output: str, print_only: bool):
    """生成诊断信息包
    
    收集环境信息打包成 tar.gz，用于提交 Issue。
    敏感信息自动脱敏。
    """
    from .diagnostic import create_diagnostic_package, print_diagnostic_info
    
    if print_only:
        print_diagnostic_info()
        return
    
    try:
        tar_path = create_diagnostic_package(output)
        click.echo(f"诊断包已生成: {tar_path}")
        click.echo("敏感信息已脱敏，可安全上传。")
    except Exception as e:
        click.echo(f"生成失败: {e}")


if __name__ == "__main__":
    main()
