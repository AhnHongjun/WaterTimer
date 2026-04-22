import json

import pytest

from src import config


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path / "WaterTimer" / "config.json"


def test_load_creates_default_when_missing(config_file):
    c = config.load()
    assert c.interval_minutes == 60
    assert c.active_start == "09:00"
    assert c.active_end == "22:00"
    assert c.popup_position == "bottom_right"
    assert c.auto_close_seconds == 12
    assert c.autostart is True
    assert len(c.sets) == 5
    assert c.sets[0].message == "물 한 잔 어때요? 💧"
    assert config_file.exists()


def test_save_then_load_roundtrip(config_file):
    c = config.load()
    c2 = config.replace(c, interval_minutes=30, active_start="08:00")
    config.save(c2)
    loaded = config.load()
    assert loaded.interval_minutes == 30
    assert loaded.active_start == "08:00"


def test_corrupted_file_recovers_and_backs_up(config_file):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("{broken")
    c = config.load()
    assert c.interval_minutes == 60
    assert config_file.with_suffix(".json.bak").exists()


@pytest.mark.parametrize("minutes", [0, -5, 1441, 99999])
def test_invalid_interval_rejected(minutes):
    with pytest.raises(ValueError):
        config.validate_interval_minutes(minutes)


@pytest.mark.parametrize("minutes", [1, 60, 1440])
def test_valid_interval_accepted(minutes):
    config.validate_interval_minutes(minutes)  # no raise


def test_active_start_must_be_before_end():
    with pytest.raises(ValueError):
        config.validate_active_window("22:00", "09:00")


def test_active_window_equal_rejected():
    with pytest.raises(ValueError):
        config.validate_active_window("09:00", "09:00")


def test_active_window_valid():
    config.validate_active_window("09:00", "22:00")


def test_invalid_position_rejected():
    with pytest.raises(ValueError):
        config.validate_position("diagonal")


def test_valid_positions():
    for p in ["bottom_right", "bottom_left", "top_right", "top_left", "center"]:
        config.validate_position(p)


def test_add_remove_update_set(config_file):
    c = config.load()
    new_set = config.Set(id="new", image_path="C:/x.png", message="hi")
    c2 = config.add_set(c, new_set)
    assert len(c2.sets) == 6
    assert c2.sets[-1].id == "new"

    c3 = config.update_set(c2, "new", image_path="C:/y.png", message="bye")
    assert c3.sets[-1].image_path == "C:/y.png"
    assert c3.sets[-1].message == "bye"

    c4 = config.remove_set(c3, "new")
    assert len(c4.sets) == 5
