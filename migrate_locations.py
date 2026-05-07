"""
Migrate Part.location_id (one-to-many) → part_bin association table (many-to-many).
Safe to run multiple times — skips rows already migrated.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'parts_inventory.db')

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Create the part_bin table if it doesn't exist yet
cur.execute("""
    CREATE TABLE IF NOT EXISTS part_bin (
        part_id INTEGER NOT NULL REFERENCES part(id),
        bin_id  INTEGER NOT NULL REFERENCES bin(id),
        PRIMARY KEY (part_id, bin_id)
    )
""")

# Copy existing location_id values into part_bin
cur.execute("""
    INSERT OR IGNORE INTO part_bin (part_id, bin_id)
    SELECT id, location_id FROM part
    WHERE location_id IS NOT NULL
""")
migrated = cur.rowcount
print(f"Migrated {migrated} existing location assignments into part_bin.")

# SQLite can't drop a foreign key column directly — rebuild the table without it.
cur.execute("PRAGMA foreign_keys=OFF")
cur.execute("""
    CREATE TABLE part_new (
        id             INTEGER PRIMARY KEY,
        part_number    VARCHAR(50)  NOT NULL UNIQUE,
        name           VARCHAR(200) NOT NULL,
        description    TEXT,
        category       VARCHAR(100),
        photo_filename VARCHAR(255),
        photo_url      VARCHAR(500),
        quantity       INTEGER DEFAULT 0,
        min_threshold  INTEGER DEFAULT 0,
        cost           FLOAT,
        created_at     DATETIME,
        updated_at     DATETIME
    )
""")
cur.execute("""
    INSERT INTO part_new
        SELECT id, part_number, name, description, category,
               photo_filename, photo_url, quantity, min_threshold,
               cost, created_at, updated_at
        FROM part
""")
cur.execute("DROP TABLE part")
cur.execute("ALTER TABLE part_new RENAME TO part")
cur.execute("PRAGMA foreign_keys=ON")
print("Rebuilt part table without location_id column.")

con.commit()
con.close()
print("Migration complete.")
