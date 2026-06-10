# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Pironman Dashboard is a Flask-based REST API server that hosts a web dashboard for SunFounder Pironman hardware devices (Raspberry Pi-based). It serves static frontend assets and a JSON API on port 34001, with optional InfluxDB-backed time-series data logging.

The frontend (`pm_dashboard/www/`) is a pre-compiled web app built from a separate [pm_dashboard_www](https://github.com/sunfounder/pm_dashboard_www) repository. Do not edit these files directly — they are replaced from upstream releases.

## Build / Install / Run

```bash
pip3 install .                    # Install the package (editable: pip install -e .)
pm_dashboard                      # Run the entry point (defined in pyproject.toml)
```

The entry point `pm_dashboard:main` is declared in `pyproject.toml` under `[project.scripts]`. The `main` function is expected to be provided by the consuming package (not defined in this repo), which constructs a `PMDashboard` instance and calls `.start()`.

There are no tests in this repository.

## Architecture

### Module layout

```
pm_dashboard/
├── __init__.py        # Exports __version__
├── version.py         # Version string (2.0.0)
├── pm_dashboard.py    # Flask app, API routes, PMDashboard orchestration class
├── database.py        # InfluxDB 1.x wrapper for time-series history
├── data_logger.py     # Background thread: periodically reads data → writes to InfluxDB
├── config.py          # Custom INI-style config file reader/writer (preserves comments/order)
├── utils.py           # log_error decorator, merge_dict helper
└── www/               # Pre-compiled frontend (do not edit; replaced from upstream)
```

### Key design patterns

- **Module-level globals for dependency injection**: `pm_dashboard.py` uses many module-level globals (`__read_data__`, `__read_config__`, `__on_config_changed__`, `__get_ip_data__`, `__test_smtp__`, etc.) that are set by the `PMDashboard` class via setter methods. External hardware/sensor code injects its callbacks through these setters.

- **Custom INI config** (`config.py`): The `Config` class is a custom `.ini` file parser that preserves comments, blank lines, and section ordering when writing. It is NOT Python's `ConfigParser` — it implements its own `_read`/`_write` logic. Use `.get(section, option, default)` and `.set(section, option, value)` for safe access.

- **Data flow**: `PMDashboard.set_read_data(func)` → `DataLogger.set_read_data(func)` → background thread calls `func()` at interval → writes to InfluxDB via `Database.set("history", data)`. The `/get-data` and `/get-history` endpoints read from InfluxDB when history is enabled, otherwise they call the read function live.

### API

All endpoints are under `/api/v1.0/` on port `34001`. Full API docs are in `dashboard_api.md`. Key endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/get-data` | Current sensor data |
| GET | `/get-history?n=N` | Last N history records |
| GET | `/get-time-range?start=&end=&key=` | Time-range query |
| GET | `/get-config` | Current config |
| GET | `/get-ips` | Network IP data |
| GET | `/get-device-info` | Device metadata |
| POST | Various `set-*` endpoints | Update config (delegates to `__on_config_changed__`) |

### Dependencies

- **InfluxDB 1.x** (not 2.x): Uses `influxdb` Python client. The `Database` class auto-starts `influxd` as a subprocess, auto-creates the database, and manages retention policies. The InfluxDB runs locally on `localhost:8086`.
- The `sf_rpi_status` package is used only for `shutdown()`, `reboot()`, and two deprecated endpoints (`get-disks`, `get-network-interface-list`).
