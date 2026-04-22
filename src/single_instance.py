"""Windows named mutex로 동시에 한 인스턴스만 실행되도록 보장.

한계: 기존 인스턴스에 "설정 창 열기"를 시그널링하는 것은 v1 스코프 밖.
두 번째 실행은 그냥 종료되고, 사용자가 트레이 아이콘을 클릭해야 함.
"""
from __future__ import annotations

import ctypes
import sys

MUTEX_NAME = "Global\\WaterTimer_SingleInstance_Mutex_v1"
ERROR_ALREADY_EXISTS = 183


def _configure_winapi():
    """kernel32 함수의 argtypes/restype 지정.

    Windows x64에서 HANDLE은 64bit인데 ctypes의 기본 restype은 c_int(32bit)라서
    명시 안 하면 반환된 HANDLE이 truncate되어 이후 CloseHandle이 잘못된 값에 동작함.
    """
    k = ctypes.windll.kernel32
    k.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    k.CreateMutexW.restype = ctypes.c_void_p
    k.GetLastError.argtypes = []
    k.GetLastError.restype = ctypes.c_ulong
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.CloseHandle.restype = ctypes.c_bool


if sys.platform == "win32":
    _configure_winapi()


class SingleInstanceGuard:
    """실행 중인 동안 named mutex를 잡고 있는 컨텍스트."""

    def __init__(self):
        self._handle = None

    def __enter__(self):
        if sys.platform != "win32":
            return self
        k = ctypes.windll.kernel32
        self._handle = k.CreateMutexW(None, False, MUTEX_NAME)
        # GetLastError는 CreateMutexW 직후 바로 읽어야 다른 호출이 덮어쓰지 않음.
        last_error = k.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            raise AlreadyRunning()
        return self

    def __exit__(self, *args):
        if self._handle:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None


class AlreadyRunning(RuntimeError):
    pass
