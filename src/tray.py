"""시스템 트레이 아이콘 + 우클릭 메뉴."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


class Tray(QSystemTrayIcon):
    def __init__(self,
                 icon_path: Path,
                 on_test_notify: Callable[[], None],
                 on_toggle_pause: Callable[[], None],
                 on_open_settings: Callable[[], None],
                 on_quit: Callable[[], None],
                 parent=None):
        super().__init__(QIcon(str(icon_path)), parent)
        self._on_test_notify = on_test_notify
        self._on_toggle_pause = on_toggle_pause
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit

        self._menu = QMenu()
        self._count_action = self._menu.addAction("오늘 0번 마심")
        self._count_action.setEnabled(False)
        self._menu.addSeparator()

        self._test_action = self._menu.addAction("지금 바로 알림 보기")
        self._test_action.triggered.connect(self._on_test_notify)

        self._pause_action = self._menu.addAction("일시정지")
        self._pause_action.triggered.connect(self._on_toggle_pause)

        self._settings_action = self._menu.addAction("설정 열기")
        self._settings_action.triggered.connect(self._on_open_settings)

        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("종료")
        self._quit_action.triggered.connect(self._on_quit)

        self.setContextMenu(self._menu)
        self.setToolTip("Water Timer")
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._on_open_settings()

    def set_count(self, count: int) -> None:
        self._count_action.setText(f"오늘 {count}번 마심")

    def set_paused(self, paused: bool) -> None:
        self._pause_action.setText("재개" if paused else "일시정지")

    def set_warning(self, text: str | None) -> None:
        self.setToolTip(text or "Water Timer")
