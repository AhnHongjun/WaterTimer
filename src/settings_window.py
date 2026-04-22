"""설정 창 QDialog — 4개 탭.

탭 추가는 같은 파일 안에 _build_*_tab() 메서드로. 탭이 많아지면 분리를 고려.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QTimeEdit, QComboBox, QDialogButtonBox, QMessageBox,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QLabel,
    QFileDialog,
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
        self.tabs.addTab(self._build_sets_tab(), "이미지 & 메시지")
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

    # ---------- 탭: 이미지 & 메시지 ----------

    def _build_sets_tab(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)

        # 좌측: 목록 + 추가/삭제
        left = QVBoxLayout()
        self.sets_list = QListWidget()
        self._reload_sets_list()
        self.sets_list.currentRowChanged.connect(self._on_set_selected)
        left.addWidget(self.sets_list)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self._add_set)
        rm_btn = QPushButton("삭제")
        rm_btn.clicked.connect(self._remove_set)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        left.addLayout(btn_row)
        h.addLayout(left, 1)

        # 우측: 편집 폼
        right = QVBoxLayout()
        form = QFormLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("이미지 파일 경로")
        browse = QPushButton("찾아보기…")
        browse.clicked.connect(self._browse_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.img_edit, 1)
        img_row.addWidget(browse)
        form.addRow("이미지", self._wrap(img_row))
        self.msg_edit = QLineEdit()
        self.msg_edit.setPlaceholderText("표시할 메시지")
        form.addRow("메시지", self.msg_edit)
        self.img_status = QLabel("")
        self.img_status.setStyleSheet("color: #c62828;")
        form.addRow("", self.img_status)
        right.addLayout(form)
        apply_btn = QPushButton("이 세트 수정 적용")
        apply_btn.clicked.connect(self._apply_set_edit)
        right.addWidget(apply_btn, 0)
        right.addStretch(1)
        h.addLayout(right, 2)

        return w

    def _wrap(self, layout) -> QWidget:
        wrapper = QWidget()
        wrapper.setLayout(layout)
        return wrapper

    def _reload_sets_list(self):
        self.sets_list.clear()
        for s in self._cfg.sets:
            self.sets_list.addItem(QListWidgetItem(f"{s.id} — {s.message[:30]}"))

    def _on_set_selected(self, row: int):
        if row < 0 or row >= len(self._cfg.sets):
            self.img_edit.setText("")
            self.msg_edit.setText("")
            self.img_status.setText("")
            return
        s = self._cfg.sets[row]
        self.img_edit.setText(s.image_path)
        self.msg_edit.setText(s.message)
        self._update_img_status(s.image_path)

    def _update_img_status(self, path_str: str):
        from src.popup import resolve_image_path
        from pathlib import Path as _P
        p = resolve_image_path(path_str) if path_str else _P("")
        if not path_str:
            self.img_status.setText("")
        elif path_str.startswith("<bundled>/") or p.exists():
            self.img_status.setText("")
        else:
            self.img_status.setText(f"경고: 이미지 파일을 찾을 수 없습니다 ({path_str})")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "이미지 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            self.img_edit.setText(path)
            self._update_img_status(path)

    def _add_set(self):
        new = config_mod.Set(id=config_mod.new_set_id(),
                             image_path="", message="새 메시지")
        self._cfg = config_mod.add_set(self._cfg, new)
        self._reload_sets_list()
        self.sets_list.setCurrentRow(len(self._cfg.sets) - 1)

    def _remove_set(self):
        row = self.sets_list.currentRow()
        if row < 0 or row >= len(self._cfg.sets):
            return
        s = self._cfg.sets[row]
        self._cfg = config_mod.remove_set(self._cfg, s.id)
        self._reload_sets_list()

    def _apply_set_edit(self):
        row = self.sets_list.currentRow()
        if row < 0 or row >= len(self._cfg.sets):
            return
        s = self._cfg.sets[row]
        self._cfg = config_mod.update_set(
            self._cfg, s.id,
            image_path=self.img_edit.text().strip(),
            message=self.msg_edit.text().strip(),
        )
        self._reload_sets_list()
        self.sets_list.setCurrentRow(row)

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
