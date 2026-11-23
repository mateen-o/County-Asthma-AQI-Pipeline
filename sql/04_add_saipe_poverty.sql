-- Adds Census SAIPE 2023 county poverty and income to the analysis table.
-- Runs after 03_create_analysis_table.sql, which rebuilds county_asthma_air_quality from scratch each time,
-- so the new columns are added to a fresh table on every run.
-- 2023 matches the asthma survey year (PLACES 2025 release uses 2023 BRFSS).

BEGIN;

DROP TABLE IF EXISTS saipe_county_poverty_income;

-- One row per county, numbers stored as numbers
CREATE TABLE saipe_county_poverty_income (
    county_fips                         TEXT PRIMARY KEY,
    saipe_year                          INTEGER NOT NULL,
    area_name                           TEXT NOT NULL,
    poverty_percent_all_ages            REAL,
    poverty_percent_all_ages_lower_90   REAL,
    poverty_percent_all_ages_upper_90   REAL,
    median_household_income             INTEGER,
    median_household_income_lower_90    INTEGER,
    median_household_income_upper_90    INTEGER
) STRICT;

INSERT INTO saipe_county_poverty_income (county_fips, saipe_year, area_name, poverty_percent_all_ages, poverty_percent_all_ages_lower_90, poverty_percent_all_ages_upper_90, median_household_income, median_household_income_lower_90, median_household_income_upper_90)

WITH saipe_county_rows_tidied AS (
    SELECT
        -- SAIPE splits the FIPS code into a 2-digit state part and a 3-digit county part; printf rebuilds the 5-digit code with leading zeros
        printf('%02d%03d', CAST(state_fips_code AS INTEGER), CAST(county_fips_code AS INTEGER)) AS county_fips,
        trim(area_name) AS area_name,
        replace(trim(poverty_percent_all_ages), ',', '') AS poverty_percent_all_ages,
        replace(trim(poverty_percent_all_ages_lower_90), ',', '') AS poverty_percent_all_ages_lower_90,
        replace(trim(poverty_percent_all_ages_upper_90), ',', '') AS poverty_percent_all_ages_upper_90,
        replace(trim(median_household_income), ',', '') AS median_household_income,
        replace(trim(median_household_income_lower_90), ',', '') AS median_household_income_lower_90,
        replace(trim(median_household_income_upper_90), ',', '') AS median_household_income_upper_90
    FROM raw_saipe_county
    -- County code 000 marks the US total and the state totals, which aren't counties
    WHERE CAST(county_fips_code AS INTEGER) <> 0
)
SELECT
    county_fips,
    2023,
    area_name,
    -- Only convert values that start with a digit; a placeholder like "." would otherwise turn into 0 instead of missing
    CASE WHEN poverty_percent_all_ages GLOB '[0-9]*' THEN CAST(poverty_percent_all_ages AS REAL) END,
    CASE WHEN poverty_percent_all_ages_lower_90 GLOB '[0-9]*' THEN CAST(poverty_percent_all_ages_lower_90 AS REAL) END,
    CASE WHEN poverty_percent_all_ages_upper_90 GLOB '[0-9]*' THEN CAST(poverty_percent_all_ages_upper_90 AS REAL) END,
    CASE WHEN median_household_income GLOB '[0-9]*' THEN CAST(median_household_income AS INTEGER) END,
    CASE WHEN median_household_income_lower_90 GLOB '[0-9]*' THEN CAST(median_household_income_lower_90 AS INTEGER) END,
    CASE WHEN median_household_income_upper_90 GLOB '[0-9]*' THEN CAST(median_household_income_upper_90 AS INTEGER) END
FROM saipe_county_rows_tidied;

-- New columns on the analysis table, so Ethan and Kathleen keep reading one table
ALTER TABLE county_asthma_air_quality ADD COLUMN poverty_percent_all_ages REAL;
ALTER TABLE county_asthma_air_quality ADD COLUMN median_household_income INTEGER;

-- Poverty doesn't change by air quality year, so both the 2022 and 2023 rows of a county get the same 2023 values
UPDATE county_asthma_air_quality
SET poverty_percent_all_ages = saipe.poverty_percent_all_ages,
    median_household_income = saipe.median_household_income
FROM saipe_county_poverty_income AS saipe
WHERE saipe.county_fips = county_asthma_air_quality.county_fips;

COMMIT;