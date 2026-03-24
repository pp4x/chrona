BEGIN;

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    category TEXT,
    project TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK (name <> ''),
    CHECK (normalized_name <> '')
);

CREATE UNIQUE INDEX tasks_normalized_name_idx
ON tasks(normalized_name);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL,
    begin_at TEXT NOT NULL,
    end_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX sessions_task_id_begin_at_idx
ON sessions(task_id, begin_at);

CREATE INDEX sessions_begin_at_idx
ON sessions(begin_at);

CREATE INDEX sessions_end_at_idx
ON sessions(end_at);

INSERT INTO schema_migrations(version, applied_at)
VALUES (1, CURRENT_TIMESTAMP);

COMMIT;
