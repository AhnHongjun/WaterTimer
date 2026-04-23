"""%APPDATA%\\WaterTimer 경로 모음. 없으면 자동 생성."""
from pathlib import Path
import os

APP_NAME = "WaterTimer"


def app_data_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(appdata) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"


def state_path() -> Path:
    return app_data_dir() / "today.json"


def error_log_path() -> Path:
    return app_data_dir() / "error.log"


def characters_dir() -> Path:
    """사용자가 업로드한 캐릭터 이미지 저장소. %APPDATA%\\WaterTimer\\characters\\"""
    d = app_data_dir() / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d
