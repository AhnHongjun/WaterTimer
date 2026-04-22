from pathlib import Path
import os
from src import paths


def test_app_data_dir_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    result = paths.app_data_dir()
    assert result == tmp_path / "WaterTimer"
    assert result.is_dir()


def test_config_path_points_to_config_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.config_path() == tmp_path / "WaterTimer" / "config.json"


def test_state_path_points_to_today_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.state_path() == tmp_path / "WaterTimer" / "today.json"


def test_error_log_path_points_to_error_log(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.error_log_path() == tmp_path / "WaterTimer" / "error.log"
