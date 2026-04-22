"""설정창 단독 확인. `python -m scripts.smoke_settings`."""
import sys

from PySide6.QtWidgets import QApplication

from src import config as config_mod
from src.settings_window import SettingsWindow


def main():
    app = QApplication(sys.argv)
    cfg = config_mod._default()
    dlg = SettingsWindow(
        cfg=cfg,
        current_count=3,
        on_save=lambda c: print("config saved:", c.interval_minutes, c.character_id),
        on_reset_count=lambda: print("reset!"),
        history=[],
        on_add_cup=lambda: print("+ one cup"),
    )
    dlg.show()
    app.exec()


if __name__ == "__main__":
    main()
