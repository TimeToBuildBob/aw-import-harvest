"""Tests for aw-import-harvest."""

from aw_import_harvest import TimeEntry, _entry_to_aw_event, _harvest_headers


def _make_entry(**kwargs) -> TimeEntry:
    defaults = dict(
        id=1,
        spent_date="2024-01-15",
        hours=2.5,
        project_name="Acme Corp",
        task_name="Development",
        notes="Worked on API",
        billable=True,
        is_running=False,
        started_time=None,
        ended_time=None,
    )
    defaults.update(kwargs)
    return TimeEntry(**defaults)


def test_entry_to_aw_event_basic():
    entry = _make_entry()
    event = _entry_to_aw_event(entry)
    assert event["duration"] == 2.5 * 3600
    assert event["data"]["project"] == "Acme Corp"
    assert event["data"]["task"] == "Development"
    assert event["data"]["billable"] is True
    assert "2024-01-15" in event["timestamp"]


def test_entry_to_aw_event_title_uses_task():
    entry = _make_entry(task_name="Design", project_name="Acme")
    event = _entry_to_aw_event(entry)
    assert event["data"]["title"] == "Design"


def test_entry_to_aw_event_title_fallback_to_project():
    entry = _make_entry(task_name="", project_name="Acme")
    event = _entry_to_aw_event(entry)
    assert event["data"]["title"] == "Acme"


def test_entry_to_aw_event_no_billable():
    entry = _make_entry(billable=False)
    event = _entry_to_aw_event(entry)
    assert event["data"]["billable"] is False


def test_hours_conversion():
    entry = _make_entry(hours=1.25)
    event = _entry_to_aw_event(entry)
    assert event["duration"] == 1.25 * 3600


def test_harvest_headers():
    headers = _harvest_headers("tok123", "acc456")
    assert headers["Authorization"] == "Bearer tok123"
    assert headers["Harvest-Account-Id"] == "acc456"
    assert "User-Agent" in headers
