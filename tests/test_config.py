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


@pytest.mark.parametrize("seconds", [-1, -100, 601, 99999])
def test_invalid_auto_close_rejected(seconds):
    with pytest.raises(ValueError):
        config.validate_auto_close(seconds)


@pytest.mark.parametrize("seconds", [0, 10, 30, 60, 300, 600])
def test_valid_auto_close_accepted(seconds):
    config.validate_auto_close(seconds)  # no raise


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


# ---------- v2 신규 필드 ----------

def test_default_has_all_v2_fields(config_file):
    c = config.load()
    assert c.goal == 8
    assert c.days == [0, 1, 2, 3, 4, 5, 6]
    assert c.active_character_ids == ["happy"]
    assert c.messages == config.DEFAULT_MESSAGES
    assert c.snooze_minutes == 5
    assert c.sound_enabled is False
    assert c.sound_name == "drop"
    assert c.volume == 60
    assert c.minimize_on_start is False
    assert c.tray_icon is True
    assert c.close_behavior == "tray"


def test_v1_file_migrates_messages_from_sets(config_file):
    """기존 사용자의 config.json에 messages가 없으면 sets의 메시지로 채운다."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    v1_data = {
        "interval_minutes": 60,
        "active_start": "09:00",
        "active_end": "22:00",
        "popup_position": "bottom_right",
        "auto_close_seconds": 12,
        "autostart": True,
        "sets": [
            {"id": "a", "image_path": "x.png", "message": "메시지 A"},
            {"id": "b", "image_path": "y.png", "message": "메시지 B"},
        ],
        # messages, goal, days 등 신규 필드 전부 없음
    }
    config_file.write_text(json.dumps(v1_data, ensure_ascii=False), encoding="utf-8")
    c = config.load()
    assert c.messages == ["메시지 A", "메시지 B"]
    assert c.goal == 8  # 신규 필드는 기본값


@pytest.mark.parametrize("g", [0, -1, 17, 100])
def test_invalid_goal_rejected(g):
    with pytest.raises(ValueError):
        config.validate_goal(g)


@pytest.mark.parametrize("g", [1, 8, 16])
def test_valid_goal_accepted(g):
    config.validate_goal(g)




def test_invalid_sound_rejected():
    with pytest.raises(ValueError):
        config.validate_sound("wrong")


def test_invalid_close_behavior_rejected():
    with pytest.raises(ValueError):
        config.validate_close_behavior("burn")


@pytest.mark.parametrize("v", [-1, 101])
def test_invalid_volume_rejected(v):
    with pytest.raises(ValueError):
        config.validate_volume(v)


@pytest.mark.parametrize("v", [0, 50, 100])
def test_valid_volume_accepted(v):
    config.validate_volume(v)


@pytest.mark.parametrize("days", [[-1], [7], [1, 2, 8], "not a list"])
def test_invalid_days_rejected(days):
    with pytest.raises(ValueError):
        config.validate_days(days)


def test_valid_days_all():
    config.validate_days([0, 1, 2, 3, 4, 5, 6])


def test_message_crud(config_file):
    c = config.load()
    original_count = len(c.messages)

    c2 = config.add_message(c, "새 메시지")
    assert c2.messages[-1] == "새 메시지"
    assert len(c2.messages) == original_count + 1

    c3 = config.update_message(c2, len(c2.messages) - 1, "수정됨")
    assert c3.messages[-1] == "수정됨"

    c4 = config.remove_message(c3, 0)
    assert len(c4.messages) == original_count


def test_default_active_character_ids_is_happy(config_file):
    c = config.load()
    assert c.active_character_ids == ["happy"]


def test_migrates_builtin_character_id_to_list(config_file):
    """기존 config에 character_id='sleepy' 만 있으면 active_character_ids=['sleepy']로 마이그레이션."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    v2_data = {
        "interval_minutes": 60,
        "active_start": "09:00",
        "active_end": "22:00",
        "popup_position": "bottom_right",
        "auto_close_seconds": 12,
        "autostart": True,
        "sets": [],
        "character_id": "sleepy",
    }
    config_file.write_text(json.dumps(v2_data, ensure_ascii=False), encoding="utf-8")
    c = config.load()
    assert c.active_character_ids == ["sleepy"]


def test_migrates_custom_character_id_to_empty_builtin_list(config_file):
    """character_id='custom' 이면 빌트인은 전부 비활성. (업로드 이미지 쪽에서 처리)"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    v2_data = {
        "interval_minutes": 60,
        "active_start": "09:00",
        "active_end": "22:00",
        "popup_position": "bottom_right",
        "auto_close_seconds": 12,
        "autostart": True,
        "sets": [],
        "character_id": "custom",
    }
    config_file.write_text(json.dumps(v2_data, ensure_ascii=False), encoding="utf-8")
    c = config.load()
    assert c.active_character_ids == []


@pytest.mark.parametrize("ids", [[], ["happy"], ["happy", "sleepy"],
                                 ["happy", "excited", "sleepy"]])
def test_validate_character_list_accepts_subsets(ids):
    config.validate_character_list(ids)  # no raise


@pytest.mark.parametrize("ids", [["grumpy"], ["happy", "unknown"],
                                 "not a list", [123]])
def test_validate_character_list_rejects_invalid(ids):
    with pytest.raises(ValueError):
        config.validate_character_list(ids)
