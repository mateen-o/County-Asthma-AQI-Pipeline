"""This script creates the raw tables in the SQLite database and fills them with data from the CSV files in the raw_data folder."""

from pathlib import Path
import pandas as pd

from database_connection import get_database_connection

# Build paths from this file's location so the script works no matter which folder it's run from
project_root_folder = Path(__file__).resolve().parent.parent
raw_table_schema_file_path = project_root_folder / "sql" / "01_create_raw_tables.sql"
raw_data_folder = project_root_folder / "data" / "raw"

# File column name -> database column name. Spaces and capitals are swapped for snake_case so SQL doesn't need quotes
places_column_names = {"Year": "year", "StateAbbr": "state_abbreviation", "StateDesc": "state_name", "LocationName": "county_name", "DataSource": "data_source", "Category": "category", "Measure": "measure", "Data_Value_Unit": "data_value_unit", "Data_Value_Type": "data_value_type", "Data_Value": "data_value", "Data_Value_Footnote_Symbol": "data_value_footnote_symbol", "Data_Value_Footnote": "data_value_footnote", "Low_Confidence_Limit": "low_confidence_limit", "High_Confidence_Limit": "high_confidence_limit", "TotalPopulation": "total_population", "TotalPop18plus": "total_population_18_plus", "LocationID": "county_fips", "CategoryID": "category_id", "MeasureId": "measure_id", "DataValueTypeID": "data_value_type_id", "Short_Question_Text": "short_question_text", "Geolocation": "geolocation"}
annual_aqi_column_names = {"State": "state_name", "County": "county_name", "Year": "year", "Days with AQI": "days_with_aqi", "Good Days": "good_days", "Moderate Days": "moderate_days", "Unhealthy for Sensitive Groups Days": "unhealthy_for_sensitive_groups_days", "Unhealthy Days": "unhealthy_days", "Very Unhealthy Days": "very_unhealthy_days", "Hazardous Days": "hazardous_days", "Max AQI": "max_aqi", "90th Percentile AQI": "percentile_90_aqi", "Median AQI": "median_aqi", "Days CO": "days_co", "Days NO2": "days_no2", "Days Ozone": "days_ozone", "Days PM2.5": "days_pm25", "Days PM10": "days_pm10"}
daily_aqi_column_names = {"State Name": "state_name", "county Name": "county_name", "State Code": "state_code", "County Code": "county_code", "Date": "date", "AQI": "aqi", "Category": "category", "Defining Parameter": "defining_parameter", "Defining Site": "defining_site", "Number of Sites Reporting": "number_of_sites_reporting"}

# Which files go into which table, and which column-name list to use for them
files_to_load = [
    ("places_county_2025_release.csv", "raw_places_county", places_column_names),
    ("annual_aqi_by_county_2023.zip", "raw_epa_annual_aqi_by_county", annual_aqi_column_names),
    ("annual_aqi_by_county_2022.zip", "raw_epa_annual_aqi_by_county", annual_aqi_column_names),
    ("daily_aqi_by_county_2023.zip", "raw_epa_daily_aqi_by_county", daily_aqi_column_names),
    ("daily_aqi_by_county_2022.zip", "raw_epa_daily_aqi_by_county", daily_aqi_column_names),
]


def create_raw_tables(database_connection):
    # Keep the table design in a .sql file rather than inside Python, so teammates can read the schema on its own
    database_connection.executescript(raw_table_schema_file_path.read_text())


def load_one_file(database_connection, raw_file_name, raw_table_name, column_name_mapping):
    # dtype=str reads every value as text, so FIPS codes like 01001 keep their leading zero and nothing gets guessed or rounded
    # keep_default_na=False with na_values=[""] means only truly empty cells become missing; text like "NA" is kept exactly as written, for the cleaning step to decide on
    raw_file_table = pd.read_csv(raw_data_folder / raw_file_name, dtype=str, keep_default_na=False, na_values=[""])
    # Stop if the agency changed its columns, because loading would otherwise put values under the wrong names
    if list(raw_file_table.columns) != list(column_name_mapping.keys()):
        raise ValueError(f"{raw_file_name} columns don't match what this script expects: {list(raw_file_table.columns)}")
    raw_file_table = raw_file_table.rename(columns=column_name_mapping)
    raw_file_table["source_file_name"] = raw_file_name
    # Append into the table the schema already created, so the database keeps our column types instead of pandas inventing its own
    raw_file_table.to_sql(raw_table_name, database_connection, if_exists="append", index=False, chunksize=10_000)
    return len(raw_file_table)

def main():
    database_connection = get_database_connection()
    create_raw_tables(database_connection)
    for raw_file_name, raw_table_name, column_name_mapping in files_to_load:
        rows_in_file = load_one_file(database_connection, raw_file_name, raw_table_name, column_name_mapping)
        # Counts what actually landed in the database for this file, to confirm nothing was dropped on the way in
        rows_in_database = database_connection.execute(f"SELECT COUNT(*) FROM {raw_table_name} WHERE source_file_name = ?", (raw_file_name,)).fetchone()[0]
        print(f"{raw_file_name}: {rows_in_file:,} rows in file, {rows_in_database:,} rows in {raw_table_name}")
    database_connection.commit()
    database_connection.close()


if __name__ == "__main__":
    main()