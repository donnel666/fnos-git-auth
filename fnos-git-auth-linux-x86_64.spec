# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/donnel/fn_git/main.py'],
    pathex=[],
    binaries=[],
    datas=[('/home/donnel/fn_git/src', 'src')],
    hiddenimports=['websockets', 'click', 'Crypto', 'Crypto.Cipher', 'Crypto.PublicKey', 'Crypto.Hash'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='fnos-git-auth-linux-x86_64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
