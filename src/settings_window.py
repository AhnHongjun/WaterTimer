"""설정 창 (v2): 860×600 + 커스텀 타이틀바 + 200px 사이드바 + 5탭 스택.

탭 구성 (디자인 순서):
  🔔 알림   📊 기록(default)   🎨 커스터마이즈   🔊 사운드   ⚙️ 시작·트레이

Save/Cancel 버튼 없음 — 모든 변경은 즉시 config.save() + on_save() 콜백으로 반영.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QDialog, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy,
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
