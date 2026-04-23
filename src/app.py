"""Water Timer 진입점.

동작:
- 트레이 아이콘 상주
- 1분마다 scheduler tick → 조건 맞으면 팝업 (요일 + 활성시간 필터)
- '지금 바로 알림 보기'로 수동 테스트
- 일시정지/재개
- 5분 뒤 스누즈 (팝업 내 버튼)
- 설정 창 (5탭)
- 종료

Phase 3 완료: 자동 시작 레지스트리, 중복 실행 방지, 에러 로깅 모두 구현됨.
"""
from __future__ import annotations

import random
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
from src.sound_player import SoundPlayer
from src.tray import Tray

TICK_MS = 60_000  # 1분


class Application:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.cfg = config_mod.load()
        self.state = state_mod.load()
        self.paused = False
        self._last_message_index: Optional[int] = None
        self._last_image_path: Optional[str] = None
        self.active_popup: Optional[Popup] = None
        self.sound_player = SoundPlayer()

        self.tray = Tray(
            icon_path=fallback_icon_path(),
            on_test_notify=self.force_notify,
            on_toggle_pause=self.toggle_pause,
            on_open_settings=self.open_settings,
            on_quit=self.quit,
        )
        self.tray.show()
        self.tray.set_count(self.state.count)
        if not self.cfg.messages:
            self.tray.set_warning("알림 메시지가 비어있습니다. 설정의 '커스터마이즈'에서 추가하세요.")

        self.timer = QTimer(self.qt_app)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        # 시작 직후 한 번 판정 (09:00 진입 등 케이스)
        QTimer.singleShot(1000, self.tick)

        # 자동 시작 레지스트리 동기화
        self._sync_autostart()

    def _sync_autostart(self):
        from src import autostart
        exe = autostart.current_exe_path()
        autostart.set_autostart(self.cfg.autostart, exe)

    # ---------- 메시지 선택 ----------

    def _pick_message(self) -> Optional[str]:
        """직전 메시지와 연속 중복을 피해 random 선택. 메시지가 없으면 None."""
        msgs = self.cfg.messages
        if not msgs:
            return None
        if len(msgs) == 1:
            self._last_message_index = 0
            return msgs[0]
        candidates = [i for i in range(len(msgs)) if i != self._last_message_index]
        idx = random.choice(candidates or list(range(len(msgs))))
        self._last_message_index = idx
        return msgs[idx]

    # ---------- tick & 발화 ----------

    def tick(self):
        # 날짜 전환 감지
        reloaded = state_mod.load()
        if reloaded.date != self.state.date:
            self.state = reloaded
            self._last_message_index = None
            self.tray.set_count(self.state.count)

        now = datetime.now()
        if not self._should_fire_now(now):
            return
        if self.active_popup is not None and self.active_popup.isVisible():
            return  # 이전 팝업 아직 떠 있음
        self.show_popup(now)

    def _should_fire_now(self, now: datetime) -> bool:
        """v2: scheduler.should_fire + 요일 필터 + messages 비어있으면 skip."""
        if not self.cfg.messages:
            return False
        # weekday(): 월=0 ~ 일=6  — cfg.days와 동일 규칙
        if now.weekday() not in self.cfg.days:
            return False
        # 기존 순수 로직 재사용 (간격·활성시간·일시정지).
        # scheduler는 sets 기반이지만 여기선 messages만 체크하면 되므로
        # 임시 Config 복제를 만들지 않고 직접 세 가지 조건을 검증한다.
        if self.paused:
            return False
        if not scheduler._in_active_window(now, self.cfg.active_start, self.cfg.active_end):
            return False
        if self.state.last_notified_at is None:
            return True
        elapsed = now - self.state.last_notified_at
        return elapsed.total_seconds() >= self.cfg.interval_minutes * 60

    def force_notify(self):
        if self.active_popup is not None and self.active_popup.isVisible():
            return
        if not self.cfg.messages:
            self.tray.showMessage("Water Timer", "알림 메시지가 없어요", icon=self.tray.Information)
            return
        self.show_popup(datetime.now(), force=True)

    def _pick_image(self) -> str:
        """character_id=='custom'일 때 활성 풀에서 랜덤 하나. 직전 것과 중복 회피."""
        paths = [p for p in self.cfg.active_image_paths if p]
        if not paths:
            return ""
        if len(paths) == 1:
            self._last_image_path = paths[0]
            return paths[0]
        candidates = [p for p in paths if p != self._last_image_path] or list(paths)
        chosen = random.choice(candidates)
        self._last_image_path = chosen
        return chosen

    def show_popup(self, now: datetime, force: bool = False):
        message = self._pick_message()
        if message is None:
            return
        image_path = ""
        if self.cfg.character_id == "custom":
            image_path = self._pick_image()
        self.active_popup = Popup(
            character_id=self.cfg.character_id,
            character_image_path=image_path,
            message=message,
            auto_close_seconds=self.cfg.auto_close_seconds,
            position=self.cfg.popup_position,
            count=self.state.count,
            goal=self.cfg.goal,
            last_notified_at=self.state.last_notified_at,
            on_drank=self.on_drank,
            on_snooze=self.on_snooze,
        )
        self.active_popup.show()
        if self.cfg.sound_enabled:
            self.sound_player.play(self.cfg.sound_name, self.cfg.volume)
        if not force:
            self.state = state_mod.update_last_notified(self.state, now)

    def on_drank(self):
        self.state = state_mod.increment_count(self.state)
        self.tray.set_count(self.state.count)

    def on_snooze(self):
        """5분 뒤 재알림. 현재 팝업이 끝난 뒤 one-shot으로 force_notify."""
        snooze_ms = max(1, self.cfg.snooze_minutes) * 60 * 1000
        QTimer.singleShot(snooze_ms, self.force_notify)

    def toggle_pause(self):
        self.paused = not self.paused
        self.tray.set_paused(self.paused)

    def open_settings(self):
        from src.settings_window import SettingsWindow
        dlg = SettingsWindow(
            cfg=self.cfg,
            current_count=self.state.count,
            history=self.state.history,
            on_save=self._on_config_saved,
            on_reset_count=self._reset_count,
            on_add_cup=self._add_cup,
            on_preview_sound=self.sound_player.play,
        )
        dlg.exec()

    def _reset_count(self):
        from dataclasses import replace
        self.state = replace(self.state, count=0)
        state_mod.save(self.state)
        self.tray.set_count(0)

    def _add_cup(self):
        """기록 탭의 '+ 한잔' 버튼용: 카운트 +1."""
        self.state = state_mod.increment_count(self.state)
        self.tray.set_count(self.state.count)

    def _on_config_saved(self, new_cfg):
        self.cfg = new_cfg
        if not self.cfg.messages:
            self.tray.set_warning("알림 메시지가 비어있습니다. 설정의 '커스터마이즈'에서 추가하세요.")
        else:
            self.tray.set_warning(None)
        self._sync_autostart()

    def quit(self):
        self.qt_app.quit()

    def run(self) -> int:
        return self.qt_app.exec()


def main():
    from src.error_log import install_excepthook
    install_excepthook()
    from src.single_instance import SingleInstanceGuard, AlreadyRunning
    try:
        with SingleInstanceGuard():
            sys.exit(Application().run())
    except AlreadyRunning:
        # 조용히 종료. Qt 메시지 박스를 띄우려면 QApplication이 필요해서
        # 간단히 Windows MessageBox를 직접 호출.
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "Water Timer가 이미 실행 중입니다.", "Water Timer", 0x40
            )
        sys.exit(0)


if __name__ == "__main__":
    main()
