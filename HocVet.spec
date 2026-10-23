# -*- mode: python ; coding: utf-8 -*-
from app_info import APP_NAME, APP_VERSION
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
    VarFileInfo, VarStruct,
)

version_tuple = tuple(int(part) for part in APP_VERSION.split('.')) + (0,)
product_version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'Nhật Nam (@UIBreaker)'),
        StringStruct('FileDescription', APP_NAME),
        StringStruct('ProductName', APP_NAME),
        StringStruct('FileVersion', APP_VERSION),
        StringStruct('ProductVersion', APP_VERSION),
        StringStruct('OriginalFilename', 'HocVet.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app_icon.png', '.'), ('app_icon.ico', '.')],
    hiddenimports=[],
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
    name=APP_NAME,
    version=product_version,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
