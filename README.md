# Girls Who Code Project 6L Florida Health Insurance Recommender

> **Scope:** Health insurance plans in Florida, for plan year **2026**.
>
> **Disclaimer:** This is a student project. It is not insurance, legal, or financial advice. Check [HealthCare.gov](https://www.healthcare.gov) or talk to a licensed agent before choosing a plan.

## What is this?

A tool that asks a shopper a few questions (county, age, household size, budget, how often they use care) and suggests Florida health insurance plans that fit, with a plain-language reason for each pick.

Behind the tool is a SQL data warehouse that collects public plan data, cleans it, and organizes it so the recommender can use it quickly.

## How it works

```
Public plan data (files or API)
        |
        v
   RAW layer       copied in, unchanged         (Bronze)
        |
        v
  CLEAN layer      duplicates, gaps, labels fixed (Silver)
        |
        v
 CURATED layer     star schema for the app       (Gold)
        |
        v
  Recommender      filters -> yearly cost -> score -> "why"
        |
        v
   App (shopper sees questionnaire and results)
```

We call the layers Raw, Clean, and Curated so they are not confused with insurance plan tiers (bronze, silver, gold).

## Repo map

| Folder | What is in it |
|---|---|
| `docs/` | PRD, insurance research, diagrams, data catalog, naming rules |
| `data/` | Downloaded plan files and made-up test shoppers (see `data/README.md`) |
| `ingestion/` | Code that fetches data and loads it into the Raw layer |
| `sql/` | Scripts that build the Raw, Clean, and Curated layers |
| `recommender/` | Filters, cost estimate, scoring, and explanations |
| `app/` | The questionnaire and results page |
| `tests/` | Data quality checks and persona tests |

## Getting started

### 1. What you need
- Git
- PostgreSQL and a viewer (pgAdmin or DBeaver)
- Python 3.x
- *(Update this list if the team picks different tools.)*

### 2. Get the code
```bash
git clone https://github.com/LenLemony/Project-6.git
cd Project-6
```

### 3. Set up your settings
```bash
cp .env.example .env
```
Open `.env` and fill in your own database details (and an API key, if the team uses one). **Never commit `.env`.**

### 4. Install Python packages
```bash
pip install -r requirements.txt
```

### 5. Build the warehouse
Run the SQL scripts in the order listed in `sql/run_order.md`. In short:
1. `sql/00_init/` creates the database and schemas
2. `sql/raw/` creates and loads the Raw tables
3. `sql/clean/` creates and loads the Clean tables
4. `sql/curated/` creates the Curated views

### 6. Run the app
```bash
# Update this command if the team uses a different tool
streamlit run app/app.py
```

## Data

- **Source:** *(fill in: where the plan data comes from)*
- **Plan year:** *(fill in)*
- **Date downloaded:** *(fill in)*
- **Notes:** Plans and prices change every year, so results are only correct for the plan year above.

Full details are in `data/README.md`. Large source files are not stored in Git.

## Privacy

- We use public plan data and made-up test shoppers only.
- The app does not ask for names or ID numbers and does not save shoppers' answers.

## Team

| Name | Role |
|---|---|
|Shanelle| Lead, Git, docs, ethics |
|Lara| Data sourcing, Raw and Clean layers |
|Dylan| Curated layer and modeling |
|Marcella| Recommender and interface |

## How we work together

1. Don't change `main` directly.
2. Make a branch for your task (for example `clean-layer` or `recommender`).
3. Commit small changes with clear messages.
4. Open a pull request using the template and ask a teammate to review.
5. Merge only after it runs and a teammate approves.
6. Keep `main` working so it is always safe to demo.

## Status

- [ ] Week 1: plan, research, repo, data sources
- [ ] Week 2: Raw layer
- [ ] Week 3: Clean layer
- [ ] Week 4: Curated layer, recommender, interface
- [ ] Week 5: docs, testing, demo

## License

See [LICENSE](LICENSE).