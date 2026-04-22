"""팝업 단독 확인 (v2 디자인). `python -m scripts.smoke_popup`.

자동 닫힘 없이 띄움 — 확인 후 × 또는 창 닫기로 종료.
"""
import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication

from src.popup import Popup


def main():
    app = QApplication(sys.argv)

    def on_drank():
        print("drank!")

    def on_snooze():
        print("snoozed!")

    p = Popup(
        character_id="happy",
        message="물 한 잔 어때요?",
        auto_close_seconds=0,             # 자동 닫힘 없음
        position="center",                # 가운데 띄워서 잘 보이게
        count=3,
        goal=8,
        last_notified_at=datetime.now() - timedelta(hours=2),
        on_drank=on_drank,
        on_snooze=on_snooze,
    )
    p.show()
    app.exec()


if __name__ == "__main__":
    main()
