"""Building the clean tables from the raw tables by running the cleaning SQL script and outputs then prints how many rows each table ended up with."""

from pathlib import Path

from database_connection import get_database_connection

# Build paths from this file's location so the script works no matter which folder it's run from
project_root_folder = Path(__file__).resolve().parent.parent

# SQL files run in this order, because later files build on tables made by earlier ones
sql_files_to_run = [project_root_folder / "sql" / "02_create_clean_tables.sql", project_root_folder / "sql" / "03_create_analysis_table.sql"]

# Tables to count afterwards, so a step that quietly produced too few rows is easy to spot
tables_to_count = ["counties", "places_county_measures", "epa_county_fips_lookup", "epa_annual_aqi_by_county", "county_asthma_air_quality"]

def main():
    database_connection = get_database_connection()
    for sql_file_path in sql_files_to_run:
        print(f"Running {sql_file_path.name}")
        # executescript runs every statement in the file; the file's own BEGIN and COMMIT make it all-or-nothing
        database_connection.executescript(sql_file_path.read_text())
    for table_name in tables_to_count:
        row_count = database_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {row_count:,} rows")
    database_connection.close()


if __name__ == "__main__":
    main()