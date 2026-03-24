import sqlite3
from pathlib import Path


APP_DIR_NAME = "chrona"
DB_FILENAME = "chrona.sqlite3"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_app_data_dir() -> Path:
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def get_database_path() -> Path:
    return get_app_data_dir() / DB_FILENAME


def connect_database(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_schema(connection: sqlite3.Connection, migrations_dir: Path | None = None) -> None:
    migrations_path = migrations_dir or MIGRATIONS_DIR
    _ensure_migrations_table(connection)

    applied_versions = {
        row["version"]
        for row in connection.execute("SELECT version FROM schema_migrations")
    }

    for migration_path in sorted(migrations_path.glob("*.sql")):
        version = int(migration_path.stem.split("_", 1)[0])
        if version in applied_versions:
            continue
        connection.executescript(migration_path.read_text())
        connection.commit()


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
