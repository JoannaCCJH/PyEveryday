"""
Black-box tests for scripts.productivity.reminder_system.

Derived from SPEC.md Â§reminder_system (no peeking at implementation).
Applies EP / BA / EG per proposal Â§2.2.
"""
import datetime
import json

import pytest

from scripts.productivity.reminder_system import Reminder, ReminderManager

pytestmark = pytest.mark.blackbox


def _mgr(tmp_path):
    return ReminderManager(filename=str(tmp_path / "reminders.json"))


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestAddRemoveEP:
    """EP for add/remove operations."""

    def test_add_reminder_returns_id_and_stores(self, tmp_path):
        # EP: add one -> id returned, reminder persisted.
        mgr = _mgr(tmp_path)
        now = datetime.datetime(2030, 1, 1, 10, 0)
        rid = mgr.add_reminder("take meds", now)
        assert isinstance(rid, str)
        assert len(mgr.reminders) == 1

    def test_remove_existing_id(self, tmp_path):
        # EP: remove existing id -> reminder list shrinks.
        mgr = _mgr(tmp_path)
        rid = mgr.add_reminder("x", datetime.datetime(2030, 1, 1))
        mgr.remove_reminder(rid)
        assert mgr.reminders == []

    def test_remove_nonexistent_id_is_silent(self, tmp_path):
        # EP: remove non-existent id -> no change, no raise per SPEC.
        mgr = _mgr(tmp_path)
        mgr.add_reminder("x", datetime.datetime(2030, 1, 1))
        mgr.remove_reminder("this-id-does-not-exist")
        assert len(mgr.reminders) == 1


class TestCalculateNextTimeEP:
    """EP for calculate_next_time: m / h / d suffix classes + unknown fallback."""

    @pytest.mark.parametrize("interval, delta", [
        ("30m", datetime.timedelta(minutes=30)),
        ("2h",  datetime.timedelta(hours=2)),
        ("1d",  datetime.timedelta(days=1)),
    ])
    def test_known_suffixes(self, tmp_path, interval, delta):
        # EP: one representative per suffix class.
        mgr = _mgr(tmp_path)
        t0 = datetime.datetime(2030, 1, 1, 0, 0)
        assert mgr.calculate_next_time(t0, interval) == t0 + delta

    def test_unknown_suffix_fallback_to_one_hour(self, tmp_path):
        # EP: unknown-suffix class -> falls back to +1h per SPEC.
        mgr = _mgr(tmp_path)
        t0 = datetime.datetime(2030, 1, 1, 0, 0)
        result = mgr.calculate_next_time(t0, "bogus_interval")
        assert result == t0 + datetime.timedelta(hours=1)


class TestParseTimeStringEP:
    def test_iso_timestamp_parsed(self, tmp_path):
        # EP: ISO format (contains 'T') routed through fromisoformat.
        mgr = _mgr(tmp_path)
        result = mgr.parse_time_string("2030-01-01T10:00:00")
        assert result == datetime.datetime(2030, 1, 1, 10, 0, 0)

    def test_invalid_format_returns_none(self, tmp_path):
        # EP: invalid-format class -> None per SPEC.
        mgr = _mgr(tmp_path)
        assert mgr.parse_time_string("not a time") is None

    def test_hh_mm_in_future_returns_today(self, tmp_path, frozen_time):
        # EP: HH:MM > now -> today at that time. frozen_time = 2026-04-19 12:00.
        mgr = _mgr(tmp_path)
        result = mgr.parse_time_string("15:30")
        assert result is not None
        assert result.hour == 15 and result.minute == 30


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_calculate_next_time_zero_minutes(self, tmp_path):
        # BA: 0m = identity (delta = 0).
        mgr = _mgr(tmp_path)
        t0 = datetime.datetime(2030, 1, 1)
        assert mgr.calculate_next_time(t0, "0m") == t0

    def test_check_reminders_at_exact_trigger_time(self, tmp_path, monkeypatch):
        # BA: reminder_time == now (boundary - should trigger per SPEC '<=').
        mgr = _mgr(tmp_path)
        fixed_now = datetime.datetime(2030, 1, 1, 10, 0, 0)

        class _DT(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("scripts.productivity.reminder_system.datetime.datetime", _DT)
        mgr.add_reminder("exact", fixed_now)
        mgr.check_reminders()
        # Non-repeating reminder -> active=False after trigger.
        assert mgr.reminders[0].active is False

    def test_check_reminders_one_second_before_trigger(self, tmp_path, monkeypatch):
        # BA: reminder_time > now by 1 second -> not triggered.
        mgr = _mgr(tmp_path)
        fixed_now = datetime.datetime(2030, 1, 1, 10, 0, 0)
        mgr.add_reminder("future", fixed_now + datetime.timedelta(seconds=1))

        class _DT(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("scripts.productivity.reminder_system.datetime.datetime", _DT)
        mgr.check_reminders()
        assert mgr.reminders[0].active is True


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_repeat_interval_advances_reminder_time(self, tmp_path, monkeypatch):
        # EG: a repeating reminder must advance by its interval after firing.
        mgr = _mgr(tmp_path)
        fire_at = datetime.datetime(2030, 1, 1, 10, 0, 0)
        mgr.add_reminder("repeat", fire_at, repeat=True, repeat_interval="30m")

        class _DT(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fire_at

        monkeypatch.setattr("scripts.productivity.reminder_system.datetime.datetime", _DT)
        mgr.check_reminders()
        # Still active; reminder_time pushed forward by 30 minutes.
        assert mgr.reminders[0].active is True
        assert mgr.reminders[0].reminder_time == fire_at + datetime.timedelta(minutes=30)

    def test_load_missing_file_returns_empty(self, tmp_path):
        # EG: no file -> empty list, not a crash.
        mgr = ReminderManager(filename=str(tmp_path / "no_such_file.json"))
        assert mgr.reminders == []

    def test_round_trip_persistence(self, tmp_path):
        # EG: save + reload -> same data back.
        filepath = str(tmp_path / "rt.json")
        mgr = ReminderManager(filename=filepath)
        fire = datetime.datetime(2030, 6, 15, 8, 30)
        mgr.add_reminder("do X", fire)
        mgr2 = ReminderManager(filename=filepath)
        assert len(mgr2.reminders) == 1
        assert mgr2.reminders[0].message == "do X"
        assert mgr2.reminders[0].reminder_time == fire

    def test_id_collision_when_created_within_same_millisecond(self, tmp_path, monkeypatch):
        # EG / FAULT-HUNTING: SPEC Â§Gaps #6 warns that ID = int(time.time()*1000).
        # Two reminders created in the same ms share an ID. Demonstrates the
        # risk by freezing time.time().
        mgr = _mgr(tmp_path)
        monkeypatch.setattr("scripts.productivity.reminder_system.time.time", lambda: 1700000000.0)
        id1 = mgr.add_reminder("a", datetime.datetime(2030, 1, 1))
        id2 = mgr.add_reminder("b", datetime.datetime(2030, 1, 2))
        # Documenting the collision: same timestamp -> same id.
        assert id1 == id2

    def test_empty_message_accepted(self, tmp_path):
        # EG: empty message - no validation documented -> accepted.
        mgr = _mgr(tmp_path)
        rid = mgr.add_reminder("", datetime.datetime(2030, 1, 1))
        assert rid in [r.id for r in mgr.reminders]

    def test_parse_time_string_whitespace_returns_none(self, tmp_path):
        # EG: whitespace-only string -> None (no crash).
        mgr = _mgr(tmp_path)
        assert mgr.parse_time_string("   ") is None
