"""설정 창 QDialog — 4개 탭.

탭 추가는 같은 파일 안에 _build_*_tab() 메서드로. 탭이 많아지면 분리를 고려.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QTimeEdit, QComboBox, QDialogButtonBox, QMessageBox,
)

from src import config as config_mod


POSITION_LABELS = {
    "bottom_right": "오른쪽 아래",
    "bottom_left":  "왼쪽 아래",
    "top_right":    "오른쪽 위",
    "top_left":     "왼쪽 위",
    "center":       "중앙",
}


class SettingsWindow(QDialog):
    def __init__(self, cfg: config_mod.Config, on_save: Callable[[config_mod.Config], None],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Water Timer 설정")
        self.resize(520, 420)
        self._cfg = cfg
        self._on_save = on_save

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_notify_tab(), "알림")
        # 탭 2~4는 Task 10~12에서 추가
        self.tabs.addTab(QWidget(), "이미지 & 메시지")
        self.tabs.addTab(QWidget(), "기록")
        self.tabs.addTab(QWidget(), "일반")

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ---------- 탭: 알림 ----------

    def _build_notify_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(config_mod.MIN_INTERVAL, config_mod.MAX_INTERVAL)
        self.interval_spin.setSuffix(" 분")
        self.interval_spin.setValue(self._cfg.interval_minutes)
        form.addRow("알림 간격", self.interval_spin)

        self.start_edit = QTimeEdit(QTime.fromString(self._cfg.active_start, "HH:mm"))
        self.start_edit.setDisplayFormat("HH:mm")
        form.addRow("활성 시간 시작", self.start_edit)

        self.end_edit = QTimeEdit(QTime.fromString(self._cfg.active_end, "HH:mm"))
        self.end_edit.setDisplayFormat("HH:mm")
        form.addRow("활성 시간 종료", self.end_edit)

        self.pos_combo = QComboBox()
        for key, label in POSITION_LABELS.items():
            self.pos_combo.addItem(label, key)
        self.pos_combo.setCurrentIndex(
            list(POSITION_LABELS.keys()).index(self._cfg.popup_position)
        )
        form.addRow("팝업 위치", self.pos_combo)

        self.close_spin = QSpinBox()
        self.close_spin.setRange(config_mod.MIN_AUTO_CLOSE, config_mod.MAX_AUTO_CLOSE)
        self.close_spin.setSuffix(" 초")
        self.close_spin.setValue(self._cfg.auto_close_seconds)
        form.addRow("자동 닫힘", self.close_spin)

        return w

    # ---------- 저장 ----------

    def _collect_notify_changes(self) -> dict:
        return dict(
            interval_minutes=self.interval_spin.value(),
            active_start=self.start_edit.time().toString("HH:mm"),
            active_end=self.end_edit.time().toString("HH:mm"),
            popup_position=self.pos_combo.currentData(),
            auto_close_seconds=self.close_spin.value(),
        )

    def _save(self):
        try:
            new_cfg = config_mod.replace(self._cfg, **self._collect_notify_changes())
            config_mod.save(new_cfg)
        except ValueError as e:
            QMessageBox.warning(self, "설정 오류", str(e))
            return
        self._cfg = new_cfg
        self._on_save(new_cfg)
        self.accept()
