# aw-import-harvest

Import [Harvest](https://www.getharvest.com/) time entries into [ActivityWatch](https://activitywatch.net/).

Part of the [AW data portability hub](https://github.com/ActivityWatch/activitywatch/issues/1203).

## Install

```bash
pip install aw-import-harvest
```

## Setup

Get your credentials at https://id.getharvest.com/developers (Personal Access Tokens):

```bash
export HARVEST_TOKEN=your_personal_access_token
export HARVEST_ACCOUNT_ID=your_account_id
```

## Usage

```bash
# Preview what would be imported
aw-import-harvest preview

# Preview a date range
aw-import-harvest preview --from 2024-01-01 --to 2024-12-31

# Import into ActivityWatch (must be running)
aw-import-harvest import-data

# Dry run (no writes)
aw-import-harvest import-data --dry-run
```

## AW Bucket

Creates bucket `aw-import-harvest` with event type `app.harvest.timelog`.

Each event has:
- `title`: task name (or project name if no task)
- `project`: Harvest project name
- `task`: Harvest task name
- `notes`: entry notes
- `billable`: whether the entry is billable

## Related

- [aw-import-toggl](https://github.com/ActivityWatch/aw-import-toggl) — Toggl Track
- [aw-import-rescuetime](https://github.com/ActivityWatch/aw-import-rescuetime) — RescueTime
- [aw-import-manictime](https://github.com/TimeToBuildBob/aw-import-manictime) — ManicTime (SQLite)
- [aw-import-clockify](https://github.com/TimeToBuildBob/aw-import-clockify) — Clockify
