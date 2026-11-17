# AI Usage

This file records how our team used generative AI on this project. Each team member keeps their own section up to date.

## Our approach

In our proposal we planned to use AI mainly to debug, explain errors, and help choose libraries. In practice we also used it to draft files and guide coding in SQL, which we then ran, tested and checked on their own machine. Each entry below says exactly what the AI produced and what the team member did, so the split is clear.


## How to add an entry

1. Add your entry under your own name only. Editing only your own section avoids git merge conflicts.
2. Add one entry per work session, newest at the bottom, copying the template at the end of this file.
3. Be specific about what the AI wrote versus what you wrote, decided or checked yourself.  (When you are done delete this section for the final submission)

---


## Abdulmateen Oyediran: Data pipeline, database schema, and validation

### 2026-11-17: Building the data pipeline from scratch

#### Tools used

- Claude (Anthropic), in the Claude app.
- GitHub Copilot in VS Code.
- Claude model: OPus 5.5

#### What I asked for

- Help writing and troubleshooting Python commands, pipeline scripts, and SQL for cleaning, merging, and validating the data.
- Explanations of Python errors and database connection problems.
- Guidance on whether to switch from PostgreSQL to SQLite.
- Suggestions for coding choices, script headers, and project documentation.

#### What the AI produced

- Feedback on data issues based on checks of the CDC and EPA websites:
  - The EPA annual county file lacked FIPS codes.
  - PLACES had no 2023 asthma estimates for Kentucky and Pennsylvania.
  - PLACES used Connecticut's new planning regions.
- Diagnoses of setup and coding errors, including:
  - A PostgreSQL authentication failure associated with a separate local PostgreSQL installation using port 5432.
  - A Python indentation error.
- Checked my drafts of of the following pipeline files:
  - `scripts/database_connection.py`
  - `scripts/download_raw_data.py`
  - `scripts/load_raw_data.py`
  - `scripts/profile_raw_tables.py`
  - `scripts/build_clean_tables.py`
  - `scripts/validating_database.py`
  - `run_pipeline.py`
  - `sql/01_create_raw_tables.sql`
  - `sql/02_create_clean_tables.sql`
  - `sql/03_create_analysis_table.sql`
- A summary of the data-profile results and options for handling Connecticut, counties with short monitoring years, and the selection of county-level health measures.
- Initial drafts of the pipeline section of `README.md` and the AI-use documentation in `AI-USAGE.md`.
- Corrections to several lines of codes and word choices in comments`.
- Coding suggestions in VS Code and assistance drafting headers for my scripts.

#### What I did myself

- Built and assembled the working pipeline in my local project, creating the Python and SQL files and which was then given to Claude to check my work.
- Wrote and revised Python and SQL with AI guidance, rather than treating the generated drafts as finished deliverables.
- Ran every command and script on my own machine, worked through setup and execution problems, and reran the pipeline to check whether the changes resolved them.
- Managed the local development setup and made the final decision to switch from PostgreSQL to SQLite after encountering database setup and connection problems.
- Examined the data-profile results and made the final decisions about handling Connecticut, missing and suppressed asthma estimates, and counties with short monitoring years.
- Picked smoking, obesity, lack of health insurance, and physical inactivity as the additional county-level measures to include alongside asthma.
- Checked that the raw database tables contained the same number of rows as the downloaded source files and compared the EPA counts with EPA's published file list.
- Reviewed the cleaned county counts and the breakdown of available, unpublished, and suppressed asthma values to check that the outputs matched the data profile.
- Ran all 16 validation checks against the real data and confirmed that they passed.
- Wrote the original analysis-table comment that AI later helped correct.

#### Decisions I made

- Switched from PostgreSQL to SQLite after encountering setup problems, because a single database file would be easier for teammates to rebuild and could be accessed from both Python and R.
- Kept Connecticut in the dataset but marked it as "not comparable" rather than dropping it.
- Kept counties with short monitoring years and flagged those with fewer than 274 monitored days out of 365, using 75% coverage as the threshold.
- Included smoking, obesity, lack of health insurance, and physical inactivity as county-level measures alongside asthma.

#### How I checked it

- Confirmed that database row counts matched the downloaded files exactly:
  - PLACES: 229,298 rows.
  - EPA annual files: 993 and 1,004 rows.
  - EPA daily files: 325,707 and 324,751 rows.
- Compared the EPA row counts with EPA's published file list.
- Ran a data profile and confirmed that the cleaned counts matched its results:
  - 3,144 counties in total.
  - 2,956 counties with an asthma value.
  - 187 counties with no published asthma value in Kentucky and Pennsylvania.
  - One county with a suppressed asthma value.
- Ran all 16 validation checks against the real data; all passed.
- Fresh-copy rebuild test: [Add the result of cloning the repository into a new folder and running `python run_pipeline.py`. If this test was not completed, state that explicitly.]

#### Files affected

- All files in `scripts/` and `sql/`
- `run_pipeline.py`
- `environment.yml`
- `.gitignore`
- `README.md`
- `AI-USAGE.md`