"""We are printing a set of checks on the raw tables, so cleaning decisions are based on what's actually in the data."""

import sys

import pandas

from database_connection import get_database_connection

# Write the output as UTF-8 so county names with accents (like Dona Ana with a tilde) don't crash the script when saved to a file on Windows
sys.stdout.reconfigure(encoding="utf-8")
# Show every row and column instead of pandas hiding the middle with "..."
pandas.set_option("display.max_rows", 200)
pandas.set_option("display.width", 250)
pandas.set_option("display.max_columns", 20)

# Explain-language question check, then the SQL that answers it
profile_checks = [
    ("PLACES: which measures are in the file (one row per measure)",
     "SELECT category_id, measure_id, short_question_text, COUNT(*) AS row_count FROM raw_places_county GROUP BY category_id, measure_id, short_question_text ORDER BY category_id, measure_id"),
    ("PLACES: asthma, smoking and obesity by estimate type and year, with missing values and the value range",
     "SELECT measure_id, data_value_type_id, year, COUNT(*) AS row_count, SUM(data_value IS NULL) AS missing_values, SUM(total_population IS NULL) AS missing_population, MIN(CAST(data_value AS REAL)) AS lowest_value, MAX(CAST(data_value AS REAL)) AS highest_value FROM raw_places_county WHERE measure_id IN ('CASTHMA', 'CSMOKING', 'OBESITY') GROUP BY measure_id, data_value_type_id, year ORDER BY measure_id, data_value_type_id, year"),
    ("PLACES: values that are filled in but don't look like a number",
     "SELECT data_value, COUNT(*) AS row_count FROM raw_places_county WHERE data_value IS NOT NULL AND data_value GLOB '*[^0-9.]*' GROUP BY data_value"),
    ("PLACES: FIPS code length and whether any contain non-digits",
     "SELECT length(county_fips) AS fips_length, county_fips GLOB '*[^0-9]*' AS has_non_digit, COUNT(DISTINCT county_fips) AS distinct_counties FROM raw_places_county GROUP BY fips_length, has_non_digit"),
    ("PLACES: states where some counties have no age-adjusted asthma value",
     "SELECT state_abbreviation, COUNT(DISTINCT county_fips) AS counties_in_file, COUNT(DISTINCT CASE WHEN measure_id = 'CASTHMA' AND data_value_type_id = 'AgeAdjPrv' AND data_value IS NOT NULL THEN county_fips END) AS counties_with_asthma FROM raw_places_county GROUP BY state_abbreviation HAVING counties_with_asthma < counties_in_file ORDER BY state_abbreviation"),
    ("PLACES: footnotes used",
     "SELECT data_value_footnote_symbol, data_value_footnote, COUNT(*) AS row_count FROM raw_places_county GROUP BY data_value_footnote_symbol, data_value_footnote"),
    ("PLACES: Connecticut county codes",
     "SELECT DISTINCT county_fips, county_name FROM raw_places_county WHERE state_abbreviation = 'CT' ORDER BY county_fips"),
    ("EPA annual: how many days each county has AQI data for",
     "SELECT year, COUNT(*) AS counties, MIN(CAST(days_with_aqi AS INTEGER)) AS fewest_days, MAX(CAST(days_with_aqi AS INTEGER)) AS most_days, SUM(CAST(days_with_aqi AS INTEGER) < 90) AS under_90_days, SUM(CAST(days_with_aqi AS INTEGER) BETWEEN 90 AND 179) AS days_90_to_179, SUM(CAST(days_with_aqi AS INTEGER) BETWEEN 180 AND 299) AS days_180_to_299, SUM(CAST(days_with_aqi AS INTEGER) >= 300) AS days_300_plus FROM raw_epa_annual_aqi_by_county GROUP BY year"),
    ("EPA annual: median AQI values that are missing or not whole numbers",
     "SELECT year, median_aqi, COUNT(*) AS row_count FROM raw_epa_annual_aqi_by_county WHERE median_aqi IS NULL OR median_aqi GLOB '*[^0-9]*' GROUP BY year, median_aqi"),
    ("EPA annual: state names that don't appear in PLACES (spelling differences or places that aren't states)",
     "SELECT DISTINCT state_name FROM raw_epa_annual_aqi_by_county WHERE state_name NOT IN (SELECT DISTINCT state_name FROM raw_places_county) ORDER BY state_name"),
    ("EPA daily: date range and number of days in each file",
     "SELECT source_file_name, MIN(date) AS first_date, MAX(date) AS last_date, COUNT(DISTINCT date) AS distinct_dates FROM raw_epa_daily_aqi_by_county GROUP BY source_file_name"),
    ("EPA daily: length of the state and county codes",
     "SELECT length(state_code) AS state_code_length, length(county_code) AS county_code_length, COUNT(*) AS row_count FROM raw_epa_daily_aqi_by_county GROUP BY state_code_length, county_code_length"),
    ("EPA daily: AQI values that are missing or not whole numbers",
     "SELECT aqi, COUNT(*) AS row_count FROM raw_epa_daily_aqi_by_county WHERE aqi IS NULL OR aqi GLOB '*[^0-9]*' GROUP BY aqi"),
    ("EPA daily: county names that map to more than one FIPS code (would make the name-to-FIPS match ambiguous)",
     "SELECT source_file_name, state_name, county_name, COUNT(DISTINCT state_code || '-' || county_code) AS distinct_codes FROM raw_epa_daily_aqi_by_county GROUP BY source_file_name, state_name, county_name HAVING distinct_codes > 1"),
    ("EPA: annual rows whose state and county name can't be found in the daily file for the same year",
     "SELECT annual.year, COUNT(*) AS annual_rows, SUM(daily_names.county_name IS NULL) AS annual_rows_without_match FROM raw_epa_annual_aqi_by_county AS annual LEFT JOIN (SELECT DISTINCT substr(date, 1, 4) AS year, state_name, county_name FROM raw_epa_daily_aqi_by_county) AS daily_names ON daily_names.year = annual.year AND daily_names.state_name = annual.state_name AND daily_names.county_name = annual.county_name GROUP BY annual.year"),
    ("EPA daily: Connecticut county codes",
     "SELECT DISTINCT state_code, county_code, county_name FROM raw_epa_daily_aqi_by_county WHERE state_name = 'Connecticut' ORDER BY state_code, county_code"),
    ("EPA daily counties whose FIPS code is not in PLACES (first 40)",
     "SELECT DISTINCT daily.state_name, daily.county_name, substr('00' || daily.state_code, -2) || substr('000' || daily.county_code, -3) AS county_fips FROM raw_epa_daily_aqi_by_county AS daily WHERE substr('00' || daily.state_code, -2) || substr('000' || daily.county_code, -3) NOT IN (SELECT DISTINCT county_fips FROM raw_places_county) ORDER BY daily.state_name, daily.county_name LIMIT 40"),
]


def main():
    database_connection = get_database_connection()
    for check_number, (check_question, check_query) in enumerate(profile_checks, start=1):
        print(f"\n=== Check {check_number}: {check_question} ===")
        check_result = pandas.read_sql(check_query, database_connection)
        print("(no rows)" if check_result.empty else check_result.to_string(index=False))
    database_connection.close()


if __name__ == "__main__":
    main()