"""Shared helper so every pipeline script opens the same database file the same way."""

import sqlite3
from pathlib import Path

# Build the path from this file's location so the scripts work no matter which folder they're run from
project_root_folder = Path(__file__).resolve().parent.parent
database_file_path = project_root_folder / "data" / "asthma_air_quality.db"


def get_database_connection():
    # SQLite creates the file the first time it's opened, so there is no server to start
    database_connection = sqlite3.connect(database_file_path)
    # SQLite skips foreign key checks unless they are switched on for each new connection
    database_connection.execute("PRAGMA foreign_keys = ON")
    return database_connection


if __name__ == "__main__":
    # Running this file directly is a quick test that the database file can be created and opened
    database_connection = get_database_connection()
    print("SQLite version:", database_connection.execute("SELECT sqlite_version()").fetchone()[0])
    print("Database file:", database_file_path)
    database_connection.close()