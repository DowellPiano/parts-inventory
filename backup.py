"""Database backup via sqlite3 dump."""
import os
import sqlite3


def create_backup(database_url):
    """Dump the SQLite database and return the SQL bytes."""
    db_path = database_url.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'instance', db_path)

    lines = []
    with sqlite3.connect(db_path) as con:
        for line in con.iterdump():
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')
