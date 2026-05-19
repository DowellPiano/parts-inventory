"""Database backup via sqlite3 dump."""
import os
import sqlite3
import tempfile


def database_path(database_url):
    """Return the filesystem path for the configured SQLite database."""
    db_path = database_url.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'instance', db_path)
    return db_path


def create_backup(database_url):
    """Dump the SQLite database and return the SQL bytes."""
    db_path = database_path(database_url)

    lines = []
    with sqlite3.connect(db_path) as con:
        for line in con.iterdump():
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')


def restore_backup(database_url, sql_bytes):
    """Validate a SQL backup and replace the configured SQLite database."""
    db_path = database_path(database_url)
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    sql_text = sql_bytes.decode('utf-8')
    temp_file = tempfile.NamedTemporaryFile(
        prefix='restore_',
        suffix='.db',
        dir=db_dir,
        delete=False,
    )
    temp_path = temp_file.name
    temp_file.close()

    try:
        with sqlite3.connect(temp_path) as con:
            con.executescript(sql_text)
            tables = {
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            required_tables = {'part', 'bin'}
            missing_tables = required_tables - tables
            if missing_tables:
                missing = ', '.join(sorted(missing_tables))
                raise ValueError(f"Backup is missing required table(s): {missing}")

        os.replace(temp_path, db_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
