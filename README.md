# Chrona

Chrona is a small and hopefully simple Linux desktop time tracker built with Python, PySide6, and SQLite. It is designed around a straightforward workflow: start an activity, let Chrona track time locally, pause or complete it when you are done, and review totals in the reports tab.

## What It Does

- Tracks work in task-based sessions.
- Stores data locally in SQLite under the user's home directory.
- Separates tasks into `Active`, `Completed`, and `Reports` views.
- Supports pausing, resuming, restarting, editing, and deleting tasks.
- Includes daily and weekly reports grouped by task or project.
- Prevents overlapping time entries when sessions are edited.

## Task Naming

Chrona uses the full task text as the task identity after normalizing case and whitespace.

Examples:

- `Write release notes @work #chrona`
- `Plan trip @personal`
- `Inbox cleanup`

The app extracts:

- one optional `@category`
- one optional `#project`

These tags are used for filtering and reporting, but the full task name remains the source of truth.

## Project Layout

- `src/chrona.py`: main PySide6 application window
- `src/db.py`: SQLite connection and migration bootstrapping
- `src/repository.py`: task persistence and query helpers
- `src/reports_pane.py`: reporting UI and report logic
- `src/task_edit_dialog.py`: task/session editing dialog
- `src/session_ops.py`: session normalization and overlap handling
- `migrations/`: SQL schema migrations
- `tests/`: unit tests
- `icons/`: application assets

## Requirements

- Linux
- Python 3.10+
- Qt libraries required by `PySide6`

Install dependencies in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install PySide6 pytest
```

## Running The App

From the repository root:

```bash
PYTHONPATH=src python src/chrona.py
```

On first launch, Chrona creates its local data directory and applies any SQL migrations automatically.

## Running Tests

```bash
PYTHONPATH=src pytest
```

## Linux Launcher Installation

Chrona includes a Freedesktop `.desktop` launcher that works across KDE, GNOME, Xfce, and other Linux desktop environments.

To install it for your current user:

```bash
chmod +x scripts/install-linux-launcher.sh
./scripts/install-linux-launcher.sh
```

This installs:

- a launcher wrapper at `~/.local/bin/chrona`
- a desktop entry at `~/.local/share/applications/chrona.desktop`
- an icon at `~/.local/share/icons/hicolor/256x256/apps/chrona.png`

The wrapper prefers the repository's `.venv/bin/python` when present and falls back to `python3`.

## Data Storage

Chrona stores its database at:

```text
~/.local/share/chrona/chrona.sqlite3
```

Schema changes are managed through the SQL files in `migrations/`.

## Current Behavior

- Starting or resuming one task pauses any currently active task.
- Completing a task moves it to the `Completed` tab.
- Restarting a completed task moves it back to `Active`.
- Report totals include active session time up to the current moment.
- The UI refreshes periodically so active durations stay current.

## Development Notes

- Data is stored locally; there is no sync layer.
- The schema is plain SQLite and intended to stay inspectable.
- Spec documents under `docs/` are kept out of version control.

## License

Chrona is released under the MIT License. See [LICENSE](/home/paulo/src/chrona/LICENSE).
