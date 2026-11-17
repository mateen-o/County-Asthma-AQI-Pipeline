-- Clean tables: built only from the raw tables, with real numbers instead of text, 5-digit FIPS codes as the key,
-- and every cleaning decision written out below. Re-running this file rebuilds the clean tables from scratch.

BEGIN;

-- Drop the table that points at counties before counties itself, because SQLite won't drop a table other rows still depend on
DROP TABLE IF EXISTS places_county_measures;
DROP TABLE IF EXISTS counties;
DROP TABLE IF EXISTS epa_annual_aqi_by_county;
DROP TABLE IF EXISTS epa_county_fips_lookup;


-- counties: one row per U.S. county (or county equivalent) in PLACES. This is the master list every other table joins to.
CREATE TABLE counties (
    county_fips         TEXT PRIMARY KEY CHECK (length(county_fips) = 5),
    state_abbreviation  TEXT NOT NULL,
    state_name          TEXT NOT NULL,
    county_name         TEXT NOT NULL,
    total_population    INTEGER,
    adult_population    INTEGER  -- ages 18 and older; the right weight for adult asthma prevalence
) STRICT;

INSERT INTO counties (county_fips, state_abbreviation, state_name, county_name, total_population, adult_population)
SELECT
    county_fips,
    MAX(state_abbreviation),
    MAX(state_name),
    MAX(county_name),
    -- Take population from the asthma rows when they exist, since those match the 2023 survey year;
    -- Kentucky and Pennsylvania have no asthma rows, so fall back to their other rows.
    -- REPLACE removes any thousands commas, because SQLite would otherwise read "59,285" as 59.

    COALESCE(MAX(CASE WHEN measure_id = 'CASTHMA' THEN CAST(REPLACE(total_population, ',', '') AS INTEGER) END), MAX(CAST(REPLACE(total_population, ',', '') AS INTEGER))),
    COALESCE(MAX(CASE WHEN measure_id = 'CASTHMA' THEN CAST(REPLACE(total_population_18_plus, ',', '') AS INTEGER) END), MAX(CAST(REPLACE(total_population_18_plus, ',', '') AS INTEGER)))
FROM raw_places_county
-- The one 2-digit location code is the national estimate, not a county
WHERE length(county_fips) = 5
GROUP BY county_fips;


-- places_county_measures: every PLACES measure for every county, one row per county + measure + estimate type.
-- All 40 measures are kept here so teammates can pull any of them later without re-running the load.

CREATE TABLE places_county_measures (
    county_fips             TEXT NOT NULL REFERENCES counties (county_fips),
    measure_id              TEXT NOT NULL,
    measure_short_name      TEXT NOT NULL,
    measure_full_name       TEXT NOT NULL,
    category_id             TEXT NOT NULL,
    estimate_type           TEXT NOT NULL CHECK (estimate_type IN ('age_adjusted', 'crude')),
    survey_year             INTEGER NOT NULL,
    prevalence_percent      REAL CHECK (prevalence_percent BETWEEN 0 AND 100),  
    lower_confidence_limit  REAL,
    upper_confidence_limit  REAL,
    PRIMARY KEY (county_fips, measure_id, estimate_type)
) STRICT;

INSERT INTO places_county_measures
SELECT
    county_fips,
    measure_id,
    short_question_text,
    measure,
    category_id,
    -- Plain names instead of CDC's codes; any code other than these two becomes empty and the NOT NULL rule stops the build
    CASE data_value_type_id WHEN 'AgeAdjPrv' THEN 'age_adjusted' WHEN 'CrdPrv' THEN 'crude' END,
    CAST(year AS INTEGER),
    CAST(data_value AS REAL),
    CAST(low_confidence_limit AS REAL),
    CAST(high_confidence_limit AS REAL)
FROM raw_places_county
WHERE length(county_fips) = 5;


-- epa_county_fips_lookup: EPA county name -> FIPS code, taken from the daily files (the only EPA files with codes).
-- The primary key makes the build stop if one name ever maps to two codes, instead of silently picking one.

CREATE TABLE epa_county_fips_lookup (
    state_name   TEXT NOT NULL,
    county_name  TEXT NOT NULL,
    county_fips  TEXT NOT NULL CHECK (length(county_fips) = 5),
    PRIMARY KEY (state_name, county_name)
) STRICT;

INSERT INTO epa_county_fips_lookup (state_name, county_name, county_fips)
-- Pad the codes to 2 and 3 digits; they already are in the 2022 and 2023 files, but this protects against a file that drops a leading zero
SELECT DISTINCT state_name, county_name, substr('00' || state_code, -2) || substr('000' || county_code, -3)
FROM raw_epa_daily_aqi_by_county;


-- epa_annual_aqi_by_county: EPA's yearly AQI summary per county, now keyed by FIPS.
-- No foreign key to counties on purpose: Connecticut's 8 old EPA counties have no match in PLACES (which uses the
-- 9 new planning regions), and they are kept here because they are real EPA data.

CREATE TABLE epa_annual_aqi_by_county (
    county_fips                          TEXT NOT NULL CHECK (length(county_fips) = 5),
    air_quality_year                     INTEGER NOT NULL,
    epa_state_name                       TEXT NOT NULL,
    epa_county_name                      TEXT NOT NULL,
    days_with_aqi                        INTEGER NOT NULL CHECK (days_with_aqi BETWEEN 1 AND 366),
    -- 1 when the county has AQI on at least 274 days, which is 75% of a 365-day year (EPA's usual completeness rule).
    -- Counties below this are kept but flagged, because a summer-only ozone monitor makes a county look worse than a full year would
    has_75_percent_of_days               INTEGER NOT NULL CHECK (has_75_percent_of_days IN (0, 1)),
    good_days                            INTEGER,
    moderate_days                        INTEGER,
    unhealthy_for_sensitive_groups_days  INTEGER,
    unhealthy_days                       INTEGER,
    very_unhealthy_days                  INTEGER,
    hazardous_days                       INTEGER,
    max_aqi                              INTEGER,
    percentile_90_aqi                    INTEGER,
    median_aqi                           INTEGER,
    days_co                              INTEGER,
    days_no2                             INTEGER,
    days_ozone                           INTEGER,
    days_pm25                            INTEGER,
    days_pm10                            INTEGER,
    PRIMARY KEY (county_fips, air_quality_year)
) STRICT;

INSERT INTO epa_annual_aqi_by_county
SELECT
    lookup.county_fips,
    CAST(annual.year AS INTEGER),
    annual.state_name,
    annual.county_name,
    CAST(annual.days_with_aqi AS INTEGER),
    CAST(annual.days_with_aqi AS INTEGER) >= 274,
    CAST(annual.good_days AS INTEGER),
    CAST(annual.moderate_days AS INTEGER),
    CAST(annual.unhealthy_for_sensitive_groups_days AS INTEGER),
    CAST(annual.unhealthy_days AS INTEGER),
    CAST(annual.very_unhealthy_days AS INTEGER),
    CAST(annual.hazardous_days AS INTEGER),
    CAST(annual.max_aqi AS INTEGER),
    CAST(annual.percentile_90_aqi AS INTEGER),
    CAST(annual.median_aqi AS INTEGER),
    CAST(annual.days_co AS INTEGER),
    CAST(annual.days_no2 AS INTEGER),
    CAST(annual.days_ozone AS INTEGER),
    CAST(annual.days_pm25 AS INTEGER),
    CAST(annual.days_pm10 AS INTEGER)
FROM raw_epa_annual_aqi_by_county AS annual
JOIN epa_county_fips_lookup AS lookup ON lookup.state_name = annual.state_name AND lookup.county_name = annual.county_name
-- Keep the 50 states and DC (state codes 01-56); this drops Puerto Rico (72), the Virgin Islands (78) and Mexico (80), which PLACES doesn't cover
WHERE CAST(substr(lookup.county_fips, 1, 2) AS INTEGER) BETWEEN 1 AND 56;

COMMIT;