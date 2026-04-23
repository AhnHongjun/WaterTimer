"""알림 팝업 (v2 디자인).

- 440×220, 좌측 150px 캐릭터 패널 + 우측 컨텐츠 (시간 뱃지, 제목, 부제, 진행바, 버튼 2개)
- 프레임 없음, 항상 위
- "마셨어요!" → on_drank() + 물방울 파티클 + count 증가 (호출측에서 반영)
- "5분 뒤" → on_snooze() (호출측이 5분 후 다시 띄움)
- 자동 닫힘: auto_close_seconds > 0이면 해당 초 후 페이드아웃
- 등장: 화면 하단에서 30px 아래 → 목표 위치 slide-up + fade-in 280ms
"""
from __future__ import annotations

import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QPoint, QRect,
)
from PySide6.QtGui import (
    QColor, QGuiApplication, QPainter, QPainterPath, QLinearGradient,
    QFont, QPen, QBrush, QPixmap,
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy,
)

from src import tokens
from src.widgets.droplet import Droplet


# ---------- 레거시 경로 해석 (설정창에서 이미지 미리보기 fallback 용) ----------

def resolve_image_path(stored_path: str) -> Path:
    """<bundled>/xxx → 실제 경로로 치환. 레거시 이미지 세트 지원용."""
    if stored_path.startswith("<bundled>/"):
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "assets" / "bundled"
        else:
            base = Path(__file__).resolve().parent / "assets" / "bundled"
        return base / stored_path.replace("<bundled>/", "", 1)
    return Path(stored_path)


def fallback_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = Path(__file__).resolve().parent / "assets"
    png = base / "icon.png"
    if png.exists():
        return png
    return base / "icon.ico"


# ---------- 파티클 ----------

class _DropParticle(QWidget):
    """물방울 파티클. 지정된 dx/dy로 이동하며 페이드아웃."""

    def __init__(self, size: int, color: QColor, parent: QWidget):
        super().__init__(parent)
        self._size = size
        self._color = color
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(int(size * 1.4), int(size * 1.8))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2
        path = QPainterPath()
        # 위 꼭짓점에서 시작해 우측 곡선으로 하단까지, 다시 좌측 곡선으로 위로 닫는 물방울
        path.moveTo(cx, 0)
        path.cubicTo(w, h * 0.45, w, h * 0.75, cx, h)
        path.cubicTo(0, h * 0.75, 0, h * 0.45, cx, 0)
        path.closeSubpath()
        p.fillPath(path, QBrush(self._color))


class _ProgressBar(QWidget):
    """8px 높이 진행바. sky-100 트랙 + sky-400→sky-600 그라디언트 fill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._progress = 0.0  # 0.0~1.0

    def set_progress(self, p: float):
        self._progress = max(0.0, min(1.0, p))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = 4  # half of height
        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(tokens.SKY_100))
        p.drawRoundedRect(self.rect(), r, r)
        # Fill
        fw = int(self.width() * self._progress)
        if fw > 0:
            grad = QLinearGradient(0, 0, self.width(), 0)
            grad.setColorAt(0.0, QColor(tokens.SKY_400))
            grad.setColorAt(1.0, QColor(tokens.SKY_600))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, fw, self.height(), r, r)


class _CharacterPanel(QFrame):
    """좌측 150px 캐릭터 패널: 그라디언트 bg + Droplet 또는 커스텀 이미지."""

    def __init__(self, mood: str, custom_image_path: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("charPanel")
        self.setStyleSheet(f"""
            #charPanel {{
                background-color: {tokens.SKY_100};
                border-radius: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 8)
        layout.setSpacing(0)

        # custom + 유효한 이미지면 QLabel에 scaled pixmap. 아니면 Droplet fallback.
        use_custom = (mood == "custom" and custom_image_path
                      and Path(custom_image_path).exists())
        if use_custom:
            pix = QPixmap(custom_image_path)
            if pix.isNull():
                use_custom = False
        if use_custom:
            img_label = QLabel()
            img_label.setFixedSize(tokens.POPUP_CHAR_SIZE, tokens.POPUP_CHAR_SIZE)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("background: transparent;")
            img_label.setPixmap(pix.scaled(
                tokens.POPUP_CHAR_SIZE, tokens.POPUP_CHAR_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            ))
            self._body = img_label
        else:
            # mood가 "custom"인데 이미지가 없으면 happy로 fallback
            fallback_mood = mood if mood in ("happy", "excited", "sleepy") else "happy"
            self._body = Droplet(size=tokens.POPUP_CHAR_SIZE, mood=fallback_mood)
        layout.addStretch(1)
        layout.addWidget(self._body, alignment=Qt.AlignCenter)
        layout.addStretch(1)

    def paintEvent(self, event):
        # 패널 내부에 실제 그라디언트를 그려준다 (QSS는 qlineargradient로도 가능하지만
        # QFrame 배경에 styleSheet만으로는 radial/linear 혼합이 까다로움).
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width() * 0.8, self.height())
        grad.setColorAt(0.0, QColor(tokens.SKY_50))
        grad.setColorAt(1.0, QColor(tokens.SKY_100))
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(path, QBrush(grad))

    def body_rect(self) -> QRect:
        """파티클 원점 계산용: 캐릭터(Droplet 또는 이미지) rect."""
        return self._body.geometry()


# ---------- Popup ----------

class Popup(QWidget):
    """알림 팝업 창.

    시그널:
        on_drank: "마셨어요!" 클릭 시 호출됨 (카운터 증가 책임은 호출측).
        on_snooze: "5분 뒤" 클릭 시 호출됨 (호출측이 5분 후 재알림 예약).

    Args:
        character_id: 'happy' | 'excited' | 'sleepy' | 'custom'
        character_image_path: character_id='custom'일 때 사용할 이미지 경로 (절대)
        message: 팝업에 표시할 문구
        auto_close_seconds: 0이면 자동 닫힘 비활성
        position: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right' | 'center'
        count: 현재 오늘 카운트 (진행바/서브 텍스트용)
        goal: 하루 목표
        last_notified_at: 마지막 알림 시각 (시간 뱃지에 "N시간 전" 식으로 표시)
        on_drank, on_snooze: 콜백
    """

    def __init__(self, *,
                 character_id: str,
                 message: str,
                 auto_close_seconds: int,
                 position: str,
                 count: int,
                 goal: int,
                 last_notified_at: Optional[datetime],
                 on_drank: Callable[[], None],
                 on_snooze: Callable[[], None],
                 character_image_path: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._on_drank = on_drank
        self._on_snooze = on_snooze
        self._closed = False
        self._count = count
        self._goal = max(1, goal)
        self._particles: List[_DropParticle] = []
        self._anim_refs: List[QPropertyAnimation] = []

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(tokens.POPUP_W, tokens.POPUP_H + 20)  # +20: shadow 여유

        self._build_ui(character_id, message, last_notified_at, character_image_path)
        self._place(position)

        # 자동 닫힘
        if auto_close_seconds and auto_close_seconds > 0:
            ms = auto_close_seconds * 1000
            QTimer.singleShot(max(0, ms - 400), self._fade_out)
            QTimer.singleShot(ms, self._close_silently)

    # ---------- UI 구성 ----------

    def _build_ui(self, character_id: str, message: str,
                  last_notified_at: Optional[datetime],
                  character_image_path: str = "") -> None:
        # 외곽: 투명 배경 + 내부 컨테이너 (흰색 + 라운드 + 그림자)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 4, 10, 16)

        container = QFrame(self)
        container.setObjectName("popupContainer")
        container.setStyleSheet(f"""
            #popupContainer {{
                background-color: {tokens.SURFACE};
                border-radius: 22px;
                border: 1px solid {tokens.LINE};
            }}
        """)
        # 그림자: QGraphicsDropShadowEffect + WA_TranslucentBackground 조합이
        # 자식 위젯 클릭 이벤트를 막는 Qt 버그(QTBUG-17314)가 있어 사용하지 않음.
        # 옅은 1px 테두리로 경계만 살림.
        outer.addWidget(container)

        root = QHBoxLayout(container)
        root.setContentsMargins(18, 18, 20, 18)
        root.setSpacing(14)

        # 좌측 캐릭터 패널
        self._char_panel = _CharacterPanel(character_id, character_image_path, container)
        self._char_panel.setFixedWidth(tokens.POPUP_CHAR_PANEL_W)
        root.addWidget(self._char_panel)

        # 우측 컨텐츠
        right = QVBoxLayout()
        right.setContentsMargins(0, 2, 0, 0)
        right.setSpacing(0)

        # 헤더: 빨간 뱃지 + 현재 시각
        header = QHBoxLayout()
        header.setSpacing(8)
        header.setContentsMargins(0, 0, 0, 4)
        badge = self._make_time_badge(last_notified_at)
        header.addWidget(badge)
        now_label = QLabel(datetime.now().strftime("%H:%M"))
        now_label.setStyleSheet(
            f"font-family: {tokens.FONT_MONO}; font-size: 12px; color: {tokens.INK_3};"
        )
        header.addWidget(now_label)
        header.addStretch(1)
        right.addLayout(header)

        # 타이틀
        title = QLabel(message)
        title.setWordWrap(True)
        title.setStyleSheet(f"""
            font-family: {tokens.FONT_FUN};
            font-size: 24px;
            font-weight: 700;
            color: {tokens.SKY_700};
        """)
        right.addWidget(title)

        # 서브텍스트
        remain = max(0, self._goal - self._count)
        sub = QLabel(self._format_sub(remain))
        sub.setStyleSheet(
            f"font-size: 12px; color: {tokens.INK_2}; margin-top: 2px;"
        )
        sub.setTextFormat(Qt.RichText)
        self._sub_label = sub
        right.addWidget(sub)
        right.addSpacing(10)

        # 진행바
        self._progress = _ProgressBar(container)
        self._progress.set_progress(min(self._count / self._goal, 1.0))
        right.addWidget(self._progress)
        right.addStretch(1)

        # 버튼 행
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self._primary_btn = self._make_primary("마셨어요!")
        self._primary_btn.clicked.connect(self._handle_drank)
        buttons.addWidget(self._primary_btn, 1)
        self._secondary_btn = self._make_secondary("5분 뒤")
        self._secondary_btn.clicked.connect(self._handle_snooze)
        buttons.addWidget(self._secondary_btn)
        right.addLayout(buttons)

        root.addLayout(right, 1)

        # 닫기 × 버튼 (우상단)
        self._close_btn = QPushButton("✕", container)
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {tokens.INK_3};
                font-size: 12px;
                padding: 0;
            }}
            QPushButton:hover {{ color: {tokens.INK}; }}
        """)
        self._close_btn.clicked.connect(self._close_silently)
        # 컨테이너 기준 우상단에 배치 — showEvent에서 재배치
        self._close_btn.raise_()

    def _make_time_badge(self, last_notified_at: Optional[datetime]) -> QWidget:
        text = self._format_since(last_notified_at)
        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background-color: {tokens.DANGER_BG};
                border-radius: 999px;
            }}
            QLabel {{
                color: {tokens.DANGER_FG};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(7, 3, 10, 3)
        lay.setSpacing(5)
        icon = QLabel("⏰")
        icon.setStyleSheet("font-size: 12px; background: transparent;")
        lay.addWidget(icon)
        txt = QLabel(text)
        lay.addWidget(txt)
        return w

    @staticmethod
    def _format_since(last: Optional[datetime]) -> str:
        if last is None:
            return "NEW"
        delta = datetime.now() - last
        total_min = int(delta.total_seconds() // 60)
        if total_min < 1:
            return "방금"
        if total_min < 60:
            return f"{total_min}분"
        hours = total_min // 60
        return f"{hours}h"

    def _format_sub(self, remain: int) -> str:
        if remain <= 0:
            return f'오늘 목표 <b style="color:{tokens.SKY_600};">달성!</b>'
        return f'오늘 목표까지 <b style="color:{tokens.SKY_600};">{remain}잔</b> 남았어요.'

    def _make_primary(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SKY_500};
                color: #ffffff;
                border: none;
                border-radius: 999px;
                padding: 8px 20px;
                font-family: {tokens.FONT_FUN};
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_400}; }}
            QPushButton:pressed {{ background-color: {tokens.SKY_600}; }}
        """)
        return btn

    def _make_secondary(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SURFACE};
                color: {tokens.SKY_700};
                border: 1.5px solid {tokens.SKY_300};
                border-radius: 999px;
                padding: 8px 14px;
                font-family: {tokens.FONT_FUN};
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_50}; }}
        """)
        return btn

    # ---------- 위치 & 애니메이션 ----------

    def _place(self, position: str) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        m = tokens.POPUP_MARGIN
        x, y = {
            "top_left":     (screen.x() + m, screen.y() + m),
            "top_right":    (screen.right() - w - m, screen.y() + m),
            "bottom_left":  (screen.x() + m, screen.bottom() - h - m),
            "bottom_right": (screen.right() - w - m, screen.bottom() - h - m),
            "center":       (screen.x() + (screen.width() - w) // 2,
                             screen.y() + (screen.height() - h) // 2),
        }.get(position, (screen.right() - w - m, screen.bottom() - h - m))
        self._target_pos = QPoint(x, y)
        # 최종 위치보다 30px 아래에서 시작
        self.move(x, y + 30)
        self.setWindowOpacity(0.0)

    def showEvent(self, event):
        super().showEvent(event)
        # × 버튼을 컨테이너 우상단으로 이동 (showEvent에서 geometry가 확정됨).
        # close_btn은 container의 자식이므로 container 좌표계 기준으로 move.
        container = self.findChild(QFrame, "popupContainer")
        if container:
            self._close_btn.move(
                container.width() - self._close_btn.width() - 12,
                10,
            )
            self._close_btn.raise_()
        # 트레이 기반 컨텍스트에서 팝업이 포커스·최상단을 안정적으로 차지하도록
        # 명시적으로 raise/activate. Qt.Dialog 플래그와 함께 쓰면 무해하고
        # 첫 클릭을 단순 activation으로 소비되는 상황을 예방함.
        self.raise_()
        self.activateWindow()
        self._slide_in()

    def _slide_in(self):
        group = QParallelAnimationGroup(self)
        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(280)
        pos_anim.setStartValue(self.pos())
        pos_anim.setEndValue(self._target_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        op_anim = QPropertyAnimation(self, b"windowOpacity")
        op_anim.setDuration(280)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        op_anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(pos_anim)
        group.addAnimation(op_anim)
        group.start()
        self._anim_refs.append(group)

    def _fade_out(self):
        if self._closed:
            return
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._anim_refs.append(anim)

    # ---------- 액션 ----------

    def _handle_drank(self):
        if self._closed or getattr(self, "_drank_fired", False):
            return
        self._drank_fired = True
        # 두 버튼 모두 즉시 비활성화해 중복 입력 방지
        self._primary_btn.setEnabled(False)
        self._secondary_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._count = min(self._count + 1, self._goal)
        self._progress.set_progress(min(self._count / self._goal, 1.0))
        remain = max(0, self._goal - self._count)
        self._sub_label.setText(self._format_sub(remain))
        self._spawn_particles()
        # 파티클 후 닫힘
        QTimer.singleShot(950, self._fade_out)
        QTimer.singleShot(1050, lambda: self._finalize_drank())

    def _finalize_drank(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._on_drank()
        finally:
            self.close()

    def _handle_snooze(self):
        if self._closed or getattr(self, "_drank_fired", False):
            return
        self._closed = True
        self._primary_btn.setEnabled(False)
        self._secondary_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        try:
            self._on_snooze()
        finally:
            self._fade_out()
            QTimer.singleShot(250, self.close)

    def _close_silently(self):
        if self._closed:
            return
        self._closed = True
        for a in self._anim_refs:
            try:
                a.stop()
            except Exception:
                pass
        self.close()

    def _spawn_particles(self):
        """캐릭터 위로 10개 물방울이 튀어오르는 애니메이션."""
        panel_rect = self._char_panel.geometry()
        # 컨테이너 안쪽 좌표 기준이므로 self(외곽) 기준으로 변환 필요.
        container = self.findChild(QFrame, "popupContainer")
        if not container:
            return
        # 캐릭터 패널 중앙 (self 좌표계)
        origin_x = container.x() + panel_rect.x() + panel_rect.width() // 2
        origin_y = container.y() + panel_rect.y() + panel_rect.height() // 2
        for i in range(10):
            size = int(8 + random.random() * 4)
            dx = (random.random() - 0.5) * 100
            dy = -60 - random.random() * 50
            color = QColor(tokens.SKY_400)
            color.setAlphaF(0.85)
            p = _DropParticle(size, color, self)
            p.move(origin_x - p.width() // 2, origin_y - p.height() // 2)
            p.show()
            p.raise_()
            self._particles.append(p)
            QTimer.singleShot(i * 35, lambda part=p, dx_=dx, dy_=dy: self._animate_particle(part, dx_, dy_))

    def _animate_particle(self, part: _DropParticle, dx: float, dy: float):
        if self._closed:
            return
        start_pos = part.pos()
        end_pos = QPoint(start_pos.x() + int(dx), start_pos.y() + int(dy))
        move_anim = QPropertyAnimation(part, b"pos")
        move_anim.setDuration(800)
        move_anim.setStartValue(start_pos)
        move_anim.setEndValue(end_pos)
        move_anim.setEasingCurve(QEasingCurve.OutCubic)
        op_anim = QPropertyAnimation(part, b"windowOpacity")
        op_anim.setDuration(800)
        op_anim.setStartValue(1.0)
        op_anim.setEndValue(0.0)
        op_anim.setEasingCurve(QEasingCurve.InCubic)
        group = QParallelAnimationGroup(part)
        group.addAnimation(move_anim)
        group.addAnimation(op_anim)
        group.finished.connect(part.deleteLater)
        group.start()
        self._anim_refs.append(group)
