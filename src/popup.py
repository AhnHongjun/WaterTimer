"""알림 팝업: 이미지 + 메시지 + '물 마셨음' 버튼.

- 프레임 없는 항상-위 창
- 340×220
- 사용자 설정 위치(corner)에 배치
- 자동 닫힘 N초 (카운터 증가 X)
- '물 마셨음' 클릭 시 즉시 닫힘 + on_drank() 콜백 호출
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QGuiApplication, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect,
)


WIDTH = 340
HEIGHT = 220
MARGIN = 24           # 화면 가장자리와의 여백
THUMB = 128           # 이미지 썸네일 크기


def resolve_image_path(stored_path: str) -> Path:
    """<bundled>/xxx → 실제 경로로 치환."""
    if stored_path.startswith("<bundled>/"):
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "assets" / "bundled"  # PyInstaller 런타임 경로
        else:
            base = Path(__file__).resolve().parent / "assets" / "bundled"
        return base / stored_path.replace("<bundled>/", "", 1)
    return Path(stored_path)


def fallback_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "icon.ico"
    return Path(__file__).resolve().parent / "assets" / "icon.ico"


class Popup(QWidget):
    def __init__(self,
                 image_path: str,
                 message: str,
                 auto_close_seconds: int,
                 position: str,
                 on_drank: Callable[[], None],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._on_drank = on_drank
        self._closed = False

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)

        # --- 콘텐츠 컨테이너 (둥근 모서리 + 그림자) ---
        container = QWidget(self)
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: white;
                border-radius: 16px;
            }
            QLabel#msg {
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 14pt;
                color: #222;
            }
            QPushButton#drank {
                background-color: #4FC3F7;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 11pt;
            }
            QPushButton#drank:hover { background-color: #29B6F6; }
            QPushButton#close {
                background: transparent;
                color: #888;
                border: none;
                font-size: 14pt;
            }
            QPushButton#close:hover { color: #333; }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        container.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.addWidget(container)

        # --- 내부 레이아웃 ---
        h = QHBoxLayout(container)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(14)

        img_label = QLabel()
        img_label.setFixedSize(THUMB, THUMB)
        img_label.setAlignment(Qt.AlignCenter)
        pm = QPixmap(str(resolve_image_path(image_path)))
        if pm.isNull():
            pm = QPixmap(str(fallback_icon_path()))
        img_label.setPixmap(
            pm.scaled(THUMB, THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        h.addWidget(img_label)

        right = QVBoxLayout()
        right.setSpacing(10)

        top_row = QHBoxLayout()
        msg_label = QLabel(message)
        msg_label.setObjectName("msg")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        top_row.addWidget(msg_label, 1)

        close_btn = QPushButton("×")
        close_btn.setObjectName("close")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._close_silently)
        top_row.addWidget(close_btn, 0, Qt.AlignTop)

        right.addLayout(top_row, 1)

        drank_btn = QPushButton("물 마셨음")
        drank_btn.setObjectName("drank")
        drank_btn.clicked.connect(self._mark_drank)
        right.addWidget(drank_btn, 0, Qt.AlignRight)

        h.addLayout(right, 1)

        # 위치 배치
        self._place(position)

        # 자동 닫힘 + 페이드 아웃
        self._auto_close_ms = max(3, auto_close_seconds) * 1000
        QTimer.singleShot(self._auto_close_ms - 400, self._fade_out)
        QTimer.singleShot(self._auto_close_ms, self._close_silently)

    def _place(self, position: str) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = {
            "top_left":     (screen.x() + MARGIN, screen.y() + MARGIN),
            "top_right":    (screen.right() - WIDTH - MARGIN, screen.y() + MARGIN),
            "bottom_left":  (screen.x() + MARGIN, screen.bottom() - HEIGHT - MARGIN),
            "bottom_right": (screen.right() - WIDTH - MARGIN, screen.bottom() - HEIGHT - MARGIN),
            "center":       (screen.x() + (screen.width() - WIDTH) // 2,
                             screen.y() + (screen.height() - HEIGHT) // 2),
        }.get(position, (screen.right() - WIDTH - MARGIN, screen.bottom() - HEIGHT - MARGIN))
        self.move(x, y)

    def _mark_drank(self):
        if self._closed:
            return
        self._closed = True
        anim = getattr(self, "_anim", None)
        if anim is not None and anim.state() == QPropertyAnimation.Running:
            anim.stop()
        try:
            self._on_drank()
        finally:
            self.close()

    def _close_silently(self):
        if self._closed:
            return
        self._closed = True
        anim = getattr(self, "_anim", None)
        if anim is not None and anim.state() == QPropertyAnimation.Running:
            anim.stop()
        self.close()

    def _fade_out(self):
        if self._closed:
            return
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.start()
