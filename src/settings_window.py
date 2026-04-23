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
    QSlider, QTimeEdit, QComboBox, QGridLayout, QAbstractSpinBox, QSpinBox,
    QStyle, QStyleOptionSpinBox, QLineEdit, QMessageBox,
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
        self._close_btn = self._mk_window_btn("✕", parent_dialog._handle_close_request)
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

    def _build_history_tab(self) -> QWidget:
        return _build_history_tab_for(self)

    def _build_custom_tab(self) -> QWidget:
        return _CustomPanel(self)

    def _build_sound_tab(self) -> QWidget:
        return _SoundPanel(self)

    def _build_system_tab(self) -> QWidget:
        return _SystemPanel(self)

    # ---------- 닫기 동작 ----------

    def _handle_close_request(self) -> None:
        """타이틀바 ✕ 눌렀을 때. cfg.close_behavior에 따라 분기."""
        behavior = self._cfg.close_behavior
        if behavior == "quit":
            from PySide6.QtWidgets import QApplication
            self.accept()
            qa = QApplication.instance()
            if qa:
                qa.quit()
            return
        if behavior == "ask":
            box = QMessageBox(self)
            box.setWindowTitle("Water Timer")
            box.setText("설정창을 어떻게 닫을까요?")
            hide_btn = box.addButton("트레이로 숨기기", QMessageBox.AcceptRole)
            quit_btn = box.addButton("프로그램 종료", QMessageBox.DestructiveRole)
            box.addButton("취소", QMessageBox.RejectRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked is hide_btn:
                self.accept()
            elif clicked is quit_btn:
                self.accept()
                from PySide6.QtWidgets import QApplication
                qa = QApplication.instance()
                if qa:
                    qa.quit()
            return
        # default: tray
        self.accept()

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
        self._hint_label: Optional[QLabel] = None
        if hint is not None:
            self._hint_label = QLabel(hint)
            self._hint_label.setStyleSheet(
                f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_3};"
                f"background: transparent; margin-top: 2px;"
            )
            left.addWidget(self._hint_label)
        root.addLayout(left, 1)

        self._slot = QHBoxLayout()
        self._slot.setContentsMargins(0, 0, 0, 0)
        self._slot.setSpacing(tokens.SP_SM)
        root.addLayout(self._slot, 0)

    def set_control(self, widget: QWidget) -> None:
        self._slot.addWidget(widget)

    def add_control(self, widget: QWidget) -> None:
        self._slot.addWidget(widget)

    def set_hint(self, text: str) -> None:
        if self._hint_label is not None:
            self._hint_label.setText(text)


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


# ---------- Themed SpinBox / TimeEdit (커스텀 화살표) ----------

def _paint_themed_spinbox_arrows(widget: QAbstractSpinBox) -> None:
    """위젯의 up/down 서브컨트롤 rect에 sky 톤 삼각형 아이콘을 덮어 그린다."""
    opt = QStyleOptionSpinBox()
    widget.initStyleOption(opt)
    style = widget.style()
    up_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxUp, widget)
    down_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, widget)

    painter = QPainter(widget)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(tokens.SKY_500)))

    cx = up_rect.center().x()
    cy = up_rect.center().y()
    painter.drawPolygon([
        QPoint(cx - 4, cy + 2),
        QPoint(cx + 4, cy + 2),
        QPoint(cx, cy - 3),
    ])
    cx = down_rect.center().x()
    cy = down_rect.center().y()
    painter.drawPolygon([
        QPoint(cx - 4, cy - 2),
        QPoint(cx + 4, cy - 2),
        QPoint(cx, cy + 3),
    ])


class _ThemedTimeEdit(QTimeEdit):
    def paintEvent(self, event):
        super().paintEvent(event)
        _paint_themed_spinbox_arrows(self)


class _ThemedSpinBox(QSpinBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        _paint_themed_spinbox_arrows(self)


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


# ---------- 기록 탭 ----------

def _compute_week(history, today_count: int, today_date_str: str) -> tuple[list[int], list[str]]:
    """최근 7일의 카운트와 요일 라벨. 오늘을 마지막 자리로.

    history: list[DayRecord] (오래된 것부터 시작). 오늘 날짜는 보통 없다 (아직 roll-over 전이므로).
    """
    from datetime import date as dt_date, timedelta
    # 오늘 날짜 파싱
    try:
        yy, mm, dd = map(int, today_date_str.split("-"))
        today = dt_date(yy, mm, dd)
    except Exception:
        today = dt_date.today()

    # 최근 6일 각각의 count를 history에서 찾고 없으면 0
    date_to_count = {r.date: r.count for r in history}
    week_counts: list[int] = []
    week_labels: list[str] = []
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    for i in range(6, 0, -1):
        d = today - timedelta(days=i)
        iso = d.isoformat()
        week_counts.append(date_to_count.get(iso, 0))
        week_labels.append(day_names[d.weekday()])
    # 오늘
    week_counts.append(today_count)
    week_labels.append(day_names[today.weekday()])
    return week_counts, week_labels


def _compute_stats(history, today_count: int, today_date_str: str, goal: int) -> dict:
    """주 평균 / 연속 달성 / 이번 달 합계."""
    from datetime import date as dt_date, timedelta
    try:
        yy, mm, dd = map(int, today_date_str.split("-"))
        today = dt_date(yy, mm, dd)
    except Exception:
        today = dt_date.today()

    week_counts, _ = _compute_week(history, today_count, today_date_str)
    weekly_avg = sum(week_counts) / max(1, len(week_counts))

    # 연속 달성: 어제부터 거꾸로 연속해서 goal 이상인 날 수
    date_to_count = {r.date: r.count for r in history}
    streak = 0
    d = today - timedelta(days=1)
    while True:
        iso = d.isoformat()
        c = date_to_count.get(iso)
        if c is None or c < goal:
            break
        streak += 1
        d = d - timedelta(days=1)
    # 오늘도 달성했으면 +1
    if today_count >= goal:
        streak += 1

    # 이번 달 합계: 현재 년-월로 시작하는 date의 count 합 + 오늘 카운트
    month_prefix = f"{today.year:04d}-{today.month:02d}"
    this_month = sum(r.count for r in history if r.date.startswith(month_prefix))
    this_month += today_count

    return {
        "weekly_avg": weekly_avg,
        "streak": streak,
        "this_month": this_month,
    }


class _WeeklyBar(QWidget):
    """주간 차트 하나의 막대 (숫자 위 + 막대 + 요일 라벨 아래)."""

    def __init__(self, count: int, day_label: str, ratio: float, is_today: bool, parent=None):
        super().__init__(parent)
        self._is_today = is_today
        self._ratio = ratio
        self.setMinimumWidth(28)
        self.setMaximumWidth(60)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        num = QLabel(str(count))
        num.setAlignment(Qt.AlignCenter)
        num.setStyleSheet(f"""
            font-family: {tokens.FONT_FUN};
            font-size: 14px;
            font-weight: 700;
            color: {tokens.SKY_600 if is_today else tokens.INK_3};
            background: transparent;
        """)
        root.addWidget(num)

        # 막대 영역
        self._bar_area = QWidget()
        self._bar_area.setFixedHeight(150)
        self._bar_area.setAttribute(Qt.WA_TransparentForMouseEvents)
        # 바닥 정렬을 위해 레이아웃 대신 paintEvent에서 직접 그림
        self._bar_area.paintEvent = self._paint_bar
        root.addWidget(self._bar_area)

        day = QLabel(day_label)
        day.setAlignment(Qt.AlignCenter)
        day.setStyleSheet(f"""
            font-family: {tokens.FONT_UI};
            font-size: 12px;
            font-weight: {'600' if is_today else '400'};
            color: {tokens.SKY_700 if is_today else tokens.INK_3};
            background: transparent;
        """)
        root.addWidget(day)

    def _paint_bar(self, _):
        from PySide6.QtGui import QPainter, QLinearGradient
        p = QPainter(self._bar_area)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self._bar_area.rect()
        bar_w = 20
        max_h = rect.height()
        bar_h = max(8, int(max_h * self._ratio))
        x = (rect.width() - bar_w) // 2
        y = rect.height() - bar_h
        if self._is_today:
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0.0, QColor(tokens.SKY_400))
            grad.setColorAt(1.0, QColor(tokens.SKY_700))
            p.setBrush(QBrush(grad))
        else:
            p.setBrush(QColor(tokens.SKY_300))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(x, y, bar_w, bar_h, 8, 8)


class _StatCard(QFrame):
    """소형 통계 카드: 라벨 + 큰 숫자 + 단위."""

    def __init__(self, label: str, value: str, unit: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {tokens.SURFACE_2};
                border: 1px solid {tokens.LINE};
                border-radius: 14px;
            }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(4)
        l = QLabel(label)
        l.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_3}; background: transparent;"
        )
        root.addWidget(l)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        v = QLabel(value)
        v.setStyleSheet(f"""
            font-family: {tokens.FONT_FUN};
            font-size: 26px;
            font-weight: 700;
            color: {tokens.SKY_600};
            background: transparent;
        """)
        u = QLabel(unit)
        u.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_2}; background: transparent;"
        )
        row.addWidget(v)
        row.addWidget(u)
        row.addStretch(1)
        root.addLayout(row)


class _HistoryPanel(QWidget):
    """기록 탭. +한잔/초기화/목표 변경 시 전체가 재계산·갱신된다."""

    def __init__(self, sw: "SettingsWindow", parent=None):
        super().__init__(parent)
        from src.widgets.cup import Cup

        self._sw = sw
        self.setStyleSheet(f"background-color: {tokens.SURFACE};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 제목 + hint — hint는 라이브로 갱신되어야 하므로 Section의 hint 기능 대신 수동 라벨
        title = QLabel("오늘의 수분 기록")
        title.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 18px; font-weight: 600; color: {tokens.INK}; background: transparent;"
        )
        root.addWidget(title)
        self._hint_label = QLabel("")
        self._hint_label.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 12px; color: {tokens.INK_3}; background: transparent; margin-top: 2px;"
        )
        root.addWidget(self._hint_label)
        root.addSpacing(14)

        # 2열 그리드
        grid = QHBoxLayout()
        grid.setContentsMargins(0, 8, 0, 0)
        grid.setSpacing(tokens.SP_3XL)
        root.addLayout(grid)

        # --- 좌측: Cup 카드 ---
        cup_card = QFrame()
        cup_card.setObjectName("cupCard")
        cup_card.setFixedWidth(300)
        cup_card.setStyleSheet(f"""
            QFrame#cupCard {{
                background-color: {tokens.SKY_50};
                border: 1px solid {tokens.LINE};
                border-radius: 20px;
            }}
        """)
        cup_lay = QVBoxLayout(cup_card)
        cup_lay.setContentsMargins(16, 20, 16, 16)
        cup_lay.setSpacing(14)
        cup_lay.setAlignment(Qt.AlignHCenter)

        self._cup = Cup(size=220, count=sw._current_count, goal=sw._cfg.goal)
        cup_lay.addWidget(self._cup, alignment=Qt.AlignHCenter)

        # 하루 목표 설정 — 디자인상 커스터마이즈 탭에 있지만 여기서도 빠르게 접근
        goal_row = QHBoxLayout()
        goal_row.setAlignment(Qt.AlignCenter)
        goal_row.setSpacing(8)
        goal_label = QLabel("하루 목표")
        goal_label.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 13px; color: {tokens.INK_2}; background: transparent;"
        )
        goal_row.addWidget(goal_label)
        self._goal_spin = _ThemedSpinBox()
        self._goal_spin.setRange(config_mod.MIN_GOAL, config_mod.MAX_GOAL)
        self._goal_spin.setValue(sw._cfg.goal)
        self._goal_spin.setSuffix(" 잔")
        self._goal_spin.setFixedWidth(100)
        self._goal_spin.setAlignment(Qt.AlignCenter)
        self._goal_spin.setStyleSheet(_INPUT_STYLE)
        self._goal_spin.valueChanged.connect(self._on_goal_changed)
        goal_row.addWidget(self._goal_spin)
        cup_lay.addLayout(goal_row)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        btn_row.setAlignment(Qt.AlignCenter)

        self._add_btn = QPushButton("+ 한잔")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SKY_500};
                color: #ffffff;
                border: none;
                border-radius: 999px;
                padding: 8px 20px;
                font-family: {tokens.FONT_FUN};
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_400}; }}
            QPushButton:pressed {{ background-color: {tokens.SKY_600}; }}
            QPushButton:disabled {{ background-color: {tokens.SKY_200}; color: {tokens.SURFACE}; }}
        """)
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)

        self._reset_btn = QPushButton("초기화")
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {tokens.INK_3};
                border: none;
                padding: 6px 10px;
                font-family: {tokens.FONT_UI};
                font-size: 13px;
            }}
            QPushButton:hover {{ color: {tokens.SKY_700}; }}
        """)
        self._reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(self._reset_btn)
        cup_lay.addLayout(btn_row)

        grid.addWidget(cup_card, 0)

        # --- 우측: 차트 + 통계 ---
        right = QVBoxLayout()
        right.setSpacing(20)
        right.setContentsMargins(0, 8, 0, 0)

        # 차트 컨테이너 — 내용만 교체하기 위해 별도 홀더 유지
        self._chart_wrap = QFrame()
        self._chart_wrap.setStyleSheet(
            f"background: transparent; border-bottom: 1px solid {tokens.LINE};"
        )
        self._chart_layout = QHBoxLayout(self._chart_wrap)
        self._chart_layout.setContentsMargins(0, 0, 0, tokens.SP_XL)
        self._chart_layout.setSpacing(12)
        self._chart_layout.setAlignment(Qt.AlignBottom)
        right.addWidget(self._chart_wrap)

        # 통계 홀더
        self._stats_wrap = QWidget()
        self._stats_layout = QHBoxLayout(self._stats_wrap)
        self._stats_layout.setContentsMargins(0, 0, 0, 0)
        self._stats_layout.setSpacing(12)
        right.addWidget(self._stats_wrap)

        right.addStretch(1)
        grid.addLayout(right, 1)

        root.addStretch(1)

        # 초기 렌더
        self._refresh()

    # ---------- 이벤트 ----------

    def _on_add(self):
        if self._sw._current_count >= self._sw._cfg.goal:
            return
        self._sw._on_add_cup()
        self._sw._current_count = min(self._sw._current_count + 1, self._sw._cfg.goal)
        self._refresh()

    def _on_reset(self):
        self._sw._on_reset_count()
        self._sw._current_count = 0
        self._refresh()

    def _on_goal_changed(self, value: int):
        self._sw._apply(goal=int(value))
        # 목표가 오늘 카운트보다 작아지면 카운트를 목표 이하로 당김
        if self._sw._current_count > value:
            # 기존 카운트를 새 목표까지만 인정하되, 내부 state는 보존 (호출측 책임)
            pass
        self._refresh()

    # ---------- 렌더 ----------

    def _refresh(self):
        cnt = self._sw._current_count
        goal = self._sw._cfg.goal

        # hint
        self._hint_label.setText(f"목표 {goal}잔 중 {cnt}잔 마셨어요")

        # Cup
        self._cup.set_counts(cnt, goal)

        # 목표 달성 여부에 따라 add 버튼 활성
        self._add_btn.setEnabled(cnt < goal)

        # 차트 리빌드
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        import datetime as _dt
        today_iso = _dt.date.today().isoformat()
        week_counts, week_labels = _compute_week(self._sw._history, cnt, today_iso)
        max_count = max(week_counts + [goal])
        for i, (c, lbl) in enumerate(zip(week_counts, week_labels)):
            ratio = c / max_count if max_count else 0
            bar = _WeeklyBar(count=c, day_label=lbl, ratio=ratio, is_today=(i == 6))
            self._chart_layout.addWidget(bar, 1)

        # 통계 리빌드
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        stats = _compute_stats(self._sw._history, cnt, today_iso, goal)
        self._stats_layout.addWidget(
            _StatCard("주 평균", f"{stats['weekly_avg']:.1f}", "잔"), 1
        )
        self._stats_layout.addWidget(
            _StatCard("연속 달성", f"{stats['streak']}", "일"), 1
        )
        self._stats_layout.addWidget(
            _StatCard("이번 달", f"{stats['this_month']}", "잔"), 1
        )


def _build_history_tab_for(sw: "SettingsWindow") -> QWidget:
    return _HistoryPanel(sw)


# ---------- 커스터마이즈 탭 ----------

CHARACTERS = [
    ("happy",   "기본"),
    ("excited", "신남"),
    ("sleepy",  "졸림"),
]


class _CharacterCard(QFrame):
    """캐릭터 선택 카드. 그라디언트 배경 + Droplet + 이름 라벨."""

    def __init__(self, char_id: str, name: str, selected: bool,
                 on_click: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.setObjectName("charCard")
        self._id = char_id
        self._selected = selected
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(130)
        self.setAttribute(Qt.WA_Hover, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 16, 10, 10)
        root.setSpacing(10)

        self._droplet = Droplet(size=tokens.POPUP_DROPLET_SIZE, mood=char_id)
        root.addWidget(self._droplet, alignment=Qt.AlignCenter)
        root.addStretch(1)

        self._name = QLabel(name)
        self._name.setAlignment(Qt.AlignCenter)
        root.addWidget(self._name)

        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame#charCard {{
                    background: transparent;
                    border: 2px solid {tokens.SKY_500};
                    border-radius: 16px;
                }}
                QFrame#charCard QLabel {{
                    color: {tokens.SKY_700};
                    font-family: {tokens.FONT_UI};
                    font-size: 13px;
                    font-weight: 600;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#charCard {{
                    background: transparent;
                    border: 1.5px solid {tokens.LINE_2};
                    border-radius: 16px;
                }}
                QFrame#charCard:hover {{
                    border-color: {tokens.SKY_300};
                    background: {tokens.SKY_50};
                }}
                QFrame#charCard QLabel {{
                    color: {tokens.INK_2};
                    font-family: {tokens.FONT_UI};
                    font-size: 13px;
                    background: transparent;
                }}
            """)

    def set_selected(self, selected: bool):
        if selected == self._selected:
            return
        self._selected = selected
        self._apply_style()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_click(self._id)
        super().mouseReleaseEvent(event)


class _UploadSlot(QFrame):
    """'+ 직접 업로드' 점선 카드 — v2에서는 디스플레이만, 클릭 시 안내."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("uploadSlot")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(130)
        self.setStyleSheet(f"""
            QFrame#uploadSlot {{
                background-color: {tokens.SURFACE_2};
                border: 2px dashed {tokens.LINE_2};
                border-radius: 16px;
            }}
            QFrame#uploadSlot:hover {{
                border-color: {tokens.SKY_300};
            }}
            QFrame#uploadSlot QLabel {{ background: transparent; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 16, 10, 10)
        root.setSpacing(6)
        plus = QLabel("＋")
        plus.setAlignment(Qt.AlignCenter)
        plus.setStyleSheet(
            f"font-size: 36px; color: {tokens.SKY_500};"
        )
        plus.setFixedHeight(72)
        root.addWidget(plus, alignment=Qt.AlignCenter)
        tag = QLabel("GIF / Lottie")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(
            f"font-family: {tokens.FONT_MONO}; font-size: 9px; color: {tokens.INK_3};"
            f"margin-top: 2px;"
        )
        root.addWidget(tag)
        nm = QLabel("직접 업로드")
        nm.setAlignment(Qt.AlignCenter)
        nm.setStyleSheet(
            f"font-family: {tokens.FONT_UI}; font-size: 13px; color: {tokens.INK_2};"
        )
        root.addWidget(nm)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            QMessageBox.information(
                self, "준비 중",
                "사용자 이미지 업로드는 다음 버전에서 지원됩니다.\n"
                "지금은 기본/신남/졸림 캐릭터 중 선택해 주세요."
            )
        super().mouseReleaseEvent(event)


class _MessageRow(QWidget):
    """메시지 한 줄: 입력 + × 삭제 버튼."""

    def __init__(self, text: str,
                 on_edit: Callable[[str], None],
                 on_delete: Callable[[], None],
                 parent=None):
        super().__init__(parent)
        self._on_edit = on_edit
        self._on_delete = on_delete

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._edit = QLineEdit(text)
        self._edit.setStyleSheet(f"""
            QLineEdit {{
                font-family: {tokens.FONT_UI};
                font-size: 14px;
                color: {tokens.INK};
                background-color: {tokens.SURFACE};
                border: 1.5px solid {tokens.LINE_2};
                border-radius: 10px;
                padding: 9px 14px;
            }}
            QLineEdit:focus {{ border-color: {tokens.SKY_400}; }}
            QLineEdit::placeholder {{ color: {tokens.INK_3}; }}
        """)
        self._edit.setPlaceholderText("표시할 메시지")
        # 포커스 벗어날 때(editingFinished) 저장 — 타이핑할 때마다 저장하지 않음
        self._edit.editingFinished.connect(self._handle_edit_done)
        root.addWidget(self._edit, 1)

        self._del = QPushButton()
        self._del.setCursor(Qt.PointingHandCursor)
        self._del.setFixedSize(32, 32)
        self._del.setText("✕")
        self._del.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SURFACE_2};
                color: {tokens.INK_3};
                border: none;
                border-radius: 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_50}; color: {tokens.SKY_700}; }}
        """)
        self._del.clicked.connect(self._on_delete)
        root.addWidget(self._del)

    def _handle_edit_done(self):
        self._on_edit(self._edit.text().strip())


class _CustomPanel(QWidget):
    """커스터마이즈 탭: 캐릭터 선택 + 메시지 목록."""

    def __init__(self, sw: "SettingsWindow", parent=None):
        super().__init__(parent)
        self._sw = sw
        self.setStyleSheet(f"background-color: {tokens.SURFACE};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 캐릭터 이미지 ----
        char_section = Section("캐릭터 이미지",
                               hint="팝업에 표시할 이미지를 선택하세요")
        root.addWidget(char_section)

        self._char_cards: list[_CharacterCard] = []
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(0)

        for col, (cid, name) in enumerate(CHARACTERS):
            card = _CharacterCard(cid, name,
                                  selected=(sw._cfg.character_id == cid),
                                  on_click=self._on_character_click)
            self._char_cards.append(card)
            grid.addWidget(card, 0, col)
        grid.addWidget(_UploadSlot(), 0, len(CHARACTERS))
        char_section.add_layout(grid)

        # 파일 선택 버튼 (placeholder)
        file_btn = self._make_secondary("📁 파일에서 선택...")
        file_btn.clicked.connect(lambda: QMessageBox.information(
            self, "준비 중", "사용자 이미지 업로드는 다음 버전에서 지원됩니다."
        ))
        file_btn_row = QHBoxLayout()
        file_btn_row.setContentsMargins(0, tokens.SP_LG, 0, 0)
        file_btn_row.addWidget(file_btn, alignment=Qt.AlignLeft)
        file_btn_row.addStretch(1)
        char_section.add_layout(file_btn_row)

        # ---- 알림 메시지 ----
        msg_section = Section("알림 메시지",
                              hint="랜덤하게 보여질 메시지 목록이에요")
        root.addWidget(msg_section)

        self._msg_list_holder = QWidget()
        self._msg_list_layout = QVBoxLayout(self._msg_list_holder)
        self._msg_list_layout.setContentsMargins(0, 0, 0, 0)
        self._msg_list_layout.setSpacing(10)
        msg_section.add(self._msg_list_holder)
        self._rebuild_messages()

        add_msg_btn = self._make_secondary("+ 메시지 추가")
        add_msg_btn.clicked.connect(self._on_add_message)
        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, tokens.SP_LG, 0, 0)
        add_row.addWidget(add_msg_btn, alignment=Qt.AlignLeft)
        add_row.addStretch(1)
        msg_section.add_layout(add_row)

        root.addStretch(1)

    # ---------- helpers ----------

    def _make_secondary(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SURFACE};
                color: {tokens.SKY_700};
                border: 1.5px solid {tokens.SKY_300};
                border-radius: 999px;
                padding: 8px 16px;
                font-family: {tokens.FONT_UI};
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {tokens.SKY_50}; }}
        """)
        return btn

    # ---------- 캐릭터 ----------

    def _on_character_click(self, char_id: str):
        for card in self._char_cards:
            card.set_selected(card._id == char_id)
        self._sw._apply(character_id=char_id)

    # ---------- 메시지 ----------

    def _rebuild_messages(self):
        while self._msg_list_layout.count():
            item = self._msg_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        messages = list(self._sw._cfg.messages)
        if not messages:
            hint = QLabel("메시지가 없습니다. 아래 버튼으로 추가하세요.")
            hint.setStyleSheet(
                f"font-family: {tokens.FONT_UI}; font-size: 13px; color: {tokens.INK_3};"
                f"background: transparent; padding: 4px 0;"
            )
            self._msg_list_layout.addWidget(hint)
            return

        for i, text in enumerate(messages):
            row = _MessageRow(
                text,
                on_edit=lambda new_text, idx=i: self._on_edit_message(idx, new_text),
                on_delete=lambda idx=i: self._on_delete_message(idx),
            )
            self._msg_list_layout.addWidget(row)

    def _on_edit_message(self, index: int, new_text: str):
        if not new_text:
            # 빈 문자열이면 삭제와 동일 취급
            self._on_delete_message(index)
            return
        new_cfg = config_mod.update_message(self._sw._cfg, index, new_text)
        self._sw._cfg = new_cfg
        try:
            config_mod.save(new_cfg)
        except ValueError:
            return
        self._sw._on_save(new_cfg)
        # 리스트 자체는 재빌드 불필요 (행이 자기 텍스트를 이미 가짐). 다만
        # 최초 추가 후 빈 plaheolder가 있으면 제거하기 위해 한 번 재빌드:
        # 간단히 전체 rebuild — 비용 미미
        # 여기선 타이핑 중 포커스 이동 이슈 피하기 위해 재빌드 생략.

    def _on_delete_message(self, index: int):
        new_cfg = config_mod.remove_message(self._sw._cfg, index)
        self._sw._cfg = new_cfg
        try:
            config_mod.save(new_cfg)
        except ValueError:
            return
        self._sw._on_save(new_cfg)
        self._rebuild_messages()

    def _on_add_message(self):
        new_cfg = config_mod.add_message(self._sw._cfg, "")
        self._sw._cfg = new_cfg
        # 빈 메시지는 save 전 validate 통과. 사용자가 타이핑 후 editingFinished 시 저장.
        try:
            config_mod.save(new_cfg)
        except ValueError:
            return
        self._sw._on_save(new_cfg)
        self._rebuild_messages()
        # 마지막 입력 필드에 포커스
        count = self._msg_list_layout.count()
        if count:
            last = self._msg_list_layout.itemAt(count - 1).widget()
            if isinstance(last, _MessageRow):
                last._edit.setFocus()


# ---------- 공용: Pill Toggle Switch ----------

class _Toggle(QWidget):
    """38×22 pill 토글 스위치. 디자인 spec: off=line-2 track, on=sky-500, 18px 흰 thumb."""

    def __init__(self, initial: bool, on_change: Callable[[bool], None], parent=None):
        super().__init__(parent)
        self._on = bool(initial)
        self._on_change = on_change
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)
        self.setAttribute(Qt.WA_Hover, True)

    def is_on(self) -> bool:
        return self._on

    def set_on(self, on: bool, emit: bool = True):
        if on == self._on:
            return
        self._on = on
        self.update()
        if emit:
            self._on_change(on)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.set_on(not self._on)

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        # Track
        track_color = QColor(tokens.SKY_500 if self._on else tokens.LINE_2)
        p.setPen(Qt.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(rect), rect.height() / 2, rect.height() / 2)
        # Thumb
        thumb_d = 18
        x = rect.width() - thumb_d - 2 if self._on else 2
        y = 2
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(x, y, thumb_d, thumb_d)
        # Thumb 그림자 효과(작은 1px offset)
        p.setBrush(QColor(0, 0, 0, 30))
        p.setPen(Qt.NoPen)
        # 그림자는 그냥 얇은 반투명 원
        # (완전히 정확하진 않지만 디자인상 충분)


# ---------- 사운드 탭 ----------

SOUNDS = [
    ("drop",   "물방울"),
    ("chime",  "차임"),
    ("bubble", "뽀글뽀글"),
    ("soft",   "부드러운 소리"),
    ("off",    "무음"),
]


class _SoundRow(QFrame):
    """알림음 선택 카드 한 줄: 라디오 인디케이터 + 이름 + 미리듣기 버튼."""

    def __init__(self, sound_id: str, label: str, selected: bool,
                 on_click: Callable[[str], None],
                 on_preview: Callable[[str], None],
                 parent=None):
        super().__init__(parent)
        self.setObjectName("soundRow")
        self._id = sound_id
        self._selected = selected
        self._on_click = on_click
        self._on_preview = on_preview
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedHeight(48)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 0, 12, 0)
        root.setSpacing(12)

        # 라디오 인디케이터 (18×18)
        self._indicator = _RadioIndicator(selected)
        root.addWidget(self._indicator, alignment=Qt.AlignVCenter)

        # 라벨
        self._label = QLabel(label)
        root.addWidget(self._label, 1)

        # 미리듣기 버튼 (ghost)
        preview_btn = QPushButton("미리듣기")
        preview_btn.setCursor(Qt.PointingHandCursor)
        preview_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {tokens.INK_2};
                border: none;
                padding: 4px 10px;
                font-family: {tokens.FONT_UI};
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {tokens.SKY_700}; background-color: {tokens.SURFACE}; border-radius: 8px; }}
        """)
        preview_btn.clicked.connect(lambda: self._on_preview(self._id))
        root.addWidget(preview_btn)

        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame#soundRow {{
                    background-color: {tokens.SKY_50};
                    border: 1.5px solid {tokens.SKY_300};
                    border-radius: 12px;
                }}
                QFrame#soundRow QLabel {{
                    color: {tokens.SKY_700};
                    font-family: {tokens.FONT_UI};
                    font-size: 14px;
                    font-weight: 600;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#soundRow {{
                    background-color: {tokens.SURFACE_2};
                    border: 1.5px solid transparent;
                    border-radius: 12px;
                }}
                QFrame#soundRow:hover {{
                    border-color: {tokens.SKY_200};
                }}
                QFrame#soundRow QLabel {{
                    color: {tokens.INK};
                    font-family: {tokens.FONT_UI};
                    font-size: 14px;
                    background: transparent;
                }}
            """)

    def set_selected(self, selected: bool):
        if selected == self._selected:
            return
        self._selected = selected
        self._indicator.set_selected(selected)
        self._apply_style()

    def mouseReleaseEvent(self, event):
        # 클릭이 preview 버튼 영역이 아닐 때만 선택
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            # 자식이 이미 처리한 경우(이벤트 accepted)엔 여기 안 옴
            if self.rect().contains(pos):
                self._on_click(self._id)
        super().mouseReleaseEvent(event)


class _RadioIndicator(QWidget):
    """18×18 원형 라디오 인디케이터."""

    def __init__(self, selected: bool, parent=None):
        super().__init__(parent)
        self._selected = selected
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_selected(self, selected: bool):
        if selected == self._selected:
            return
        self._selected = selected
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self._selected:
            # sky-500 border + sky-500 fill + 작은 흰 점
            p.setPen(QPen(QColor(tokens.SKY_500), 2))
            p.setBrush(QColor(tokens.SKY_500))
            p.drawEllipse(rect)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffffff"))
            inner = rect.adjusted(4, 4, -4, -4)
            p.drawEllipse(inner)
        else:
            p.setPen(QPen(QColor(tokens.LINE_2), 2))
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(rect)


class _SoundPanel(QWidget):
    """사운드 탭."""

    def __init__(self, sw: "SettingsWindow", parent=None):
        super().__init__(parent)
        self._sw = sw
        self.setStyleSheet(f"background-color: {tokens.SURFACE};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Section: 알림음 ----
        s1 = Section("알림음")
        root.addWidget(s1)

        # 소리 켜기 토글
        toggle_row = KVRow("소리 켜기")
        self._toggle = _Toggle(sw._cfg.sound_enabled, self._on_toggle_enabled)
        toggle_row.set_control(self._toggle)
        s1.add(toggle_row)

        # 볼륨
        vol_row = KVRow("볼륨", hint=f"{sw._cfg.volume}%")
        self._vol_hint_row = vol_row   # hint 업데이트용 참조
        vol_container = QWidget()
        vol_container.setFixedWidth(240)
        vol_container.setAttribute(Qt.WA_TranslucentBackground)
        vol_lay = QHBoxLayout(vol_container)
        vol_lay.setContentsMargins(0, 0, 0, 0)
        vol_lay.setSpacing(12)

        self._vol_slider = QSlider(Qt.Horizontal)
        self._vol_slider.setMinimum(0)
        self._vol_slider.setMaximum(100)
        self._vol_slider.setValue(sw._cfg.volume)
        self._vol_slider.setStyleSheet(_SLIDER_STYLE)
        # 볼륨은 항상 조절 가능. 재생 여부는 sound_enabled가 결정.
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        vol_lay.addWidget(self._vol_slider, 1)

        self._vol_label = QLabel(str(sw._cfg.volume))
        self._vol_label.setFixedWidth(36)
        self._vol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._vol_label.setStyleSheet(
            f"font-family: {tokens.FONT_FUN}; font-size: 16px; font-weight: 700;"
            f"color: {tokens.SKY_600}; background: transparent;"
        )
        vol_lay.addWidget(self._vol_label)
        vol_row.set_control(vol_container)
        s1.add(vol_row)

        # ---- Section: 알림음 선택 ----
        s2 = Section("알림음 선택")
        root.addWidget(s2)

        self._sound_rows: list[_SoundRow] = []
        sound_wrap = QWidget()
        sound_wrap.setStyleSheet("background: transparent;")
        sound_lay = QVBoxLayout(sound_wrap)
        sound_lay.setContentsMargins(0, 0, 0, 0)
        sound_lay.setSpacing(6)
        for sid, label in SOUNDS:
            row = _SoundRow(
                sid, label,
                selected=(sw._cfg.sound_name == sid),
                on_click=self._on_sound_selected,
                on_preview=self._on_preview,
            )
            self._sound_rows.append(row)
            sound_lay.addWidget(row)
        s2.add(sound_wrap)

        root.addStretch(1)

    # ---------- 핸들러 ----------

    def _on_toggle_enabled(self, on: bool):
        self._sw._apply(sound_enabled=on)

    def _on_volume_changed(self, v: int):
        self._vol_label.setText(str(v))
        self._vol_hint_row.set_hint(f"{v}%")
        self._sw._apply(volume=int(v))

    def _on_sound_selected(self, sound_id: str):
        for row in self._sound_rows:
            row.set_selected(row._id == sound_id)
        self._sw._apply(sound_name=sound_id)

    def _on_preview(self, sound_id: str):
        QMessageBox.information(
            self, "준비 중",
            f"'{dict(SOUNDS).get(sound_id, sound_id)}' 미리듣기는 다음 버전에서 지원됩니다."
        )


# ---------- 시작·트레이 탭 ----------

_CLOSE_BEHAVIORS = [
    ("tray", "트레이로 숨기기"),
    ("quit", "프로그램 종료"),
    ("ask",  "매번 물어보기"),
]


class _SystemPanel(QWidget):
    """시작·트레이 탭. autostart/minimize/tray_icon 토글 + close_behavior select."""

    def __init__(self, sw: "SettingsWindow", parent=None):
        super().__init__(parent)
        self._sw = sw
        self.setStyleSheet(f"background-color: {tokens.SURFACE};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 시작 프로그램 ----
        s1 = Section("시작 프로그램")
        root.addWidget(s1)

        auto_row = KVRow("Windows 시작 시 자동 실행", hint="컴퓨터 켜면 자동으로 실행돼요")
        self._autostart_toggle = _Toggle(
            sw._cfg.autostart,
            lambda on: self._sw._apply(autostart=on),
        )
        auto_row.set_control(self._autostart_toggle)
        s1.add(auto_row)

        min_row = KVRow("최소화 상태로 시작", hint="시작할 때 설정창을 열지 않아요")
        self._minimize_toggle = _Toggle(
            sw._cfg.minimize_on_start,
            lambda on: self._sw._apply(minimize_on_start=on),
        )
        min_row.set_control(self._minimize_toggle)
        s1.add(min_row)

        # ---- 트레이 ----
        s2 = Section("트레이")
        root.addWidget(s2)

        tray_row = KVRow("트레이 아이콘 표시",
                         hint="끄면 앱이 백그라운드에서만 돌게 돼요")
        self._tray_toggle = _Toggle(
            sw._cfg.tray_icon,
            lambda on: self._sw._apply(tray_icon=on),
        )
        tray_row.set_control(self._tray_toggle)
        s2.add(tray_row)

        close_row = KVRow("닫기 버튼 동작",
                          hint="설정 창의 X 버튼을 눌렀을 때 어떻게 할까요?")
        self._close_combo = QComboBox()
        for cid, clabel in _CLOSE_BEHAVIORS:
            self._close_combo.addItem(clabel, cid)
        # 현재 값으로 인덱스 설정
        current_idx = next(
            (i for i, (cid, _) in enumerate(_CLOSE_BEHAVIORS)
             if cid == sw._cfg.close_behavior),
            0,
        )
        self._close_combo.setCurrentIndex(current_idx)
        self._close_combo.setFixedWidth(180)
        self._close_combo.setStyleSheet(_INPUT_STYLE)
        self._close_combo.currentIndexChanged.connect(self._on_close_behavior)
        close_row.set_control(self._close_combo)
        s2.add(close_row)

        root.addStretch(1)

    def _on_close_behavior(self, _idx: int):
        self._sw._apply(close_behavior=str(self._close_combo.currentData()))
