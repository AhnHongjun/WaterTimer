"""Water Timer 진입점 (MVP).

이 버전에서는 다음이 동작:
- 트레이 아이콘 상주
- 1분마다 scheduler tick → 조건 맞으면 팝업
- '지금 바로 알림 보기'로 수동 테스트
- 일시정지/재개
- 종료

아직 없음(후속 Task에서 추가): 설정 창, 자동 시작 레지스트리, 중복 실행 방지, 에러 로깅.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src import config as config_mod
from src import scheduler
from src import state as state_mod
from src.popup import Popup, fallback_icon_path
from src.tray import Tray

TICK_MS = 60_000  # 1분


class Application:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.cfg = config_mod.load()
        self.state = state_mod.load()
        self.paused = False
        self.last_set_id: Optional[str] = None
        self.active_popup: Optional[Popup] = None

        self.tray = Tray(
            icon_path=fallback_icon_path(),
            on_test_notify=self.force_notify,
            on_toggle_pause=self.toggle_pause,
            on_open_settings=self.open_settings,
            on_quit=self.quit,
        )
        self.tray.show()
        self.tray.set_count(self.state.count)
        if not self.cfg.sets:
            self.tray.set_warning("등록된 이미지·메시지 세트가 없습니다. 설정에서 추가하세요.")

        self.timer = QTimer(self.qt_app)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        # 시작 직후 한 번 판정 (09:00 진입 등 케이스)
        QTimer.singleShot(1000, self.tick)

    # ---------- 콜백 ----------

    def tick(self):
        # 날짜 전환 감지
        reloaded = state_mod.load()
        if reloaded.date != self.state.date:
            self.state = reloaded
            self.last_set_id = None
            self.tray.set_count(self.state.count)

        now = datetime.now()
        if not scheduler.should_fire(now=now, cfg=self.cfg, state=self.state, paused=self.paused):
            return
        if self.active_popup is not None and self.active_popup.isVisible():
            return  # 이전 팝업 아직 떠 있음
        self.show_popup(now)

    def force_notify(self):
        if self.active_popup is not None and self.active_popup.isVisible():
            return
        if not self.cfg.sets:
            self.tray.showMessage("Water Timer", "등록된 세트가 없어요", icon=self.tray.Information)
            return
        self.show_popup(datetime.now(), force=True)

    def show_popup(self, now: datetime, force: bool = False):
        chosen = scheduler.select_set(sets=self.cfg.sets, last_id=self.last_set_id)
        if chosen is None:
            return
        self.last_set_id = chosen.id
        self.active_popup = Popup(
            image_path=chosen.image_path,
            message=chosen.message,
            auto_close_seconds=self.cfg.auto_close_seconds,
            position=self.cfg.popup_position,
            on_drank=self.on_drank,
        )
        self.active_popup.show()
        if not force:
            self.state = state_mod.update_last_notified(self.state, now)

    def on_drank(self):
        self.state = state_mod.increment_count(self.state)
        self.tray.set_count(self.state.count)

    def toggle_pause(self):
        self.paused = not self.paused
        self.tray.set_paused(self.paused)

    def open_settings(self):
        # MVP에서는 stub. Phase 2에서 구현.
        self.tray.showMessage("Water Timer", "설정 창은 곧 추가됩니다", icon=self.tray.Information)

    def quit(self):
        self.qt_app.quit()

    def run(self) -> int:
        return self.qt_app.exec()


def main():
    sys.exit(Application().run())


if __name__ == "__main__":
    main()
