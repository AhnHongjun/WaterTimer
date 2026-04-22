# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — 단일 .exe 생성.
# 빌드: pyinstaller build.spec  (또는 build.bat)

from pathlib import Path

ROOT = Path.cwd()

a = Analysis(
    [str(ROOT / "src" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "assets" / "bundled"), "assets/bundled"),
        (str(ROOT / "src" / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "src" / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WaterTimer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # --windowed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "src" / "assets" / "icon.ico"),
)
