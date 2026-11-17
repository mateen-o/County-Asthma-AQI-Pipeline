# Asthma and Air Quality: Data Pipeline

This pipeline downloads county asthma estimates (CDC PLACES) and county air quality summaries (EPA AirData), loads them into a SQLite database, cleans them, links them by county FIPS code, and checks the result. The dashboard and the R analysis both read from the finished database.

## Setup (once)

```
conda env create -f environment.yml
conda activate asthma-air-quality
```

## Run the pipeline

```
python run_pipeline.py
```

This downloads the raw files into `data/raw/`, builds `data/asthma_air_quality.db`, and runs 16 validation checks. It stops at the first problem. The raw files and the database are not in git; anyone can rebuild them with this one command.

## What's in the database

| Table | What it holds |
|---|---|
| `raw_places_county`, `raw_epa_annual_aqi_by_county`, `raw_epa_daily_aqi_by_county` | The downloaded files, every value stored as text exactly as published |
| `counties` | One row per county (3,144), with total and adult population |
| `places_county_measures` | All 40 PLACES measures for every county, as numbers |
| `epa_county_fips_lookup` | EPA county names matched to FIPS codes |
| `epa_annual_aqi_by_county` | EPA yearly AQI summaries by FIPS code, 2022 and 2023 |
| **`county_asthma_air_quality`** | **The table to use**: one row per county per air quality year, with asthma, other county measures, air quality, and status columns |

## Reading the database

Python (dashboard):

```python
import sqlite3
import pandas
database_connection = sqlite3.connect("data/asthma_air_quality.db")
analysis_table = pandas.read_sql("SELECT * FROM county_asthma_air_quality WHERE air_quality_year = 2023", database_connection)
```

R (analysis):

```r
library(DBI)
database_connection <- dbConnect(RSQLite::SQLite(), "data/asthma_air_quality.db")
analysis_table <- dbGetQuery(database_connection, "SELECT * FROM county_asthma_air_quality WHERE air_quality_year = 2023")
dbDisconnect(database_connection)
```

## Key columns in `county_asthma_air_quality`

| Column | Meaning |
|---|---|
| `county_fips`, `air_quality_year` | Together, one unique row. Use year 2023 for the main analysis and 2022 for the sensitivity check |
| `asthma_age_adjusted_percent` | Adults with current asthma (age-adjusted %), 2023 survey year |
| `smoking_`, `obesity_`, `no_health_insurance_`, `physical_inactivity_age_adjusted_percent` | Other county measures for the regression, all age-adjusted |
| `adult_population` | Weight for the population-weighted regression |
| `median_aqi` | Main air quality measure for the year |
| `percent_days_unhealthy_for_sensitive_or_worse` | Share of monitored days at "unhealthy for sensitive groups" or worse |
| `has_75_percent_of_days` | 1 if the county has AQI on at least 274 of 365 days |
| `asthma_data_status` | Why asthma might be empty: `available`, `not published for this state`, or `suppressed by CDC (population under 50)` |
| `air_quality_coverage` | Why air quality might be empty: `monitored`, `not monitored`, or `not comparable (Connecticut boundary change)` |

## Data sources

- **CDC PLACES: Local Data for Better Health, County Data, 2025 release** (data.cdc.gov dataset `swc5-untb`). Asthma and the other measures used here come from the 2023 BRFSS survey. Downloaded November 17, 2026.
- **EPA AirData pre-generated files**: `annual_aqi_by_county` and `daily_aqi_by_county` for 2022 and 2023 (files dated June 25, 2026 on EPA's file list). Downloaded November 17, 2026.

## Cleaning decisions

- **Counties are matched by 5-digit FIPS code, never by name.** EPA's yearly file only has county names, so we take each name's FIPS code from EPA's daily file. Every yearly row matched, and no name matched more than one code.
- **The national row in PLACES is dropped**, since it isn't a county.
- **Kentucky and Pennsylvania have no asthma estimates.** CDC did not publish 2023-based measures for these states (187 counties). They stay in the table with asthma empty.
- **One Texas county's estimates are suppressed by CDC** because its population is under 50.
- **Puerto Rico, the Virgin Islands and Mexico are dropped from the EPA data** (22 rows), because PLACES doesn't cover them.
- **Connecticut is marked "not comparable."** PLACES uses Connecticut's 9 new planning regions, and EPA uses the 8 old counties. The two don't line up, so Connecticut has asthma values but no air quality values.
- **Counties with short monitoring years are kept and flagged.** `has_75_percent_of_days` marks counties with at least 274 days of AQI, following EPA's usual 75% completeness rule. Summer-only ozone monitors can make a county look worse than a full year would.
- **Every county is kept**, whether or not it has a monitor. In 2023, 975 counties are monitored and about 2,160 are not. The main sample (asthma available and monitored) is 912 counties, 750 of which meet the 75% rule.
- **Poverty is not in the PLACES county file.** `no_health_insurance_age_adjusted_percent` is included as a stand-in for income level.

## Why SQLite instead of PostgreSQL

We planned on PostgreSQL but switched to SQLite because the database is small, only one person writes to it, and a single database file lets any teammate rebuild everything by running the pipeline, without installing a database server or Docker.