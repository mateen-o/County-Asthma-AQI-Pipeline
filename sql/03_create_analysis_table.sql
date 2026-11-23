-- Analysis table: dashboard and the R analysis read from this table, not the raw PLACES and EPA tables. This table is one row per county per air quality year, with asthma and other county measures in columns.
-- Every PLACES county is included, even with no monitor or no asthma estimate, so missing data shows up as empty values instead of missing counties.
-- The asthma data is from the 2023 survey year, so the 2023 air quality year is the main analysis. The 2022 air quality year is a sensitivity check (no 2023 wildfire smoke).
-- The main asthma measure is age-adjusted (crude is included too), so the other county measures are also age-adjusted to match. "No health insurance" is also age-adjusted but only covers adults 18-64; it stands in for income, since poverty isn't in the PLACES county file.
-- The asthma data is sometimes suppressed by CDC (population under 50) or not published for a state (Kentucky and Pennsylvania in the 2025 PLACES release). The air quality data is sometimes not monitored or not comparable (Connecticut boundary change).
-- The "percent_days_unhealthy_for_sensitive_or_worse" is a percentage, not a count, so a county monitored 200 days can be compared fairly with one monitored 365 days.
-- The "days_ozone" and "days_pm25" are the number of days when ozone or fine particles (PM2.5) were the main pollutant, respectively.
-- The "has_75_percent_of_days" is 1 when the county has AQI data on at least 274 of 365 days (75%, EPA's usual completeness rule). It can be used in the regression analysis to leave out counties with too little data.
-- The "asthma_data_status" and "air_quality_coverage" columns explain why a value is empty. The dashboard uses them to label counties on the map, and the analysis uses them to choose which counties go in the sample.
-- The "county_fips" is the unique identifier for each county, and the "air_quality_year" is the year of the air quality data. The combination of these two columns forms the primary key for this table.
-- The "adult_population" column is the weight for the population-weighted regression, since asthma prevalence is for adults. "total_population" is kept for context on the dashboard.

BEGIN;

DROP TABLE IF EXISTS county_asthma_air_quality;

CREATE TABLE county_asthma_air_quality (
    county_fips                                    TEXT NOT NULL,
    air_quality_year                               INTEGER NOT NULL,
    state_abbreviation                             TEXT NOT NULL,
    state_name                                     TEXT NOT NULL,
    county_name                                    TEXT NOT NULL,
    total_population                               INTEGER,
    adult_population                               INTEGER,
    -- Asthma (2023 survey year) and why it might be empty
    asthma_data_status                             TEXT NOT NULL CHECK (asthma_data_status IN ('available', 'suppressed by CDC (population under 50)', 'not published for this state')),
    asthma_age_adjusted_percent                    REAL,
    asthma_lower_confidence_limit                  REAL,
    asthma_upper_confidence_limit                  REAL,
    asthma_crude_percent                           REAL,
    -- Other county measures for the regression (all age-adjusted, to match asthma)
    smoking_age_adjusted_percent                   REAL,
    obesity_age_adjusted_percent                   REAL,
    no_health_insurance_age_adjusted_percent       REAL,  -- Kept as a measure of access to care; poverty and income now come from Census SAIPE (added in 04_add_saipe_poverty.sql)
    physical_inactivity_age_adjusted_percent       REAL,
    -- Air quality for this county and year, and why it might be empty
    air_quality_coverage                           TEXT NOT NULL CHECK (air_quality_coverage IN ('monitored', 'not monitored', 'not comparable (Connecticut boundary change)')),
    days_with_aqi                                  INTEGER,
    has_75_percent_of_days                         INTEGER CHECK (has_75_percent_of_days IN (0, 1)),
    median_aqi                                     INTEGER,
    percentile_90_aqi                              INTEGER,
    max_aqi                                        INTEGER,
    good_days                                      INTEGER,
    moderate_days                                  INTEGER,
    unhealthy_for_sensitive_groups_days            INTEGER,
    unhealthy_days                                 INTEGER,
    very_unhealthy_days                            INTEGER,
    hazardous_days                                 INTEGER,
    -- Share of monitored days at "unhealthy for sensitive groups" or worse. A percentage, not a count, so a county
    -- monitored 200 days can be compared fairly with one monitored 365 days
    percent_days_unhealthy_for_sensitive_or_worse  REAL,
    days_ozone                                     INTEGER,  -- days when ozone was the main pollutant
    days_pm25                                      INTEGER,  -- days when fine particles (PM2.5) were the main pollutant
    PRIMARY KEY (county_fips, air_quality_year)
) STRICT;

INSERT INTO county_asthma_air_quality (county_fips, air_quality_year, state_abbreviation, state_name, county_name, total_population, adult_population, asthma_data_status, asthma_age_adjusted_percent, asthma_lower_confidence_limit, asthma_upper_confidence_limit, asthma_crude_percent, smoking_age_adjusted_percent, obesity_age_adjusted_percent, no_health_insurance_age_adjusted_percent, physical_inactivity_age_adjusted_percent, air_quality_coverage, days_with_aqi, has_75_percent_of_days, median_aqi, percentile_90_aqi, max_aqi, good_days, moderate_days, unhealthy_for_sensitive_groups_days, unhealthy_days, very_unhealthy_days, hazardous_days, percent_days_unhealthy_for_sensitive_or_worse, days_ozone, days_pm25)
WITH
    -- The two air quality years: 2023 matches the asthma survey year; 2022 is the sensitivity check (no 2023 wildfire smoke)
    air_quality_years (air_quality_year) AS (VALUES (2022), (2023)),
    -- Turn the long measures table into one row per county with one column per measure we need
    county_measures_side_by_side AS (
        SELECT
            county_fips,
            MAX(CASE WHEN measure_id = 'CASTHMA' AND estimate_type = 'age_adjusted' THEN prevalence_percent END) AS asthma_age_adjusted_percent,
            MAX(CASE WHEN measure_id = 'CASTHMA' AND estimate_type = 'age_adjusted' THEN lower_confidence_limit END) AS asthma_lower_confidence_limit,
            MAX(CASE WHEN measure_id = 'CASTHMA' AND estimate_type = 'age_adjusted' THEN upper_confidence_limit END) AS asthma_upper_confidence_limit,
            MAX(CASE WHEN measure_id = 'CASTHMA' AND estimate_type = 'crude' THEN prevalence_percent END) AS asthma_crude_percent,
            -- Tells "CDC suppressed it" (asthma row exists but is empty) apart from "CDC didn't publish it" (no asthma row at all)
            SUM(measure_id = 'CASTHMA') > 0 AS has_asthma_row,
            MAX(CASE WHEN measure_id = 'CSMOKING' AND estimate_type = 'age_adjusted' THEN prevalence_percent END) AS smoking_age_adjusted_percent,
            MAX(CASE WHEN measure_id = 'OBESITY' AND estimate_type = 'age_adjusted' THEN prevalence_percent END) AS obesity_age_adjusted_percent,
            MAX(CASE WHEN measure_id = 'ACCESS2' AND estimate_type = 'age_adjusted' THEN prevalence_percent END) AS no_health_insurance_age_adjusted_percent,
            MAX(CASE WHEN measure_id = 'LPA' AND estimate_type = 'age_adjusted' THEN prevalence_percent END) AS physical_inactivity_age_adjusted_percent
        FROM places_county_measures
        GROUP BY county_fips
    )
SELECT
    counties.county_fips,
    air_quality_years.air_quality_year,
    counties.state_abbreviation,
    counties.state_name,
    counties.county_name,
    counties.total_population,
    counties.adult_population,
    CASE
        WHEN measures.asthma_age_adjusted_percent IS NOT NULL THEN 'available'
        WHEN measures.has_asthma_row = 1 THEN 'suppressed by CDC (population under 50)'
        ELSE 'not published for this state'  -- Kentucky and Pennsylvania in the 2025 PLACES release
    END,
    measures.asthma_age_adjusted_percent,
    measures.asthma_lower_confidence_limit,
    measures.asthma_upper_confidence_limit,
    measures.asthma_crude_percent,
    measures.smoking_age_adjusted_percent,
    measures.obesity_age_adjusted_percent,
    measures.no_health_insurance_age_adjusted_percent,
    measures.physical_inactivity_age_adjusted_percent,
    CASE
        -- Checked first: PLACES uses Connecticut's planning regions and EPA uses the old counties, so an empty match here
        -- means "can't be lined up", not "no monitor"
        WHEN counties.state_abbreviation = 'CT' THEN 'not comparable (Connecticut boundary change)'
        WHEN air_quality.county_fips IS NOT NULL THEN 'monitored'
        ELSE 'not monitored'
    END,
    air_quality.days_with_aqi,
    air_quality.has_75_percent_of_days,
    air_quality.median_aqi,
    air_quality.percentile_90_aqi,
    air_quality.max_aqi,
    air_quality.good_days,
    air_quality.moderate_days,
    air_quality.unhealthy_for_sensitive_groups_days,
    air_quality.unhealthy_days,
    air_quality.very_unhealthy_days,
    air_quality.hazardous_days,
    -- 100.0 (not 100) forces decimal division; whole-number division would round most counties down to 0
    100.0 * (air_quality.unhealthy_for_sensitive_groups_days + air_quality.unhealthy_days + air_quality.very_unhealthy_days + air_quality.hazardous_days) / air_quality.days_with_aqi,
    air_quality.days_ozone,
    air_quality.days_pm25
FROM counties
-- Every county gets one row per air quality year, whether or not it has a monitor
CROSS JOIN air_quality_years
LEFT JOIN county_measures_side_by_side AS measures ON measures.county_fips = counties.county_fips
LEFT JOIN epa_annual_aqi_by_county AS air_quality ON air_quality.county_fips = counties.county_fips AND air_quality.air_quality_year = air_quality_years.air_quality_year;

COMMIT;