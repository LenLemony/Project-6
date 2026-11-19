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
- Streamlit

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

### 5. Run the app
```bash
# Update this command if the team uses a different tool
streamlit run app/app.py
```

## Data

- **Source:** Plan Attributes, Benefits and Cost Sharing, and Rate CMS Marketplace Public Use Files (PUFs)
- **Plan year:** 2026
- **Date downloaded:** 10/25/2026
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

- [X] Week 1: plan, research, repo, data sources
- [X] Week 2: Raw layer
- [X] Week 3: Clean layer
- [X] Week 4: Curated layer, recommender, interface
- [ ] Week 5: docs, testing, demo

## Machine learning prototype

The recommendations now use a saved **LGBMRanker** to return up to five plans
within the shopper's budget. The existing questionnaire, plan cards and charts
are kept in place.

The 2026 prototype supports individual and household comparisons using plan costs,
covered applicants, healthcare needs and preferences. It was trained on 600
hypothetical household profiles with 122 features. Its labels are generated from
preference rules, not real enrollment choices or verified suitability judgments.

### Added files and folders

| Location | What it contains |
|---|---|
| `preprocessing/` | Scripts to prepare the data, generate example labels and train the ranker |
| `data/processed/` | Generated plan features and training/validation/test datasets |
| `models/` | Saved model, feature definitions, configuration and training report |

The added recommender code builds shopper–plan features, loads the saved model,
and formats its results for the existing cards. Tests cover data joins, profile
handling, household calculations, ranking inputs and the app's results flow.

### Preparing data and training

Run these commands from the project folder after installing the requirements:

```bash
python -m preprocessing.prepare
python -m preprocessing.train_ranker --profiles 600
```

Training saves the model and its matching feature definitions. The app loads those
files when making recommendations; it does not retrain after each answer change.

See [the model explanation](docs/model_integration.md) for features, training and
evaluation, and [questionnaire coverage](docs/questionnaire_model_v2.md) for how
each answer is used.

ZIP-specific availability, subsidy amounts, final eligibility and named doctor or
medication checks still need work. Pricing currently uses a disclosed demonstration
rating area, so the results remain prototype comparisons.

## License

See [LICENSE](LICENSE).
