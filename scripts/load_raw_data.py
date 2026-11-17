"""Creates the raw tables in the SQLite database"""

from pathlib import Path

from database_connection import get_database_connection

# Build paths from this file's location so the script works no matter which folder it's run from
project_root_folder = Path(__file__).resolve().parent.parent
raw_table_schema_file_path = project_root_folder / "sql" / "01_create_raw_tables.sql"


def create_raw_tables(database_connection):
    # Keep the table design in a .sql file rather than inside Python, so teammates can read the schema on its own
    database_connection.executescript(raw_table_schema_file_path.read_text())


def main():
    database_connection = get_database_connection()
    create_raw_tables(database_connection)
    # List the tables so you can see they were created
    table_names = database_connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    for (table_name,) in table_names:
        print("Created table:", table_name)
    database_connection.close()


if __name__ == "__main__":
    main()