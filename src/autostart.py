"""Windows 시작 시 자동 실행.

HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 에
앱 실행 경로를 값으로 저장한다.
"""
from __future__ import annotations

import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "WaterTimer"


def _winreg():
    import winreg  # Windows 전용
    return winreg


def set_autostart(enabled: bool, exe_path: str) -> None:
    if sys.platform != "win32":
        return
    winreg = _winreg()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        if enabled:
            # 경로에 공백이 있는 경우 대비 quote
            value = f'"{exe_path}"'
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass  # 이미 없으면 OK


def get_autostart() -> bool:
    if sys.platform != "win32":
        return False
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def get_registered_path() -> str | None:
    if sys.platform != "win32":
        return None
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            # 저장은 quote 포함 → 반환 시 제거
            return value.strip('"')
    except FileNotFoundError:
        return None


def current_exe_path() -> str:
    """런타임에 자기 자신 경로 추출. PyInstaller 빌드 시 sys.executable 사용."""
    if getattr(sys, "frozen", False):
        return sys.executable
    import os
    # 개발 환경: python.exe -m src.app → sys.executable + 현재 스크립트
    return os.path.abspath(sys.argv[0]) or sys.executable
