# Run Order

Follow these steps **in order** to build the whole warehouse from scratch. All commands are run from the **top folder of the repo**.

> Replace `your_username` with your PostgreSQL username. `psql` will ask for your password.
> Keep this file up to date: whenever you add or rename a script, update the list below.

## Layers at a glance

| Layer | Schema name | What happens |
|---|---|---|
| Raw (Bronze) | `raw` | Source data copied in, unchanged |
| Clean (Silver) | `clean` | Duplicates, gaps, and labels fixed |
| Curated (Gold) | `curated` | Star schema the recommender reads |

## Steps

| # | Step | Script | What it does | Done when... |
|---|---|---|---|---|
| 0 | Set up settings | `.env` (copy from `.env.example`) | Stores your database details | `.env` exists and is filled in |
| 1 | Create database and schemas | `sql/00_init/create_database_and_schemas.sql` | Makes the database and the `raw`, `clean`, and `curated` schemas | The three schemas exist |
| 2 | Get the source data | `ingestion/fetch_from_api.py` or `ingestion/download_files.py` | Downloads the plan files into `data/source/` | Files are in `data/source/` |
| 3 | Create Raw tables | `sql/raw/ddl_raw.sql` | Creates empty tables that match the source files | Tables exist in `raw` |
| 4 | Load Raw tables | `ingestion/load_to_raw.py` (and `sql/raw/load_raw.sql` if used) | Copies source data into Raw | Row counts match the source files |
| 5 | Create Clean tables | `sql/clean/ddl_clean.sql` | Creates the cleaned tables | Tables exist in `clean` |
| 6 | Load Clean tables | `sql/clean/load_clean.sql` | Cleans the Raw data and loads it | Clean checks pass (step 7) |
| 7 | Check the Clean layer | `tests/sql/quality_checks_clean.sql` | Looks for duplicates, missing values, and bad codes | No problems found |
| 8 | Create Curated views | `sql/curated/create_curated_views.sql` | Builds the star schema (`dim_` and `fact_` tables) | Views or tables exist in `curated` |
| 9 | Check the Curated layer | `tests/sql/quality_checks_curated.sql` | Looks for missing keys and doubled rows | No problems found |
| 10 | Run the recommender tests | `pytest tests/` | Runs the persona tests | All tests pass |
| 11 | Start the app | `streamlit run app/app.py` | Opens the questionnaire and results page | The app loads |

## Commands

**Step 1: create the database**
Connect to the default `postgres` database first, since you can't create a database while connected to it.
```bash
psql -U your_username -d postgres -f sql/00_init/create_database_and_schemas.sql
```

**Steps 3, 5, 7, 8, 9: run a SQL script**
```bash
psql -U your_username -d fl_insurance -f sql/raw/ddl_raw.sql
psql -U your_username -d fl_insurance -f sql/clean/ddl_clean.sql
psql -U your_username -d fl_insurance -f sql/clean/load_clean.sql
psql -U your_username -d fl_insurance -f tests/sql/quality_checks_clean.sql
psql -U your_username -d fl_insurance -f sql/curated/create_curated_views.sql
psql -U your_username -d fl_insurance -f tests/sql/quality_checks_curated.sql
```

**Steps 2 and 4: run the Python scripts**
```bash
python ingestion/download_files.py
python ingestion/load_to_raw.py
```

**Steps 10 and 11: tests and app**
```bash
pytest tests/
streamlit run app/app.py
```

## Rebuilding from scratch

To start over, drop and recreate the database (or the three schemas), then run the steps again from step 1. Because every step is a script, nobody should ever need to click around to rebuild.

## Rules for this file

- Add new scripts in the right spot in the table, and renumber if needed.
- If a script must run before another, say why in a short note.
- Re-run steps 7 and 9 after any change to the Clean or Curated layers.
- Plan year and data source are listed in `data/README.md`. Check them before loading new data.