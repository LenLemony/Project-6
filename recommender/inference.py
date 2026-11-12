"""Use the saved ranker without retraining or notebook variables."""

import json
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from recommender.features import build_candidates, load_catalog, model_matrix

ROOT = Path(__file__).resolve().parents[1]


def load_assets():
    model = lgb.Booster(model_file=str(ROOT / "models/insurance_ranker.txt"))
    plans, rates = load_catalog(ROOT / "data/processed")
    schema = json.loads((ROOT / "models/feature_schema.json").read_text(encoding="utf-8"))
    if schema["columns"] != model.feature_name():
        raise ValueError("Saved model and feature schema do not match; export them together")
    return model, plans, rates, schema


def recommend(profile, assets):
    model, plans, rates, schema = assets
    # Select the price region before matching age and dates to avoid scanning
    # the entire rates table on every results-page interaction.
    region_rates = rates.loc[rates["rating_area_id"].eq(profile["rating_area_id"])]
    candidates = build_candidates(plans, region_rates, profile)
    candidates = candidates.loc[candidates["within_budget"]].copy()
    if candidates.empty:
        return candidates
    x = model_matrix(candidates).loc[:, schema["columns"]]
    for col, categories in schema["categories"].items():
        values = x[col].astype("string")
        x[col] = pd.Categorical(values.where(values.isin(categories)), categories=categories)
    # Avoid creating a large CPU thread pool for fewer than a few hundred rows.
    candidates["ranking_score"] = model.predict(x, num_threads=1, validate_features=True)
    return candidates.sort_values(["ranking_score", "variant_id"], ascending=[False, True]).head(5)
