-- Raw tables: one row per row of each downloaded file, with every value stored as text exactly as the file has it.
-- STRICT makes SQLite refuse any value that isn't text, instead of quietly storing whatever it's given.

-- Drop and recreate so re-running the pipeline always starts from empty tables, never from leftovers of an earlier run
DROP TABLE IF EXISTS raw_places_county;
DROP TABLE IF EXISTS raw_epa_annual_aqi_by_county;
DROP TABLE IF EXISTS raw_epa_daily_aqi_by_county;

-- CDC PLACES county file: one row per county, per measure (asthma, smoking, ...), per estimate type (crude or age-adjusted)
CREATE TABLE raw_places_county (
    year                        TEXT,
    state_abbreviation          TEXT,
    state_name                  TEXT,
    county_name                 TEXT,
    data_source                 TEXT,
    category                    TEXT,
    measure                     TEXT,
    data_value_unit             TEXT,
    data_value_type             TEXT,
    data_value                  TEXT,
    data_value_footnote_symbol  TEXT,
    data_value_footnote         TEXT,
    low_confidence_limit        TEXT,
    high_confidence_limit       TEXT,
    total_population            TEXT,
    total_population_18_plus    TEXT,
    county_fips                 TEXT,  -- called LocationID in the file
    category_id                 TEXT,
    measure_id                  TEXT,
    data_value_type_id          TEXT,
    short_question_text         TEXT,
    geolocation                 TEXT,
    source_file_name            TEXT   -- which downloaded file the row came from, so row counts can be checked file by file
) STRICT;

-- EPA yearly AQI summary: one row per county per year, counties named but no FIPS codes
CREATE TABLE raw_epa_annual_aqi_by_county (
    state_name                           TEXT,
    county_name                          TEXT,
    year                                 TEXT,
    days_with_aqi                        TEXT,
    good_days                            TEXT,
    moderate_days                        TEXT,
    unhealthy_for_sensitive_groups_days  TEXT,
    unhealthy_days                       TEXT,
    very_unhealthy_days                  TEXT,
    hazardous_days                       TEXT,
    max_aqi                              TEXT,
    percentile_90_aqi                    TEXT,
    median_aqi                           TEXT,
    days_co                              TEXT,
    days_no2                             TEXT,
    days_ozone                           TEXT,
    days_pm25                            TEXT,
    days_pm10                            TEXT,
    source_file_name                     TEXT
) STRICT;

-- EPA daily AQI: one row per county per day; the only EPA file here that carries state and county FIPS codes
CREATE TABLE raw_epa_daily_aqi_by_county (
    state_name                 TEXT,
    county_name                TEXT,
    state_code                 TEXT,
    county_code                TEXT,
    date                       TEXT,
    aqi                        TEXT,
    category                   TEXT,
    defining_parameter         TEXT,
    defining_site              TEXT,
    number_of_sites_reporting  TEXT,
    source_file_name           TEXT
) STRICT;