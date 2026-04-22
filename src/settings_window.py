"""설정 창 (v2): 860×600 + 커스텀 타이틀바 + 200px 사이드바 + 5탭 스택.

탭 구성 (디자인 순서):
  🔔 알림   📊 기록(default)   🎨 커스터마이즈   🔊 사운드   ⚙️ 시작·트레이

Save/Cancel 버튼 없음 — 모든 변경은 즉시 config.save() + on_save() 콜백으로 반영.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QPoint, QSize, QTime, QByteArray, QRect, QRectF
from PySide6.QtGui import QColor, QCursor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QDialog, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy,
    QSlider, QTimeEdit, QComboBox, QGridLayout, QAbstractSpinBox,
    QStyle, QStyleOptionSpinBox,
)

from src import config as config_mod
from src import tokens
from src.widgets.droplet import Droplet


TABS = [
    ("notify",  "🔔", "알림"),
    ("history", "📊", "기록"),
    ("custom",  "🎨", "커스터마이즈"),
    ("sound",   "🔊", "사운드"),
    ("system",  "⚙️", "시작·트레이"),
]
DEFAULT_TAB = "history"


# ---------- TitleBar ----------

class _TitleBar(QFrame):
    """프레임리스 창의 36px 커스텀 타이틀바. 드래그로 창 이동."""

    def __init__(self, parent_dialog: QDialog):
        super().__init__(parent_dialog)
        self._parent_dialog = parent_dialog
        self._drag_origin: Optional[QPoint] = None
        self.setObjectName("titlebar")
        self.setFixedHeight(tokens.TITLEBAR_H)
        self.setStyleSheet(f"""
            #titlebar {{
                background-color: {tokens.SURFACE_2};
                border-bottom: 1px solid {tokens.LINE};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 0, 0, 0)
        root.setSpacing(8)

        # 좌측: 물방울 아이콘 + 타이틀
        icon = Droplet(size=18, show_face=False)
        icon.setFixedSize(18, 20)
        root.addWidget(icon, alignment=Qt.AlignVCenter)

        title = QLabel("Water Timer — 설정")
        title.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_2}; background: transparent;"
        )
        root.addWidget(title)
        root.addStretch(1)

        # 우측: –  ▢  ✕ (44×36)
        self._min_btn = self._mk_window_btn("–", self._on_minimize)
        self._max_btn = self._mk_window_btn("▢", lambda: None)   # QDialog 최대화 비활성 (시각 placeholder)
        self._max_btn.setEnabled(False)
        self._close_btn = self._mk_window_btn("✕", parent_dialog.accept)
        root.addWidget(self._min_btn)
        root.addWidget(self._max_btn)
        root.addWidget(self._close_btn)

    def _mk_window_btn(self, label: str, callback) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(44, tokens.TITLEBAR_H)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {tokens.INK_2};
                font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_50}; color: {tokens.SKY_700}; }}
            QPushButton:disabled {{ color: {tokens.INK_3}; }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _on_minimize(self):
        # QDialog에는 showMinimized()가 있지만 플랫폼에 따라 비활성화될 수 있음.
        # 트레이에 있는 앱이므로 그냥 close로도 충분하나, 디자인에 – 버튼이 있으니 지원.
        self._parent_dialog.showMinimized()

    # ---------- 창 드래그 ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self._parent_dialog.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            self._parent_dialog.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        event.accept()


# ---------- Sidebar ----------

class _TabButton(QPushButton):
    """사이드바 탭 버튼. 선택 여부에 따라 스타일 토글."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self._icon = icon
        self._label = label
        self.setText(f"  {icon}    {label}")   # 간단한 간격 조정 (실제 아이콘은 QLabel로 분리해도 되나 단순화)
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 11px 14px;
                border-radius: 12px;
                border: 1px solid transparent;
                font-family: {tokens.FONT_UI};
                font-size: 14px;
                color: {tokens.INK_2};
                background: transparent;
            }}
            QPushButton:hover {{
                background-color: {tokens.SKY_50};
                color: {tokens.SKY_700};
            }}
            QPushButton:checked {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.SKY_100};
                color: {tokens.SKY_700};
                font-weight: 600;
            }}
        """)


class _Sidebar(QFrame):
    """200px 사이드바: 5개 탭 버튼 + 하단 버전 라벨."""

    def __init__(self, on_tab_change: Callable[[str], None], parent=None):
        super().__init__(parent)
        self._on_tab_change = on_tab_change
        self.setFixedWidth(tokens.SIDEBAR_W)
        self.setStyleSheet(f"""
            _Sidebar {{
                background-color: {tokens.SURFACE};
                border-right: 1px solid {tokens.LINE};
            }}
        """)
        # QSS의 attribute selector로 직접 지정하는 대신 objectName 기반
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            #sidebar {{
                background-color: {tokens.SURFACE};
                border-right: 1px solid {tokens.LINE};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 22, 14, 14)
        root.setSpacing(4)

        self._buttons: dict[str, _TabButton] = {}
        for tab_id, icon, label in TABS:
            btn = _TabButton(icon, label, self)
            btn.clicked.connect(lambda _checked=False, tid=tab_id: self._on_tab_change(tid))
            self._buttons[tab_id] = btn
            root.addWidget(btn)

        root.addStretch(1)

        # 버전 라벨 (mono, ink-3)
        from src import __version__
        version = QLabel(f"v{__version__} · Water Timer")
        version.setStyleSheet(
            f"font-family: {tokens.FONT_MONO}; font-size: 11px; color: {tokens.INK_3};"
            f"padding-left: 14px; background: transparent;"
        )
        root.addWidget(version)

    def set_active(self, tab_id: str) -> None:
        for tid, btn in self._buttons.items():
            btn.setChecked(tid == tab_id)


# ---------- 탭 placeholder (Task 33~37에서 구현) ----------

class _EmptyTab(QWidget):
    """아직 구현 전인 탭에 띄울 placeholder."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(f"'{label}' 탭은 곧 추가됩니다.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 14px; color: {tokens.INK_3};"
        )
        root.addStretch(1)
        root.addWidget(hint)
        root.addStretch(1)


# ---------- SettingsWindow ----------

class SettingsWindow(QDialog):
    """프레임리스 설정 창. 860×600. Save/Cancel 없음 — 모든 변경은 즉시 반영."""

    def __init__(self,
                 cfg: config_mod.Config,
                 current_count: int,
                 on_save: Callable[[config_mod.Config], None],
                 on_reset_count: Callable[[], None],
                 history: Optional[list] = None,
                 on_add_cup: Optional[Callable[[], None]] = None,
                 parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._current_count = current_count
        self._history = history or []
        self._on_save = on_save
        self._on_reset_count = on_reset_count
        self._on_add_cup = on_add_cup or (lambda: None)

        # 프레임리스 + 투명 배경 (라운드 코너용)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(tokens.SETTINGS_W + 20, tokens.SETTINGS_H + 20)   # +20: 그림자 여유

        self._build_ui()
        self._activate_tab(DEFAULT_TAB)

    # ---------- 구조 ----------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        # 흰색 메인 컨테이너 (라운드 + 그림자)
        container = QFrame(self)
        container.setObjectName("settingsContainer")
        container.setStyleSheet(f"""
            #settingsContainer {{
                background-color: {tokens.SURFACE};
                border-radius: 16px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(tokens.SHADOW_LG[0])
        shadow.setOffset(tokens.SHADOW_LG[1], tokens.SHADOW_LG[2])
        r, g, b, a = tokens.SHADOW_LG[3]
        shadow.setColor(QColor(r, g, b, a))
        container.setGraphicsEffect(shadow)
        outer.addWidget(container)

        container_v = QVBoxLayout(container)
        container_v.setContentsMargins(0, 0, 0, 0)
        container_v.setSpacing(0)

        # 타이틀바
        self._titlebar = _TitleBar(self)
        container_v.addWidget(self._titlebar)

        # 본문: 사이드바 + 컨텐츠
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        container_v.addLayout(body)

        self._sidebar = _Sidebar(self._activate_tab, self)
        body.addWidget(self._sidebar)

        # 컨텐츠: 스크롤 가능 + 패딩
        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet(f"background-color: {tokens.SURFACE};")

        # 각 탭을 스크롤뷰 안에 넣어 등록
        self._tab_widgets = {}
        for tab_id, _icon, label in TABS:
            tab_widget = self._build_tab(tab_id, label)
            scroll = QScrollArea()
            scroll.setWidget(tab_widget)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            scroll.setStyleSheet(f"""
                QScrollArea {{ background-color: {tokens.SURFACE}; border: none; }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 10px;
                    margin: 4px 2px 4px 0;
                }}
                QScrollBar::handle:vertical {{
                    background: {tokens.LINE_2};
                    border-radius: 4px;
                    min-height: 30px;
                }}
                QScrollBar::handle:vertical:hover {{ background: {tokens.SKY_300}; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            """)
            self._tab_widgets[tab_id] = scroll
            self._stack.addWidget(scroll)

        body.addWidget(self._stack, 1)

    def _build_tab(self, tab_id: str, label: str) -> QWidget:
        """각 탭의 본체. Task 33~37에서 _build_notify_tab 등으로 교체됨."""
        builder = getattr(self, f"_build_{tab_id}_tab", None)
        if builder is None:
            return _EmptyTab(label)
        w = builder()
        # 외곽 패딩 (28px 36px)
        wrapper = QWidget()
        wrapper.setStyleSheet(f"background-color: {tokens.SURFACE};")
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(36, 28, 36, 28)
        lay.setSpacing(0)
        lay.addWidget(w)
        lay.addStretch(1)
        return wrapper

    # ---------- 탭 전환 ----------

    def _activate_tab(self, tab_id: str) -> None:
        if tab_id not in self._tab_widgets:
            return
        self._sidebar.set_active(tab_id)
        self._stack.setCurrentWidget(self._tab_widgets[tab_id])

    # ---------- 탭 빌더 (하단 헬퍼 함수로 위임) ----------

    def _build_notify_tab(self) -> QWidget:
        return _build_notify_tab_for(self)

    # ---------- 편의: 변경 → 저장 ----------

    def _apply(self, **changes) -> None:
        """config에 변경사항을 합성해 즉시 디스크에 저장하고 콜백 호출.

        유효성 에러 시엔 기존 상태 유지 (사용자에게 메시지 없이 무시).
        개별 탭이 유효성 책임을 지도록 기대.
        """
        try:
            new_cfg = config_mod.replace(self._cfg, **changes)
            config_mod.save(new_cfg)
        except ValueError:
            return
        self._cfg = new_cfg
        self._on_save(new_cfg)


# ---------- 디자인 공통 헬퍼 (탭 구현용 import 재사용) ----------

class Section(QWidget):
    """제목(+선택적 힌트) + 아래 내용 영역. 탭 내부에서 반복 사용."""

    def __init__(self, title: str, hint: Optional[str] = None, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, tokens.SP_3XL)
        root.setSpacing(0)
        t = QLabel(title)
        t.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 18px; font-weight: 600; color: {tokens.INK};"
            f"background: transparent;"
        )
        root.addWidget(t)
        if hint:
            h = QLabel(hint)
            h.setStyleSheet(
                f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_3};"
                f"background: transparent; margin-top: 2px;"
            )
            root.addWidget(h)
            root.addSpacing(tokens.SP_MD)
        else:
            root.addSpacing(tokens.SP_MD)
        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        root.addWidget(self._body)

    def add(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._body_layout.addLayout(layout)


class KVRow(QWidget):
    """key-value 한 줄. 좌측 라벨(+힌트), 우측 컨트롤. 하단 1px 구분선."""

    def __init__(self, label: str, hint: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: transparent; border-bottom: 1px solid {tokens.LINE};")
        root = QHBoxLayout(self)
        root.setContentsMargins(0, tokens.SP_MD, 0, tokens.SP_MD)
        root.setSpacing(tokens.SP_XL)

        left = QVBoxLayout()
        left.setSpacing(0)
        left.setContentsMargins(0, 0, 0, 0)
        l = QLabel(label)
        l.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 14px; color: {tokens.INK};"
            f"background: transparent;"
        )
        left.addWidget(l)
        if hint:
            h = QLabel(hint)
            h.setStyleSheet(
                f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_3};"
                f"background: transparent; margin-top: 2px;"
            )
            left.addWidget(h)
        root.addLayout(left, 1)

        self._slot = QHBoxLayout()
        self._slot.setContentsMargins(0, 0, 0, 0)
        self._slot.setSpacing(tokens.SP_SM)
        root.addLayout(self._slot, 0)

    def set_control(self, widget: QWidget) -> None:
        self._slot.addWidget(widget)

    def add_control(self, widget: QWidget) -> None:
        self._slot.addWidget(widget)


# ---------- 스타일 공통 ----------

_INPUT_STYLE = f"""
QAbstractSpinBox, QTimeEdit {{
    font-family: {tokens.FONT_UI};
    font-size: 14px;
    color: {tokens.INK};
    background-color: {tokens.SURFACE};
    border: 1.5px solid {tokens.LINE_2};
    border-radius: 10px;
    padding: 8px 12px;
    padding-right: 28px;
}}
QAbstractSpinBox:focus, QTimeEdit:focus {{
    border-color: {tokens.SKY_400};
}}
QAbstractSpinBox::up-button, QTimeEdit::up-button,
QAbstractSpinBox::down-button, QTimeEdit::down-button {{
    subcontrol-origin: border;
    width: 22px;
    background: transparent;
    border: none;
}}
QAbstractSpinBox::up-button, QTimeEdit::up-button {{
    subcontrol-position: top right;
    margin-top: 2px;
    margin-right: 2px;
}}
QAbstractSpinBox::down-button, QTimeEdit::down-button {{
    subcontrol-position: bottom right;
    margin-bottom: 2px;
    margin-right: 2px;
}}
QAbstractSpinBox::up-button:hover, QTimeEdit::up-button:hover,
QAbstractSpinBox::down-button:hover, QTimeEdit::down-button:hover {{
    background: {tokens.SKY_50};
    border-radius: 6px;
}}
/* 기본 화살표(::up-arrow/::down-arrow)는 paintEvent에서 오버라이드해 그림 */
QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow,
QTimeEdit::up-arrow, QTimeEdit::down-arrow {{
    width: 0; height: 0;
    image: none;
}}
QComboBox {{
    font-family: {tokens.FONT_UI};
    font-size: 14px;
    color: {tokens.INK};
    background-color: {tokens.SURFACE};
    border: 1.5px solid {tokens.LINE_2};
    border-radius: 10px;
    padding: 8px 12px;
    padding-right: 28px;
}}
QComboBox:focus {{ border-color: {tokens.SKY_400}; }}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {tokens.SURFACE};
    border: 1px solid {tokens.LINE_2};
    border-radius: 10px;
    selection-background-color: {tokens.SKY_50};
    selection-color: {tokens.SKY_700};
    padding: 4px;
    outline: none;
}}
"""

_SLIDER_STYLE = f"""
QSlider::groove:horizontal {{
    height: 8px;
    background: {tokens.SKY_100};
    border-radius: 4px;
}}
QSlider::sub-page:horizontal {{
    background: {tokens.SKY_400};
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: {tokens.SKY_500};
    width: 20px; height: 20px;
    margin: -6px 0;
    border-radius: 10px;
    border: 3px solid {tokens.SURFACE};
}}
QSlider::handle:horizontal:hover {{ background: {tokens.SKY_400}; }}
"""


# ---------- Themed QTimeEdit (커스텀 화살표) ----------

class _ThemedTimeEdit(QTimeEdit):
    """QTimeEdit 위에 sky 톤 up/down 삼각형 화살표를 그려 기본 화살표를 가린다.

    QSS로 기본 ::up-arrow/::down-arrow를 숨기고, paintEvent에서 QStyle 서브컨트롤
    rect를 얻어 그 안에 삼각형을 그린다. 버튼 클릭 동작(stepUp/stepDown)은 Qt가
    자동 처리하므로 여기선 그림만 그리면 됨.
    """

    def paintEvent(self, event):
        super().paintEvent(event)
        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        style = self.style()
        up_rect = style.subControlRect(QStyle.CC_SpinBox, opt,
                                       QStyle.SC_SpinBoxUp, self)
        down_rect = style.subControlRect(QStyle.CC_SpinBox, opt,
                                         QStyle.SC_SpinBoxDown, self)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(tokens.SKY_500)))

        # 위 삼각형: 중앙점 위쪽을 꼭짓점으로
        cx = up_rect.center().x()
        cy = up_rect.center().y()
        up_pts = [
            QPoint(cx - 4, cy + 2),
            QPoint(cx + 4, cy + 2),
            QPoint(cx, cy - 3),
        ]
        painter.drawPolygon(up_pts)

        # 아래 삼각형: 중앙점 아래쪽을 꼭짓점으로
        cx = down_rect.center().x()
        cy = down_rect.center().y()
        down_pts = [
            QPoint(cx - 4, cy - 2),
            QPoint(cx + 4, cy - 2),
            QPoint(cx, cy + 3),
        ]
        painter.drawPolygon(down_pts)


# ---------- Labeled Slider ----------

class _LabeledSlider(QWidget):
    """가로 슬라이더 + 우측에 현재 값 라벨(Gaegu 700)."""

    def __init__(self, minimum: int, maximum: int, step: int, value: int,
                 suffix: str, on_change: Callable[[int], None],
                 width: int = 260, parent=None):
        super().__init__(parent)
        self._suffix = suffix
        self._on_change = on_change
        self.setFixedWidth(width)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(tokens.SP)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setSingleStep(step)
        self._slider.setPageStep(step)
        self._slider.setValue(value)
        self._slider.setStyleSheet(_SLIDER_STYLE)
        self._slider.valueChanged.connect(self._handle_change)
        root.addWidget(self._slider, 1)

        self._label = QLabel(self._fmt(value))
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label.setFixedWidth(64)
        self._label.setStyleSheet(
            f"font-family: {tokens.FONT_FUN}; font-size: 16px; font-weight: 700;"
            f"color: {tokens.SKY_600}; background: transparent;"
        )
        root.addWidget(self._label)

    def _fmt(self, v: int) -> str:
        return f"{v}{self._suffix}"

    def _handle_change(self, v: int):
        # step 배수로 스냅
        step = self._slider.singleStep()
        if step > 1:
            snapped = round(v / step) * step
            if snapped != v:
                self._slider.blockSignals(True)
                self._slider.setValue(snapped)
                self._slider.blockSignals(False)
                v = snapped
        self._label.setText(self._fmt(v))
        self._on_change(v)


# ---------- Day buttons ----------

class _DayButton(QPushButton):
    """요일 선택용 34×34 pill 버튼. 선택 상태에 따라 스타일 토글."""

    def __init__(self, label: str, selected: bool,
                 on_toggle: Callable[[bool], None], parent=None):
        super().__init__(label, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(34, 34)
        self._selected = selected
        self._on_toggle = on_toggle
        self._apply_style()
        self.clicked.connect(self._handle_click)

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tokens.SKY_500};
                    color: #ffffff;
                    border: 1.5px solid {tokens.SKY_500};
                    border-radius: 10px;
                    font-family: {tokens.FONT_UI};
                    font-size: 13px;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tokens.SURFACE};
                    color: {tokens.INK_2};
                    border: 1.5px solid {tokens.LINE_2};
                    border-radius: 10px;
                    font-family: {tokens.FONT_UI};
                    font-size: 13px;
                }}
                QPushButton:hover {{ border-color: {tokens.SKY_300}; }}
            """)

    def _handle_click(self):
        self._selected = not self._selected
        self._apply_style()
        self._on_toggle(self._selected)


# ---------- Position Card ----------

_POSITIONS = [
    ("top_left",     "왼쪽 위"),
    ("top_right",    "오른쪽 위"),
    ("center",       "화면 중앙"),
    ("bottom_left",  "왼쪽 아래"),
    ("bottom_right", "오른쪽 아래"),
]

# 각 위치의 작은 점 좌표 (32×28 박스 기준)
_POS_DOT = {
    "top_left":     (3, 3),      # (x, y)
    "top_right":    (22, 3),
    "center":       (12, 12),
    "bottom_left":  (3, 22),
    "bottom_right": (22, 22),
}


class _PositionIcon(QWidget):
    """32×28 크기로 '점선 프레임 + 위치 점' 아이콘을 QPainter로 직접 그린다.

    QSvgWidget을 쓰면 불투명 배경이 남아 선택된 카드(파란 bg) 위에 하얀 박스처럼
    보이는 문제가 있어서 커스텀 위젯으로 교체.
    """

    def __init__(self, position_id: str, selected: bool, parent=None):
        super().__init__(parent)
        self._id = position_id
        self._selected = selected
        self.setFixedSize(32, 28)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_state(self, position_id: str, selected: bool):
        self._id = position_id
        self._selected = selected
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self._selected:
            stroke_color = QColor(255, 255, 255, int(0.8 * 255))
            dot_color = QColor("#ffffff")
        else:
            stroke_color = QColor(tokens.LINE_2)
            dot_color = QColor(tokens.INK_3)

        # 점선 프레임 (1,27) → 30×26
        pen = QPen(stroke_color)
        pen.setWidthF(1.0)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([2, 2])
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(1, 1, 30, 26), 3, 3)

        # 위치 점 7×3
        dot_x, dot_y = _POS_DOT[self._id]
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(dot_color))
        p.drawRoundedRect(QRectF(dot_x, dot_y, 7, 3), 1, 1)


class _PositionCard(QFrame):
    """팝업 위치 선택 카드: 점선 프레임 아이콘 + 라벨. QFrame + 마우스 이벤트."""

    def __init__(self, position_id: str, label: str, selected: bool,
                 on_click: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.setObjectName("positionCard")
        self._id = position_id
        self._selected = selected
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)
        self.setAttribute(Qt.WA_Hover, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 10)
        root.setSpacing(6)

        self._icon = _PositionIcon(self._id, self._selected)
        root.addWidget(self._icon, alignment=Qt.AlignCenter)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignCenter)
        root.addWidget(self._label)

        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame#positionCard {{
                    background-color: {tokens.SKY_500};
                    border: 1.5px solid {tokens.SKY_500};
                    border-radius: 12px;
                }}
                QFrame#positionCard QLabel {{
                    color: #ffffff;
                    font-family: {tokens.FONT_UI};
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#positionCard {{
                    background-color: {tokens.SURFACE};
                    border: 1.5px solid {tokens.LINE_2};
                    border-radius: 12px;
                }}
                QFrame#positionCard:hover {{
                    border-color: {tokens.SKY_300};
                }}
                QFrame#positionCard QLabel {{
                    color: {tokens.INK_2};
                    font-family: {tokens.FONT_UI};
                    font-size: 12px;
                    background: transparent;
                }}
            """)

    def set_selected(self, selected: bool):
        if selected == self._selected:
            return
        self._selected = selected
        self._icon.set_state(self._id, selected)
        self._apply_style()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_click(self._id)
        super().mouseReleaseEvent(event)


# ---------- 알림 탭 ----------

def _build_notify_tab_for(sw: "SettingsWindow") -> QWidget:
    """SettingsWindow._build_notify_tab에서 호출. sw를 참조해 config 변경 콜백 연결."""
    root = QWidget()
    root.setStyleSheet(f"background-color: {tokens.SURFACE};")
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # ---- Section: 알림 스케줄 ----
    sched = Section("알림 스케줄")
    lay.addWidget(sched)

    # 1) 알림 간격: 슬라이더 15~180 step 5
    initial_interval = max(15, min(180, sw._cfg.interval_minutes))
    interval_row = KVRow("알림 간격", hint="얼마마다 알림을 울릴까요?")
    interval_slider = _LabeledSlider(
        minimum=15, maximum=180, step=5,
        value=initial_interval, suffix="분",
        on_change=lambda v: sw._apply(interval_minutes=v),
    )
    interval_row.set_control(interval_slider)
    sched.add(interval_row)

    # 2) 활성 시간: start ~ end
    active_row = KVRow("활성 시간", hint="이 시간대에만 알림이 울려요")
    start_edit = _ThemedTimeEdit(QTime.fromString(sw._cfg.active_start, "HH:mm"))
    start_edit.setDisplayFormat("HH:mm")
    start_edit.setFixedWidth(120)
    start_edit.setStyleSheet(_INPUT_STYLE)
    end_edit = _ThemedTimeEdit(QTime.fromString(sw._cfg.active_end, "HH:mm"))
    end_edit.setDisplayFormat("HH:mm")
    end_edit.setFixedWidth(120)
    end_edit.setStyleSheet(_INPUT_STYLE)
    sep = QLabel("~")
    sep.setStyleSheet(f"color: {tokens.INK_3}; background: transparent;")

    def _update_active_window():
        s = start_edit.time().toString("HH:mm")
        e = end_edit.time().toString("HH:mm")
        sw._apply(active_start=s, active_end=e)

    start_edit.timeChanged.connect(lambda _: _update_active_window())
    end_edit.timeChanged.connect(lambda _: _update_active_window())
    active_row.add_control(start_edit)
    active_row.add_control(sep)
    active_row.add_control(end_edit)
    sched.add(active_row)

    # 3) 자동으로 닫기 (select)
    close_row = KVRow("자동으로 닫기")
    close_combo = QComboBox()
    close_combo.addItem("닫지 않음", 0)
    close_combo.addItem("10초 뒤", 10)
    close_combo.addItem("30초 뒤", 30)
    close_combo.addItem("1분 뒤", 60)
    close_combo.addItem("5분 뒤", 300)
    # 현재 값과 가장 가까운 항목 선택
    current = sw._cfg.auto_close_seconds
    options = [0, 10, 30, 60, 300]
    idx = min(range(len(options)), key=lambda i: abs(options[i] - current))
    close_combo.setCurrentIndex(idx)
    close_combo.setFixedWidth(160)
    close_combo.setStyleSheet(_INPUT_STYLE)
    close_combo.currentIndexChanged.connect(
        lambda _: sw._apply(auto_close_seconds=int(close_combo.currentData()))
    )
    close_row.set_control(close_combo)
    sched.add(close_row)

    # 4) 요일 — 7 버튼 (월~일)
    days_row = KVRow("요일")
    days_container = QWidget()
    days_container.setStyleSheet("background: transparent;")
    days_layout = QHBoxLayout(days_container)
    days_layout.setContentsMargins(0, 0, 0, 0)
    days_layout.setSpacing(6)
    day_labels = ["월", "화", "수", "목", "금", "토", "일"]
    current_days = set(sw._cfg.days)
    day_buttons: list[_DayButton] = []

    def on_day_toggle(index: int, selected: bool):
        nonlocal current_days
        if selected:
            current_days.add(index)
        else:
            current_days.discard(index)
        sw._apply(days=sorted(current_days))

    for i, lbl in enumerate(day_labels):
        # bind i via default arg
        btn = _DayButton(lbl, i in current_days,
                         on_toggle=lambda s, idx=i: on_day_toggle(idx, s))
        day_buttons.append(btn)
        days_layout.addWidget(btn)
    days_row.set_control(days_container)
    sched.add(days_row)

    # ---- Section: 팝업 위치 ----
    pos_section = Section("팝업 위치")
    lay.addWidget(pos_section)

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(0)

    pos_cards: list[_PositionCard] = []

    def on_position(chosen: str):
        for c in pos_cards:
            c.set_selected(c._id == chosen)
        sw._apply(popup_position=chosen)

    for col, (pid, plabel) in enumerate(_POSITIONS):
        card = _PositionCard(pid, plabel,
                             selected=(sw._cfg.popup_position == pid),
                             on_click=on_position)
        pos_cards.append(card)
        grid.addWidget(card, 0, col)

    pos_section.add_layout(grid)

    lay.addStretch(1)
    return root
