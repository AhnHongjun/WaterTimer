"""팝업 단독 확인. `python scripts/smoke_popup.py` 로 실행."""
import sys
from PySide6.QtWidgets import QApplication

from src.popup import Popup


def main():
    app = QApplication(sys.argv)
    called = {"n": 0}
    def on_drank():
        called["n"] += 1
        print("drank!")
    p = Popup(
        image_path="<bundled>/img1.png",
        message="물 한 잔 어때요? 💧",
        auto_close_seconds=8,
        position="bottom_right",
        on_drank=on_drank,
    )
    p.show()
    app.exec()


if __name__ == "__main__":
    main()
