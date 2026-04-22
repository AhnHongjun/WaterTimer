"""물컵 시각화 위젯.

`design_ref/cup.jsx` 참조.
- 컵 윤곽: sky 톤 stroke
- 물: count/goal 비율까지 올라온 sky-400→sky-600 그라디언트 fill
- 상단: sin wave 애니메이션
- 중앙 카운트 라벨 "3/8" (Gaegu 700)
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QBrush, QPen, QFont,
)
from PySide6.QtWidgets import QWidget

from src import tokens


class Cup(QWidget):
    """물컵 위젯.

    Args:
        size: 위젯 한 변 픽셀 크기 (대략 정사각형, 내부 viewBox 200×240 유지).
        count, goal: 물 레벨 계산용.
    """

    def __init__(self, size: int = 220, count: int = 0, goal: int = 8, parent=None):
        super().__init__(parent)
        self._size = size
        self._count = count
        self._goal = max(1, goal)
        # viewBox 200×240 → 높이 = size * 1.2
        self.setFixedSize(size, int(size * 1.2))
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 웨이브 애니메이션용 위상
        self._wave_phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)   # 20fps 정도면 충분

    def set_counts(self, count: int, goal: int) -> None:
        self._count = count
        self._goal = max(1, goal)
        self.update()

    def _tick(self):
        self._wave_phase += 0.08
        if self._wave_phase > math.tau:
            self._wave_phase -= math.tau
        self.update()

    # ---------- paint ----------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 컵 경로 (viewBox 200×240 기준을 위젯 크기로 스케일)
        scale_x = w / 200.0
        scale_y = h / 240.0

        def sx(v):
            return v * scale_x

        def sy(v):
            return v * scale_y

        # 컵 외곽선: 사다리꼴. 디자인 ref와 유사하게 상단 폭 > 하단 폭
        top_left = QPointF(sx(30), sy(30))
        top_right = QPointF(sx(170), sy(30))
        bottom_right = QPointF(sx(150), sy(220))
        bottom_left = QPointF(sx(50), sy(220))

        cup_path = QPainterPath()
        cup_path.moveTo(top_left)
        # 상단은 열려있지만 시각적으로 살짝 타원 테두리 효과 없이 그냥 선
        cup_path.lineTo(bottom_left)
        # 바닥은 살짝 둥근 호
        cup_path.cubicTo(
            QPointF(sx(50), sy(232)), QPointF(sx(150), sy(232)), bottom_right
        )
        cup_path.lineTo(top_right)

        # 물 레벨 계산 (전체 물 가능 높이: 30 → 220, 총 190 단위)
        pct = min(1.0, self._count / self._goal)
        water_total_h = 190.0
        water_top_y = 220.0 - water_total_h * pct   # viewBox 좌표

        # 물의 좌/우 x 는 컵 내부 폭을 선형보간
        top_x_l = 30.0 + (50.0 - 30.0) * ((30.0 - water_top_y + 220.0 - 30.0) / 0.0001)  # placeholder; recompute below
        # 위 식은 dummy — 더 단순히: 컵은 상단 폭 140, 하단 폭 100. y=30→폭140, y=220→폭100.
        def inner_left(y: float) -> float:
            t = (y - 30.0) / (220.0 - 30.0)  # 0..1
            return 30.0 + (50.0 - 30.0) * t

        def inner_right(y: float) -> float:
            t = (y - 30.0) / (220.0 - 30.0)
            return 170.0 - (170.0 - 150.0) * t

        # 물 clipping path (컵 내부 모양)
        water_clip = QPainterPath()
        water_clip.moveTo(QPointF(sx(inner_left(30.0)), sy(30.0)))
        water_clip.lineTo(QPointF(sx(inner_left(220.0)), sy(220.0)))
        water_clip.cubicTo(
            QPointF(sx(inner_left(220.0)), sy(232)),
            QPointF(sx(inner_right(220.0)), sy(232)),
            QPointF(sx(inner_right(220.0)), sy(220.0)),
        )
        water_clip.lineTo(QPointF(sx(inner_right(30.0)), sy(30.0)))
        water_clip.closeSubpath()

        p.save()
        p.setClipPath(water_clip)

        # 물 표면 (웨이브 곡선)과 물 채움 경로
        water_surface = QPainterPath()
        wave_amp = 4.0   # viewBox 단위
        # 수면 왼쪽부터 오른쪽까지 샘플링해 sin wave
        n_samples = 30
        left_x = inner_left(water_top_y) - 2
        right_x = inner_right(water_top_y) + 2
        water_surface.moveTo(QPointF(sx(left_x), sy(water_top_y + wave_amp)))
        for i in range(n_samples + 1):
            t = i / n_samples
            x = left_x + (right_x - left_x) * t
            y = water_top_y + wave_amp * math.sin(self._wave_phase + t * math.tau * 1.8)
            water_surface.lineTo(QPointF(sx(x), sy(y)))
        # 오른쪽 아래
        water_surface.lineTo(QPointF(sx(inner_right(220.0) + 2), sy(232)))
        # 하단 호
        water_surface.cubicTo(
            QPointF(sx(inner_right(220.0) + 2), sy(240)),
            QPointF(sx(inner_left(220.0) - 2), sy(240)),
            QPointF(sx(inner_left(220.0) - 2), sy(232)),
        )
        water_surface.closeSubpath()

        grad = QLinearGradient(QPointF(sx(100), sy(water_top_y)),
                               QPointF(sx(100), sy(220)))
        grad.setColorAt(0.0, QColor(tokens.SKY_400))
        grad.setColorAt(1.0, QColor(tokens.SKY_600))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(water_surface)

        p.restore()

        # 컵 외곽선 (물 위에 덮어 그림)
        pen = QPen(QColor(tokens.SKY_300))
        pen.setWidthF(3.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(cup_path)

        # 상단 타원 테두리(컵 입구) — 살짝 얇게
        ellipse_rect = QRectF(sx(30), sy(24), sx(140), sy(12))
        p.setPen(QPen(QColor(tokens.SKY_300), 2))
        p.drawEllipse(ellipse_rect)

        # 카운트 라벨 "N/M" — 항상 컵의 세로 중앙에 고정
        label = f"{self._count}/{self._goal}"
        font = QFont()
        font.setFamily("Gaegu")
        font.setPointSize(22)
        font.setWeight(QFont.Bold)
        p.setFont(font)
        # 텍스트 가독성을 위해 살짝 그림자
        shadow_rect = QRectF(0, sy(125 - 20) + 1, w, sy(40))
        p.setPen(QColor(0, 0, 0, 80))
        p.drawText(shadow_rect, Qt.AlignCenter, label)
        text_rect = QRectF(0, sy(125 - 20), w, sy(40))
        p.setPen(QColor("#ffffff"))
        p.drawText(text_rect, Qt.AlignCenter, label)
