"""
版本检测和更新模块
"""
import os
import sys
import json
import platform
import tempfile
import shutil
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from . import __version__

# GitHub 仓库配置
GITHUB_REPO = "donnel666/fnos-git-auth"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version() -> str:
    """获取当前版本"""
    return __version__


def parse_version(version_str: str) -> tuple:
    """解析版本号为元组用于比较"""
    # 移除 'v' 前缀
    version_str = version_str.lstrip('v')
    parts = version_str.split('.')
    result = []
    for part in parts:
        # 处理带有后缀的版本号，如 1.0.0-beta
        num_part = ''
        for char in part:
            if char.isdigit():
                num_part += char
            else:
                break
        result.append(int(num_part) if num_part else 0)
    return tuple(result)


def compare_versions(v1: str, v2: str) -> int:
    """
    比较两个版本号
    返回: -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)
    """
    t1 = parse_version(v1)
    t2 = parse_version(v2)
    
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


def get_latest_release() -> dict | None:
    """
    从 GitHub 获取最新发布版本信息
    返回: {version, download_url, published_at, body} 或 None
    """
    try:
        request = Request(
            GITHUB_API_URL,
            headers={
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': f'fnos-git-auth/{__version__}'
            }
        )
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # 获取当前平台对应的下载 URL
            download_url = None
            asset_name = get_asset_name()
            
            for asset in data.get('assets', []):
                if asset['name'] == asset_name:
                    download_url = asset['browser_download_url']
                    break
            
            return {
                'version': data.get('tag_name', ''),
                'download_url': download_url,
                'published_at': data.get('published_at', ''),
                'body': data.get('body', ''),
                'html_url': data.get('html_url', '')
            }
    except (URLError, HTTPError, json.JSONDecodeError, KeyError) as e:
        print(f"获取版本信息失败: {e}")
        return None


def get_asset_name() -> str:
    """获取当前平台对应的资产文件名"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'linux':
        if machine in ('x86_64', 'amd64'):
            return 'fnos-git-auth-linux-x86_64'
        elif machine in ('aarch64', 'arm64'):
            return 'fnos-git-auth-linux-arm64'
    elif system == 'darwin':
        if machine in ('x86_64', 'amd64'):
            return 'fnos-git-auth-macos-x64'
        elif machine in ('arm64', 'aarch64'):
            return 'fnos-git-auth-macos-arm64'
    elif system == 'windows':
        return 'fnos-git-auth-windows-x64.exe'
    
    return ''


def check_for_updates() -> dict:
    """
    检查是否有更新
    返回: {has_update, current_version, latest_version, download_url, release_notes}
    """
    current = get_current_version()
    result = {
        'has_update': False,
        'current_version': current,
        'latest_version': None,
        'download_url': None,
        'release_notes': None,
        'release_url': None
    }
    
    latest = get_latest_release()
    if latest:
        result['latest_version'] = latest['version']
        result['download_url'] = latest['download_url']
        result['release_notes'] = latest['body']
        result['release_url'] = latest['html_url']
        
        if compare_versions(current, latest['version']) < 0:
            result['has_update'] = True
    
    return result


def download_update(download_url: str, target_path: str = None) -> str | None:
    """
    下载更新文件
    返回: 下载的文件路径 或 None
    """
    if not download_url:
        print("错误: 没有可用的下载链接")
        return None
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='fnos-git-auth-update-')
        filename = os.path.basename(download_url)
        temp_file = os.path.join(temp_dir, filename)
        
        print(f"正在下载: {download_url}")
        
        request = Request(
            download_url,
            headers={'User-Agent': f'fnos-git-auth/{__version__}'}
        )
        
        with urlopen(request, timeout=60) as response:
            total_size = response.headers.get('Content-Length')
            if total_size:
                total_size = int(total_size)
            
            downloaded = 0
            block_size = 8192
            
            with open(temp_file, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    f.write(buffer)
                    downloaded += len(buffer)
                    
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"\r下载进度: {percent:.1f}%", end='', flush=True)
            
            print()  # 换行
        
        # 如果指定了目标路径，移动文件
        if target_path:
            # 备份旧文件
            if os.path.exists(target_path):
                backup_path = target_path + '.backup'
                shutil.copy2(target_path, backup_path)
                print(f"已备份旧版本到: {backup_path}")
            
            shutil.move(temp_file, target_path)
            
            # 添加执行权限（Linux/macOS）
            if platform.system().lower() != 'windows':
                os.chmod(target_path, 0o755)
            
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return target_path
        
        return temp_file
        
    except (URLError, HTTPError, IOError) as e:
        print(f"下载失败: {e}")
        return None


def get_executable_path() -> str | None:
    """获取当前可执行文件路径"""
    # 如果是 PyInstaller 打包的
    if getattr(sys, 'frozen', False):
        return sys.executable
    
    # 如果是脚本运行，返回 None（不支持自动更新）
    return None


def perform_update(force: bool = False) -> bool:
    """
    执行更新
    
    :param force: 强制下载（即使已是最新版本）
    :return: 是否成功
    """
    update_info = check_for_updates()
    
    if not update_info['has_update'] and not force:
        print(f"当前已是最新版本 ({update_info['current_version']})")
        return True
    
    print(f"发现新版本: {update_info['latest_version']}")
    print(f"当前版本: {update_info['current_version']}")
    
    if update_info['release_notes']:
        print(f"\n更新说明:\n{update_info['release_notes'][:500]}...")
    
    if not update_info['download_url']:
        print(f"\n当前平台无可用的预编译版本")
        print(f"请访问: {update_info['release_url']}")
        return False
    
    # 获取当前可执行文件路径
    exe_path = get_executable_path()
    
    if exe_path:
        # 自动更新
        downloaded = download_update(update_info['download_url'], exe_path)
        if downloaded:
            print(f"更新成功! 请重新运行程序。")
            return True
        return False
    else:
        # 手动更新提示
        print(f"\n当前运行方式不支持自动更新")
        print(f"请手动下载: {update_info['download_url']}")
        print(f"或访问: {update_info['release_url']}")
        return False


def check_git_updates(repo_path: str = '.') -> dict:
    """
    检查 Git 仓库是否有更新
    返回: {has_update, local_commit, remote_commit, behind_count}
    """
    import subprocess
    
    result = {
        'has_update': False,
        'local_commit': None,
        'remote_commit': None,
        'behind_count': 0,
        'error': None
    }
    
    try:
        # 获取本地 HEAD
        local_head = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if local_head.returncode != 0:
            result['error'] = '不是有效的 Git 仓库'
            return result
        
        result['local_commit'] = local_head.stdout.strip()[:8]
        
        # fetch 远程更新
        fetch = subprocess.run(
            ['git', 'fetch', '--quiet'],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        # 获取远程 HEAD
        remote_head = subprocess.run(
            ['git', 'rev-parse', '@{u}'],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if remote_head.returncode != 0:
            result['error'] = '无法获取远程分支信息'
            return result
        
        result['remote_commit'] = remote_head.stdout.strip()[:8]
        
        # 比较本地和远程
        behind = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD..@{u}'],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if behind.returncode == 0:
            count = int(behind.stdout.strip())
            result['behind_count'] = count
            result['has_update'] = count > 0
        
    except FileNotFoundError:
        result['error'] = 'Git 未安装或不在 PATH 中'
    except Exception as e:
        result['error'] = str(e)
    
    return result
