# Chrona
Tagline: time tracking, simplified

## Stack
- Python
- PySide6
- SQLite
- Linux desktop app
- Single instance only
- Local storage in user directory
- SQLite schema is user-accessible
- Strict schema migrations

## Main window
Tabs:
- Active
- Completed
- Reports

Toolbar:
- New Activity
- Resume
- Pause
- Complete

Filter bar:
- one per tab
- applies on Enter
- partial substring match over full task string
- each tab remembers its own filter

## Task model
- Task identity is normalized full text
- case-insensitive
- whitespace-insensitive
- includes @category and #project in the name
- tasks may have no category/project
- one @category max
- one #project max
- description required
- empty input is ignored silently

## Behavior
- New Activity always enabled
- New Activity starts tracking immediately
- current activity stays on top
- starting/resuming another task auto-pauses previous active task
- explicit completion required
- completing moves task immediately to Completed
- completed tasks cannot be resumed directly
- typing the same task name merges with existing task
- if existing task was completed, revive it to Active
- no autocomplete
- clicking selects only
- double-click opens edit dialog
- multi-selection allowed; toolbar actions disabled except New Activity
- Delete key deletes selected tasks with confirmation
- no undo

## Toolbar enablement
- no selection: only New Activity
- active task selected: Pause + Complete
- paused task selected: Resume + Complete
- completed tab: only New Activity enabled
- New Activity from Completed switches to Active

## Main table
Columns:
- Task Name
- Total Time
- Last Activity

Last Activity format examples:
- 11:25 (pause)
- 12:00 (resume)

## Time editing
- separate dialog
- allowed for active and completed tasks
- prevent overlaps
- when edit causes overlap, adjust neighboring sessions
- allow edits to past dates

## Reports
- daily and weekly
- include all time in period, including ongoing active time
- previous/next buttons
- weekly label should be human-readable date range
- category is a filter
- group by Task or Project
- missing project shown as (unassigned)
- sort by time descending
- grouped children also sort by time descending
- empty report shows empty table
- remember last report settings

## Time display
- compact format
- minutes only
- refresh every minute and on focus

## Exit/reopen
- app exits fully, no tray
- active task remains active on exit
- app opens to default view
- if app was closed normally with an active task and reopened after 8h+, block with prompt to enter closing time
- suggested default is the app close time, editable
- only trigger after clean exit, not crash

## Preferences
- none in v1
- use system theme
