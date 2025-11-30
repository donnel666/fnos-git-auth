#!/usr/bin/env python3
"""
打包脚本
使用 PyInstaller 构建跨平台可执行文件
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"

# 应用信息
APP_NAME = "fnos-git-auth"
ENTRY_POINT = ROOT_DIR / "main.py"


def get_platform_suffix():
    """获取平台后缀"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        return f"windows-{machine}"
    elif system == "darwin":
        # macOS
        if machine == "arm64":
            return "macos-arm64"
        return "macos-x64"
    elif system == "linux":
        return f"linux-{machine}"
    return f"{system}-{machine}"


def clean():
    """清理构建目录"""
    print("清理构建目录...")
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
    
    # 清理 .spec 文件
    for spec in ROOT_DIR.glob("*.spec"):
        spec.unlink()


def build():
    """执行构建"""
    print(f"构建 {APP_NAME}...")
    
    suffix = get_platform_suffix()
    output_name = f"{APP_NAME}-{suffix}"
    
    # PyInstaller 参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # 打包成单文件
        "--clean",             # 清理临时文件
        "--noconfirm",         # 不确认覆盖
        f"--name={output_name}",
        "--add-data", f"{SRC_DIR}:src",  # 包含源码
        "--hidden-import=websockets",
        "--hidden-import=click",
        "--hidden-import=Crypto",
        "--hidden-import=Crypto.Cipher",
        "--hidden-import=Crypto.PublicKey",
        "--hidden-import=Crypto.Hash",
        str(ENTRY_POINT)
    ]
    
    # Windows 特殊处理
    if platform.system() == "Windows":
        args[args.index(f"{SRC_DIR}:src")] = f"{SRC_DIR};src"
    
    print(f"运行: {' '.join(args)}")
    result = subprocess.run(args, cwd=ROOT_DIR)
    
    if result.returncode != 0:
        print("构建失败!")
        sys.exit(1)
    
    # 显示输出文件
    output_dir = DIST_DIR
    if output_dir.exists():
        for f in output_dir.iterdir():
            print(f"输出文件: {f} ({f.stat().st_size / 1024 / 1024:.1f} MB)")
    
    print("构建完成!")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="构建 fnos-git-auth")
    parser.add_argument("--clean", action="store_true", help="只清理不构建")
    args = parser.parse_args()
    
    os.chdir(ROOT_DIR)
    
    if args.clean:
        clean()
    else:
        clean()
        build()


if __name__ == "__main__":
    main()
