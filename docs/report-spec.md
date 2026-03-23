Read this prompt as the source of truth for the Reports pane of a Linux desktop app called Chrona. Do not invent extra features. If something is unclear, make the smallest reasonable assumption and document it briefly.

Project context:
- App name: Chrona
- Tagline: time tracking, simplified
- Stack: Python + PySide6 + SQLite
- Linux desktop app
- System theme only
- No preferences dialog in v1
- Reports pane is read-only in v1
- No export in v1

Task:
Design and implement the Reports pane only. Keep the implementation modular and ready to connect to the existing main window tabs. Do not implement unrelated app features unless required as minimal scaffolding.

Reports pane requirements:

1. Purpose
- Show summarized time worked over a selected period.
- Support daily and weekly reports.
- Include all time in the selected period:
  - completed sessions
  - paused sessions
  - currently active session time up to now
- Exclude time outside the selected period.
- If a session crosses the period boundary, count only the overlapping portion.

2. Layout
The pane should contain:
- Report type selector:
  - Daily
  - Weekly
- Previous button
- Human-readable period label
- Next button
- Category filter dropdown
- Group by dropdown
- Results table/tree
- Total row
- Filter text box at the bottom

No Generate button. Changing controls should update the report immediately.

3. Period behavior
- Daily mode:
  - Period is one local calendar day
  - Label example: Mar 23, 2026
  - Previous/Next move by one day
- Weekly mode:
  - Period is Monday 00:00 to next Monday 00:00 in local time
  - Label example: Mar 17 – Mar 23
  - Do not show ISO week numbers like W13
  - Previous/Next move by one week

4. Filters and grouping
- Category filter:
  - First option: All
  - Then known categories found in data, such as work, personal
  - Category acts only as a filter, not a grouping dimension
- Group by dropdown:
  - Task
  - Project
- Text filter:
  - Plain substring match
  - Case-insensitive
  - Partial matches allowed
  - No special parsing for @category or #project
  - Applied only when Enter is pressed
  - Reports tab remembers its own filter text

5. Data rules
Task naming model:
- Full task text is the identity string
- It may contain free text plus @category and #project
- Category and project are embedded in the task text
- At most one @category
- At most one #project
- Task may have no category and/or no project

Project reporting:
- If a task has no project, show it under:
  (unassigned)

6. Presentation
Use compact time formatting:
- 5m
- 1h 05m
- 8h 20m
Minutes only, no seconds.

The main results area should behave like this:

If Group by = Task:
- Show a flat list
- Columns:
  - Name
  - Time
- Sort rows by time descending

If Group by = Project:
- Show a hierarchical grouped view
- Top-level rows are project groups, such as:
  - #backend
  - #website
  - (unassigned)
- Child rows are tasks belonging to that project
- Sort project groups by total time descending
- Sort tasks inside each group by time descending
- Always keep (unassigned) at the bottom even if its total is larger than other groups

7. Total row
- Always show a Total row at the bottom
- Total is the sum of all visible rows after applying category filter and text filter

8. Empty state
- Show normal headers and Total row
- No special empty-state message
- Total may be shown as 0m

9. Interaction
- Reports pane is read-only
- No toolbar actions depend on report row selection
- Double-click on report rows does nothing in v1
- Selection, if present, has no side effects

10. Remembered state
The Reports pane should remember:
- last report type
- last viewed day/week
- last category filter
- last grouping choice
- last text filter

Implement this so it can be restored by the app later. For now, local in-memory state inside the pane is acceptable if persistence is not yet wired.

11. Recommended initial defaults
On first open:
- Report type: Weekly
- Period: current week
- Category: All
- Group by: Project
- Filter: empty

12. Implementation guidance
- Use PySide6 widgets only
- Keep the code clean and split into reasonable units
- Prefer a dedicated widget/class for the Reports pane
- Keep data/query logic separate from widget rendering logic
- Add a small mock data adapter or interface if the real database layer is not yet available
- Make it easy to connect a real SQLite-backed repository later

13. Deliverables
Please produce:
1. A short implementation plan
2. The widget/class structure you propose
3. The code for the Reports pane
4. Any minimal supporting classes/interfaces needed
5. A brief note on how to connect it to the rest of Chrona later

Important constraints:
- Do not implement export
- Do not implement preferences
- Do not add charts
- Do not add column sorting by clicking headers
- Do not add autocomplete
- Do not add extra filters beyond what is specified
- Keep the UI simple and functional, not flashy