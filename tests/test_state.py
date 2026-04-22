import json
from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

from src import state


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path / "WaterTimer" / "today.json"


@freeze_time("2026-04-22 10:00:00")
def test_load_creates_default_when_missing(state_file):
    s = state.load()
    assert s.date == "2026-04-22"
    assert s.count == 0
    assert s.last_notified_at is None


@freeze_time("2026-04-22 10:00:00")
def test_save_then_load_roundtrip(state_file):
    s = state.State(date="2026-04-22", count=3,
                    last_notified_at=datetime(2026, 4, 22, 9, 30))
    state.save(s)
    loaded = state.load()
    assert loaded.count == 3
    assert loaded.last_notified_at == datetime(2026, 4, 22, 9, 30)


@freeze_time("2026-04-23 01:00:00")
def test_load_resets_when_date_changed(state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "date": "2026-04-22", "count": 7,
        "last_notified_at": "2026-04-22T22:00:00"
    }))
    s = state.load()
    assert s.date == "2026-04-23"
    assert s.count == 0
    assert s.last_notified_at is None  # 날짜 바뀌면 마지막 알림도 초기화


@freeze_time("2026-04-22 10:00:00")
def test_increment_count(state_file):
    s = state.load()
    s2 = state.increment_count(s)
    assert s2.count == 1
    assert state.load().count == 1


@freeze_time("2026-04-22 10:00:00")
def test_update_last_notified(state_file):
    s = state.load()
    now = datetime(2026, 4, 22, 10, 0)
    s2 = state.update_last_notified(s, now)
    assert s2.last_notified_at == now
    assert state.load().last_notified_at == now


@freeze_time("2026-04-22 10:00:00")
def test_corrupted_file_recovers_to_default_and_backs_up(state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{not valid json")
    s = state.load()
    assert s.count == 0
    assert state_file.with_suffix(".json.bak").exists()
