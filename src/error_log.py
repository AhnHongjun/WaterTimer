"""error.log 로깅 설정 + 글로벌 예외 훅.

사용자에게는 Qt 메시지박스로 간단히 알리고, 상세는 %APPDATA%\\WaterTimer\\error.log에 기록.
"""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

from src import paths

_logger: logging.Logger | None = None


def setup() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    log = logging.getLogger("water_timer")
    log.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        paths.error_log_path(), maxBytes=512_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    log.addHandler(handler)
    _logger = log
    return log


def install_excepthook():
    log = setup()

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.error("Unhandled exception:\n%s",
                  "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        # 사용자에게 알림
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(
                    None, "Water Timer 오류",
                    "예상치 못한 오류가 발생했습니다.\n자세한 내용은 error.log를 확인해 주세요."
                )
        except Exception:
            pass

    sys.excepthook = _hook
