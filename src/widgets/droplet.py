"""물방울 캐릭터 위젯 (QSvgRenderer + QPainter).

`design_ref/droplet.jsx`의 SVG를 QSvgRenderer로 파싱해 QPainter로 직접 그린다.
QSvgWidget을 쓰면 플랫폼/Qt 버전에 따라 WA_TranslucentBackground가 안 먹혀 흰
박스가 남는 경우가 있어 커스텀 paintEvent로 교체.

mood: happy / excited / sleepy.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


VALID_MOODS = ("happy", "excited", "sleepy")


_EYES_AWAKE = """
  <ellipse cx="38" cy="56" rx="3" ry="3.5" fill="#1a3550"/>
  <ellipse cx="62" cy="56" rx="3" ry="3.5" fill="#1a3550"/>
  <ellipse cx="39" cy="55" rx="1" ry="1.2" fill="#fff"/>
  <ellipse cx="63" cy="55" rx="1" ry="1.2" fill="#fff"/>
"""

_EYES_SLEEPY = """
  <path d="M 34 55 Q 38 57 42 55" stroke="#1a3550" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 58 55 Q 62 57 66 55" stroke="#1a3550" stroke-width="2" fill="none" stroke-linecap="round"/>
"""

_MOUTH_SMILE = '<path d="M 44 64 Q 50 70 56 64" stroke="#1a3550" stroke-width="2" fill="none" stroke-linecap="round"/>'
_MOUTH_EXCITED = '<ellipse cx="50" cy="66" rx="5" ry="4" fill="#1a3550"/>'

_FACE_EXTRAS = """
  <ellipse cx="30" cy="68" rx="5" ry="3" fill="#ff9eaa" opacity="0.5"/>
  <ellipse cx="70" cy="68" rx="5" ry="3" fill="#ff9eaa" opacity="0.5"/>
"""


def _build_svg(mood: str, show_face: bool) -> str:
    eyes = _EYES_SLEEPY if mood == "sleepy" else _EYES_AWAKE
    mouth = _MOUTH_EXCITED if mood == "excited" else _MOUTH_SMILE
    face = (_FACE_EXTRAS + eyes + mouth) if show_face else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 110" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="dg" x1="0.3" y1="0" x2="0.7" y2="1">
      <stop offset="0%" stop-color="#b6dcf2"/>
      <stop offset="50%" stop-color="#5fb0dc"/>
      <stop offset="100%" stop-color="#2a72a8"/>
    </linearGradient>
  </defs>
  <path d="M 50 8 C 50 8 18 50 18 72 A 32 32 0 0 0 82 72 C 82 50 50 8 50 8 Z" fill="url(#dg)"/>
  <ellipse cx="36" cy="44" rx="8" ry="14" fill="#ffffff" opacity="0.45" transform="rotate(-20 36 44)"/>
  <ellipse cx="32" cy="60" rx="3" ry="6" fill="#ffffff" opacity="0.35" transform="rotate(-20 32 60)"/>
  <circle cx="70" cy="30" r="1.5" fill="#ffffff" opacity="0.9"/>
  <circle cx="78" cy="44" r="1" fill="#ffffff" opacity="0.8"/>
  {face}
</svg>
"""


class Droplet(QWidget):
    """물방울 캐릭터 위젯.

    Args:
        size: 한 변 픽셀. 높이는 size * 1.1 (viewBox 100×110 비율).
        mood: "happy" | "excited" | "sleepy".
        show_face: False면 얼굴 없이 실루엣만.
    """

    def __init__(self, size: int = 80, mood: str = "happy",
                 show_face: bool = True, parent=None):
        super().__init__(parent)
        if mood not in VALID_MOODS:
            mood = "happy"
        self._mood = mood
        self._show_face = show_face
        self._size = size
        self._renderer = QSvgRenderer()
        self._renderer.load(QByteArray(_build_svg(mood, show_face).encode("utf-8")))
        self.setFixedSize(size, int(size * 1.1))
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_mood(self, mood: str) -> None:
        if mood not in VALID_MOODS or mood == self._mood:
            return
        self._mood = mood
        self._renderer.load(QByteArray(_build_svg(mood, self._show_face).encode("utf-8")))
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._renderer.render(painter, QRectF(0, 0, self.width(), self.height()))
