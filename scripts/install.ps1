# fnos-git-auth Windows 一键安装脚本
# 用法: iwr -useb https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.ps1 | iex
# 或者: Invoke-WebRequest -Uri https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.ps1 -UseBasicParsing | Invoke-Expression

$ErrorActionPreference = "Stop"

# 配置
$Repo = "donnel666/fnos-git-auth"
$InstallDir = if ($env:FNOS_GIT_AUTH_DIR) { $env:FNOS_GIT_AUTH_DIR } else { "$env:USERPROFILE\.fnos-git-auth" }
$BinDir = if ($env:FNOS_GIT_AUTH_BIN) { $env:FNOS_GIT_AUTH_BIN } else { "$env:USERPROFILE\.local\bin" }

Write-Host "fnos-git-auth 安装脚本" -ForegroundColor Blue
Write-Host "==================================" -ForegroundColor Blue

# 检测架构
function Get-Architecture {
    $arch = [System.Environment]::GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")
    switch ($arch) {
        "AMD64" { return "x64" }
        "x86" { return "x86" }
        "ARM64" { return "arm64" }
        default { return "unknown" }
    }
}

# 获取最新版本
function Get-LatestVersion {
    try {
        $response = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Method Get
        return $response.tag_name
    }
    catch {
        Write-Host "警告: 无法获取最新版本，使用默认版本 v0.1.0" -ForegroundColor Yellow
        return "v0.1.0"
    }
}

# 下载文件
function Download-File {
    param (
        [string]$Url,
        [string]$Output
    )
    
    Write-Host "正在下载: $Url" -ForegroundColor Cyan
    
    try {
        # 使用 TLS 1.2
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($Url, $Output)
    }
    catch {
        # 备用方法
        Invoke-WebRequest -Uri $Url -OutFile $Output -UseBasicParsing
    }
}

# 添加到 PATH
function Add-ToPath {
    param (
        [string]$Dir
    )
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -notlike "*$Dir*") {
        $newPath = "$currentPath;$Dir"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "已添加 $Dir 到用户 PATH" -ForegroundColor Green
        Write-Host "请重新打开终端使配置生效" -ForegroundColor Yellow
    }
    else {
        Write-Host "$Dir 已在 PATH 中" -ForegroundColor Green
    }
}

# 主函数
function Main {
    param (
        [switch]$Uninstall
    )
    
    if ($Uninstall) {
        Write-Host "正在卸载 fnos-git-auth..." -ForegroundColor Yellow
        
        $targetFile = Join-Path $BinDir "fnos-git-auth.exe"
        if (Test-Path $targetFile) {
            Remove-Item $targetFile -Force
            Write-Host "已删除 $targetFile" -ForegroundColor Green
        }
        
        if (Test-Path $InstallDir) {
            $response = Read-Host "是否删除配置目录 $InstallDir? [y/N]"
            if ($response -eq "y" -or $response -eq "Y") {
                Remove-Item $InstallDir -Recurse -Force
                Write-Host "已删除 $InstallDir" -ForegroundColor Green
            }
        }
        
        Write-Host "卸载完成" -ForegroundColor Green
        return
    }
    
    # 检测架构
    $arch = Get-Architecture
    Write-Host "检测到架构: $arch" -ForegroundColor Green
    
    if ($arch -eq "arm64") {
        Write-Host "警告: Windows ARM64 版本暂不支持，请使用 x64 仿真模式" -ForegroundColor Yellow
        $arch = "x64"
    }
    
    if ($arch -ne "x64") {
        Write-Host "错误: 不支持的架构 $arch" -ForegroundColor Red
        exit 1
    }
    
    # 获取版本
    $version = Get-LatestVersion
    Write-Host "最新版本: $version" -ForegroundColor Green
    
    # 构建下载 URL
    $filename = "fnos-git-auth-windows-x64.exe"
    $downloadUrl = "https://github.com/$Repo/releases/download/$version/$filename"
    Write-Host "下载地址: $downloadUrl" -ForegroundColor Green
    
    # 创建目录
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    if (-not (Test-Path $BinDir)) {
        New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    }
    
    # 下载
    $targetFile = Join-Path $BinDir "fnos-git-auth.exe"
    Download-File -Url $downloadUrl -Output $targetFile
    
    Write-Host "已下载到: $targetFile" -ForegroundColor Green
    
    # 添加到 PATH
    Add-ToPath -Dir $BinDir
    
    # 验证安装
    Write-Host "验证安装..." -ForegroundColor Blue
    
    if (Test-Path $targetFile) {
        Write-Host "安装成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "使用方法:" -ForegroundColor Cyan
        Write-Host "  fnos-git-auth --help     # 查看帮助"
        Write-Host "  fnos-git-auth login      # 登录"
        Write-Host "  fnos-git-auth status     # 查看状态"
        Write-Host ""
        
        # 尝试运行
        try {
            $versionInfo = & $targetFile --version 2>&1
            Write-Host "版本信息: $versionInfo" -ForegroundColor Green
        }
        catch {
            # 忽略错误
        }
    }
    else {
        Write-Host "安装失败: 文件未找到" -ForegroundColor Red
        exit 1
    }
}

# 执行
Main @args
