# Health insurance recommendation model

The project uses LightGBM's `LGBMRanker` to rank health insurance plans based on
questionnaire answers. It compares the plans for one person or household and
returns up to five options within their monthly budget.

The current version uses Florida plan data for **2026**. Its labels come from
rules applied to hypothetical shoppers, so it is a working prototype rather than
a model trained on real insurance choices or outcomes.

## How the model works

`LGBMRanker` builds a series of decision trees. Each new tree helps improve the
ranking produced by the earlier trees. The training objective is `lambdarank`,
which learns to place more relevant plans above less relevant plans for the same
shopper.

One data row represents a **shopper–plan pair**. All candidate plans for a shopper
form one ranking group. A plan can rank differently for two shoppers because their
budgets, household members and preferences differ.

The model returns a continuous score for each plan. Higher scores rank first.
These scores are not probabilities, prices or percentages, and they are not the
same thing as the 0–4 labels used during training.

## Plan data

The source archive contains three cleaned Florida datasets:

| Dataset | Rows | Information used |
|---|---:|---|
| Plan attributes | 2,201 | Plan variants, issuer, plan type, metal level, deductibles and out-of-pocket limits |
| Rates | 567,681 | Premiums by base plan, rating area, age band, tobacco category and coverage dates |
| Benefits | 154,745 | Covered services, copays, coinsurance, conditions and benefit explanations |

Prices are matched using the base plan ID. Benefits and financial limits are
matched using the full plan variant ID. Keeping these identifiers separate avoids
mixing a variant's benefits with another variant's limits.

The candidate builder selects standard on-exchange individual medical plans and
excludes catastrophic plans. It matches the coverage year, date, rating area and
each applicant's age and tobacco pricing. A household comparison requires a
matching plan for every covered applicant. Plans above the stated budget are
removed before the model produces the final ranking.

## Model features

The saved model uses **122 features**. They combine questionnaire answers, plan
attributes and calculated comparisons between the shopper and the plan.

| Feature group | Examples | What it describes |
|---|---|---|
| Applicant and household | Age, smoking status, covered people, billed people, covered children, youngest and oldest ages | Who needs coverage and how the household is priced |
| Budget and premium | Monthly budget, monthly premium, premium minus budget, premium-to-budget ratio, annual premium | How the plan's price compares with the budget |
| Financial limits | Individual and family deductibles, medical/drug limits, out-of-pocket maximum, annual premium plus maximum | The plan's cost-sharing structure and financial exposure |
| Healthcare needs | Expected usage, pregnancy count, unknown pregnancy answers, maternity example cost | Reported needs and the available maternity comparison data |
| Personal priorities | Lower premiums, lower care costs, protection against large bills, more doctor choice | What the shopper wants to prioritize |
| Plan characteristics | HMO/PPO/EPO/POS, metal level, referral requirements, HSA eligibility | The type of plan and selected coverage rules |
| Service benefits | Primary care, specialist visits, generic drugs, emergency care, hospital stays, prenatal and maternity care | Coverage and available cost-sharing details for each service |
| Payment conditions | After-deductible flags, payment basis, parsing status | Whether an amount needs additional conditions or review |
| Network preferences | Referral preference, out-of-network preference, selected-service cost-sharing comparison | Limited information relevant to access preferences |

The complete column list and categorical values are stored in
[`models/feature_schema.json`](../models/feature_schema.json).

### Household pricing

The feature builder matches each covered person's published premium and adds the
billed amounts. Among dependent children under 21, only the three oldest count
toward the premium calculation. Other covered applicants are still checked for
matching rates, even when their premium is not included in the total.

For multiple covered people, the displayed deductible and maximum use the
applicable integrated family-group limits. For one person, they use individual
limits. Missing limits stay missing; they do not become zero.

The covered household and tax household are kept separate. Someone claimed on a
tax return is not automatically someone seeking coverage in this comparison.

### Pregnancy and network information

Pregnancy answers add features about reported needs and maternity benefits. They
do not change published premiums. The maternity cost example comes from the
plan's Summary of Benefits and Coverage; it is not a prediction of the person's
medical bill.

The out-of-network feature compares available coinsurance information for selected
non-emergency services. It does not establish the size of a provider network,
whole-plan out-of-network coverage or whether a particular doctor participates.

### Answers handled outside the model

Income, marital status, joint filing and tax-dependent answers are used in the
benefits-screening logic. They are retained as questionnaire context rather than
being used to invent a different published premium. The app does not calculate
subsidy amounts or determine final eligibility.

ZIP codes are validated against the Florida list, but ZIP-to-plan availability
mapping is unfinished. The prototype still uses the demonstration rating area in
`models/inference_config.json` and identifies that limitation in the results.

## Preparing the features

Identifiers remain strings. Numerical columns are converted to numbers, while
categorical columns keep their training categories. Validation, test and live
inputs reuse those categories so a value keeps the same meaning across runs.
Unseen categories are treated as missing.

Missing values, zero and not-applicable rules are kept separate. For example,
`No Charge after deductible` includes both a zero amount and a deductible
condition. Unsupported cost text is marked for review instead of extracting an
arbitrary number from it.

Plan names, IDs, links, explanatory text, synthetic scoring calculations and
relevance labels are excluded from the model input columns.

## Training labels

The training data combines real plan records with **600 hypothetical household
profiles**. These profiles vary household members, ages, smoking status, pregnancy
answers, budgets, expected usage, priorities and access preferences.

A rule gives each candidate plan a comparison score based on premiums,
deductibles, maximum out-of-pocket exposure, budget overruns, referral requirements
and selected network and maternity preferences. The weights are chosen prototype
assumptions, not values learned from actual shoppers.

Plans are then assigned relevance labels from **0 to 4 within each shopper's
group**. Higher labels mean a better position under the rule, and tied scores get
the same label. A label of 4 does not confirm that a plan is affordable, available
or suitable for that person.

Only rows with known applicable integrated deductibles and out-of-pocket limits
receive these training labels. Other plans remain in the catalog.

## Training setup

The dataset contains **52,417 labeled shopper–plan rows**, split by shopper:

| Split | Profiles | Rows | Purpose |
|---|---:|---:|---|
| Training | 360 | 31,301 | Learn the ranking |
| Validation | 120 | 10,160 | Select the best training iteration |
| Test | 120 | 10,956 | Evaluate the selected model on held-out profiles |

All rows for one shopper stay in the same split. The same plan product may appear
in different splits, so this checks new hypothetical shoppers for the known
catalog rather than unseen products or future years.

The model allows up to 300 boosting rounds, uses up to 31 leaves per tree and has
a learning rate of 0.05. The random seed is 2026. Validation performance is checked
at each round, with an early-stopping patience of 30 rounds. The saved model uses
the best checkpoint, **iteration 293**.

## Evaluation

The metric is **NDCG@5**. It measures whether plans with higher relevance labels
appear near the top of each shopper's first five results. Scores are calculated
per shopper and then averaged. A score of 1 represents an ideal ranking under
those labels.

| Evaluation | NDCG@5 |
|---|---:|
| Validation | 0.9841 |
| Held-out test | 0.9891 |
| Test baseline: lowest premium first | 0.7093 |

These results are recorded in
[`models/training_report.json`](../models/training_report.json). They show how well
the model follows the synthetic preference rule. **0.9891 does not mean 98.91%
accuracy or that 98.91% of insurance recommendations are correct.** Directly
applying the rule remains the reference baseline for these labels.

## Producing recommendations

When the questionnaire is complete, the app builds candidate rows, applies the
budget filter and prepares the same feature columns used during training. The
saved model scores those rows, and the five highest-ranked plans fill the existing
cards and charts. If fewer than five plans qualify, it returns fewer.

Changing answers reruns the comparison and predictions. It does not retrain the
model. The explanations beside each plan describe its visible costs and
attributes; they are not explanations of the trees' internal reasoning.

## Current limits

The model is a 2026 prototype trained on synthetic preferences. It still needs
independently reviewed labels or appropriate observed feedback before its results
can support claims about real recommendation quality.

ZIP-specific availability, subsidy amounts, final eligibility, named-doctor checks
and medication formulary checks remain unfinished. Published gross premiums and
available benefit fields are useful for comparison, but do not establish that a
person can enroll in a plan or that it covers everything they need.
