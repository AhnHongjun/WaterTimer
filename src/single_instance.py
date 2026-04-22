"""Windows named mutex로 동시에 한 인스턴스만 실행되도록 보장.

한계: 기존 인스턴스에 "설정 창 열기"를 시그널링하는 것은 v1 스코프 밖.
두 번째 실행은 그냥 종료되고, 사용자가 트레이 아이콘을 클릭해야 함.
"""
from __future__ import annotations

import ctypes
import sys

MUTEX_NAME = "Global\\WaterTimer_SingleInstance_Mutex_v1"
ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """실행 중인 동안 named mutex를 잡고 있는 컨텍스트."""

    def __init__(self):
        self._handle = None

    def __enter__(self):
        if sys.platform != "win32":
            return self
        self._handle = ctypes.windll.kernel32.CreateMutexW(
            None, False, MUTEX_NAME
        )
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            raise AlreadyRunning()
        return self

    def __exit__(self, *args):
        if self._handle:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None


class AlreadyRunning(RuntimeError):
    pass
