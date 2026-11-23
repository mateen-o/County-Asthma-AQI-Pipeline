"""Checking the finished database and stops with an error if any rule is broken, so bad data never reaches the dashboard or the analysis."""

import sys

from database_connection import get_database_connection

# Each check is a rule in plain language, then SQL that counts how many rows break it. Zero means the rule holds.
validation_checks = [
    # Nothing lost between raw and clean
    ("Every raw PLACES county row made it into places_county_measures",
     "SELECT ABS((SELECT COUNT(*) FROM raw_places_county WHERE length(county_fips) = 5) - (SELECT COUNT(*) FROM places_county_measures))"),
    ("Every county in the raw PLACES file is in the counties table",
     "SELECT ABS((SELECT COUNT(DISTINCT county_fips) FROM raw_places_county WHERE length(county_fips) = 5) - (SELECT COUNT(*) FROM counties))"),
    ("Every EPA yearly row found its FIPS code in the lookup",
     "SELECT COUNT(*) FROM raw_epa_annual_aqi_by_county AS annual LEFT JOIN epa_county_fips_lookup AS lookup ON lookup.state_name = annual.state_name AND lookup.county_name = annual.county_name WHERE lookup.county_fips IS NULL"),
    ("Every EPA yearly row for the 50 states and DC is in epa_annual_aqi_by_county",
     "SELECT ABS((SELECT COUNT(*) FROM raw_epa_annual_aqi_by_county AS annual JOIN epa_county_fips_lookup AS lookup ON lookup.state_name = annual.state_name AND lookup.county_name = annual.county_name WHERE CAST(substr(lookup.county_fips, 1, 2) AS INTEGER) BETWEEN 1 AND 56) - (SELECT COUNT(*) FROM epa_annual_aqi_by_county))"),
    ("The analysis table has exactly 2 rows per county (2022 and 2023)",
     "SELECT ABS((SELECT COUNT(*) FROM counties) * 2 - (SELECT COUNT(*) FROM county_asthma_air_quality WHERE air_quality_year IN (2022, 2023)))"),
    # Keys and formats
    ("Every county FIPS code is exactly 5 digits",
     "SELECT COUNT(*) FROM counties WHERE length(county_fips) <> 5 OR county_fips GLOB '*[^0-9]*'"),
    ("Every EPA county outside Connecticut matched a PLACES county",
     "SELECT COUNT(*) FROM epa_annual_aqi_by_county WHERE substr(county_fips, 1, 2) <> '09' AND county_fips NOT IN (SELECT county_fips FROM counties)"),
    # Values that have to make sense
    ("Asthma values are between 0 and 100 and sit inside their own confidence interval",
     "SELECT COUNT(*) FROM county_asthma_air_quality WHERE asthma_age_adjusted_percent IS NOT NULL AND (asthma_lower_confidence_limit IS NULL OR asthma_upper_confidence_limit IS NULL OR asthma_age_adjusted_percent NOT BETWEEN 0 AND 100 OR asthma_age_adjusted_percent < asthma_lower_confidence_limit OR asthma_age_adjusted_percent > asthma_upper_confidence_limit)"),
    ("Adult population is above zero and no bigger than total population",
     "SELECT COUNT(*) FROM counties WHERE adult_population IS NULL OR total_population IS NULL OR adult_population <= 0 OR adult_population > total_population"),
    ("EPA good, moderate and unhealthy day counts add up to the days with AQI",
     "SELECT COUNT(*) FROM epa_annual_aqi_by_county WHERE good_days + moderate_days + unhealthy_for_sensitive_groups_days + unhealthy_days + very_unhealthy_days + hazardous_days <> days_with_aqi"),
    ("Median AQI is no higher than the 90th percentile, which is no higher than the max",
     "SELECT COUNT(*) FROM epa_annual_aqi_by_county WHERE NOT (median_aqi <= percentile_90_aqi AND percentile_90_aqi <= max_aqi)"),
    ("The 75% flag is 1 exactly when a county has 274 or more days of AQI",
     "SELECT COUNT(*) FROM epa_annual_aqi_by_county WHERE has_75_percent_of_days <> (days_with_aqi >= 274)"),
    # Status columns tell the truth
    ("asthma_data_status says 'available' exactly when there is an asthma value, and air_quality_coverage says 'monitored' exactly when there is a median AQI",
     "SELECT COUNT(*) FROM county_asthma_air_quality WHERE (asthma_data_status = 'available') <> (asthma_age_adjusted_percent IS NOT NULL) OR (air_quality_coverage = 'monitored') <> (median_aqi IS NOT NULL)"),
    ("Only Kentucky and Pennsylvania are 'not published for this state' (a new state here means CDC changed something)",
     "SELECT COUNT(*) FROM county_asthma_air_quality WHERE asthma_data_status = 'not published for this state' AND state_abbreviation NOT IN ('KY', 'PA')"),
    ("Connecticut, and only Connecticut, is marked 'not comparable'",
     "SELECT COUNT(*) FROM county_asthma_air_quality WHERE (state_abbreviation = 'CT') <> (air_quality_coverage = 'not comparable (Connecticut boundary change)')"),
    ("Every EPA county outside Connecticut shows up as 'monitored' in the analysis table",
     "SELECT ABS((SELECT COUNT(*) FROM epa_annual_aqi_by_county WHERE substr(county_fips, 1, 2) <> '09') - (SELECT COUNT(*) FROM county_asthma_air_quality WHERE air_quality_coverage = 'monitored'))"),
         # SAIPE checks: the first two confirm cleaning lost or mangled nothing; the next two confirm every county matched in both directions
    ("Every SAIPE county row in the raw table made it into the clean SAIPE table", "SELECT ABS((SELECT COUNT(*) FROM raw_saipe_county WHERE CAST(county_fips_code AS INTEGER) <> 0) - (SELECT COUNT(*) FROM saipe_county_poverty_income))"),
    ("Every county code in the clean SAIPE table is exactly 5 digits", "SELECT COUNT(*) FROM saipe_county_poverty_income WHERE length(county_fips) <> 5 OR county_fips GLOB '*[^0-9]*'"),
     ("Every county except Kalawao, HI has SAIPE poverty and income", "SELECT COUNT(*) FROM county_asthma_air_quality WHERE (poverty_percent_all_ages IS NULL OR median_household_income IS NULL) AND county_fips <> '15005'"),
    ("Every SAIPE county is in the analysis table", "SELECT COUNT(*) FROM saipe_county_poverty_income WHERE county_fips NOT IN (SELECT county_fips FROM county_asthma_air_quality)"),
    # Range checks catch values that were read wrong, such as a percent landing in the income column
    ("Poverty percent is between 0 and 100", "SELECT COUNT(*) FROM saipe_county_poverty_income WHERE poverty_percent_all_ages < 0 OR poverty_percent_all_ages > 100"),
    ("Median household income is above zero", "SELECT COUNT(*) FROM saipe_county_poverty_income WHERE median_household_income <= 0"),
    # "90% CI Lower Bound" repeats ten times in the file, so this catches a bound matched to the wrong estimate
    ("Each SAIPE estimate sits inside its own 90% interval", "SELECT COUNT(*) FROM saipe_county_poverty_income WHERE poverty_percent_all_ages NOT BETWEEN poverty_percent_all_ages_lower_90 AND poverty_percent_all_ages_upper_90 OR median_household_income NOT BETWEEN median_household_income_lower_90 AND median_household_income_upper_90"),

]


def main():
    database_connection = get_database_connection()
    failed_check_count = 0
    for check_description, check_query in validation_checks:
        problem_count = database_connection.execute(check_query).fetchone()[0]
        if problem_count == 0:
            print(f"PASS  {check_description}")
        else:
            failed_check_count += 1
            print(f"FAIL  {check_description} ({problem_count:,} problem rows)")
    database_connection.close()
    print(f"\n{len(validation_checks) - failed_check_count} of {len(validation_checks)} checks passed")
    # Exit with an error code on any failure, so a pipeline that runs this script stops instead of carrying on with bad data
    if failed_check_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()