#Create example households and synthetic labels for training.

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from preprocessing.prepare import ROOT
from recommender.features import PRIORITIES, build_candidates, load_catalog, model_matrix

LABEL_SOURCE = "synthetic_questionnaire_rule_v2"
USAGE_WEIGHT = {"Low": .5, "Moderate": 1., "High": 1.5, "Not sure": 1.}


def generate_profiles(count, rating_areas, seed):
    if count < 10 or not rating_areas:
        raise ValueError("Use at least 10 profiles and one rating area")
    rng = random.Random(seed)
    seen, profiles = set(), []
    # Make example households. Tax and income answers do not change plan prices.
    priority_options = list(PRIORITIES)
    for attempt in range(count * 100):
        priorities = sorted(rng.sample(priority_options, rng.choice([1, 2])))
        profile = {
            "age": rng.choice([18, 21, 25, 30, 35, 40, 45, 50, 55, 60, 63]),
            "smokes": rng.random() < .25, "plan_year": 2026,
            "rating_area_id": rng.choice(rating_areas),
            "monthly_budget": rng.choice([250, 350, 500, 650, 750, 1000, 1250, 1500, 2000]),
            "healthcare_usage": rng.choice(list(USAGE_WEIGHT)), "priorities": priorities,
            "referral_preference": rng.choice(["Very important", "Somewhat important", "Not important"]),
            "out_network": rng.choice(["Yes", "No", "Not sure"]),
        }
        profile["applicants"] = [{"age": profile["age"], "smokes": profile["smokes"], "role": "self",
                                   "pregnancy": rng.choice(["No", "No", "Yes", "Prefer not to say"])}]
        if rng.random() < .45:
            profile["applicants"].append({"age": rng.choice([21, 25, 35, 45, 55, 63]),
                "smokes": rng.random() < .2, "role": "partner", "pregnancy": rng.choice(["No", "Yes", "Prefer not to say"])})
        if rng.random() < .4:
            for child in range(rng.choice([1, 2, 3, 4])):
                profile["applicants"].append({"age": rng.choice([0, 5, 12, 16, 20, 23]),
                    "smokes": False, "role": "dependent", "pregnancy": "No"})
        if len(profile["applicants"]) > 1:
            profile["monthly_budget"] *= min(len(profile["applicants"]), 3)
        signature = json.dumps(profile, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        profile["profile_id"] = f"synthetic_{len(profiles):04d}"
        profiles.append(profile)
        if len(profiles) == count:
            return profiles
    raise ValueError("Could not generate enough unique profiles")


def synthetic_labels(candidates):
    """Score the example plans using the preference rules below.

    These are practice labels, not real medical cost estimates. Only label plans
    with known combined medical and drug deductibles and out-of-pocket limits.
    Other plans stay in the catalog for later review.
    """
    required = ["monthly_premium", "deductible_individual", "moop_individual"]
    c = candidates.dropna(subset=required).copy()
    if len(c) < 5:
        return c
    usage = c["healthcare_usage"].map(USAGE_WEIGHT).astype(float)
    wp = 1 + 2 * c["priority_premium"].astype(float)
    wd = usage * (1 + 2 * c["priority_care_cost"].astype(float))
    wm = .6 + 2 * c["priority_protection"].astype(float)
    referral_weight = c["referral_preference"].map(
        {"Very important": .4, "Somewhat important": .15, "Not important": 0.}
    ).astype(float)
    referral_penalty = c["referral_required"].astype("Float64").fillna(.5)
    # Compare the selected preferences using simple rules.
    # These rules do not predict medical bills or confirm coverage.
    network = pd.to_numeric(c.get("out_of_network_service_fraction", pd.Series(.5, index=c.index)), errors="coerce").fillna(.5)
    network_weight = c["out_network_preference"].map({"Yes": 1., "No": 0., "Not sure": .25}) if "out_network_preference" in c else 0.
    freedom = c.get("priority_doctor_freedom", pd.Series(False, index=c.index)).astype(float)
    maternity = c.get("maternity_example_cost", pd.Series(float("nan"), index=c.index)).fillna(10000) / 10000
    pregnant = c.get("pregnancy_count", pd.Series(0, index=c.index))
    c["rule_loss"] = (
        wp * c["monthly_premium"] / 1000
        + wd * c["deductible_individual"] / 10000
        + wm * c["annual_premium_plus_moop"] / 20000
        + 3 * (c["monthly_premium"] / c["monthly_budget"].clip(lower=1) - 1).clip(lower=0)
        + referral_weight * referral_penalty
        + (network_weight + freedom) * (1 - network)
        + .4 * freedom * referral_penalty
        + .7 * pregnant * maternity
    ).astype(float)
    # Give tied scores the same label. A 4 means the plan ranked well
    # under these rules, not that someone has checked its suitability.
    percentile = (c["rule_loss"].rank(method="average") - 1) / (len(c) - 1)
    c["relevance"] = np.floor(5 * (1 - percentile)).clip(0, 4).astype(int)
    c["label_source"] = LABEL_SOURCE
    c["profile_source"] = "hypothetical_covered_household"
    c["human_reviewed"] = False
    return c


def assign_splits(profile_ids, seed):
    ids = sorted(profile_ids)
    random.Random(seed).shuffle(ids)
    train_end, valid_end = int(.6 * len(ids)), int(.8 * len(ids))
    return {identifier: ("train" if i < train_end else "validation" if i < valid_end else "test")
            for i, identifier in enumerate(ids)}


def create_dataset(processed, output, count=300, seed=2026):
    plans, rates = load_catalog(processed)
    grouped_rates = dict(tuple(rates.groupby("rating_area_id", sort=True)))
    profiles = generate_profiles(count, sorted(grouped_rates), seed)
    groups, audit, kept = [], [], []
    for profile in profiles:
        candidates = build_candidates(plans, grouped_rates[profile["rating_area_id"]], profile)
        labeled = synthetic_labels(candidates)
        usable = len(labeled) >= 5 and "relevance" in labeled and labeled["relevance"].nunique() > 1
        audit.append({"profile_id": profile["profile_id"], "candidates": len(candidates),
                      "labeled_rows": len(labeled) if usable else 0,
                      "missing_limit_rows": int(candidates[["deductible_individual", "moop_individual"]].isna().any(axis=1).sum()),
                      "included": usable})
        if usable:
            groups.append(labeled)
            kept.append(profile)
    if len(groups) < 10:
        raise ValueError("Insufficient usable profile groups")
    data = pd.concat(groups, ignore_index=True).sort_values(["profile_id", "variant_id"]).reset_index(drop=True)
    mapping = assign_splits([p["profile_id"] for p in kept], seed)
    data["split"] = data["profile_id"].map(mapping)
    matrix = model_matrix(data)
    categorical = list(matrix.select_dtypes(include="category").columns)
    metadata = ["profile_id", "plan_year", "variant_id", "relevance", "rule_loss", "label_source",
                "profile_source", "human_reviewed", "geographic_availability_verified", "eligibility_verified"]
    # Keep the label calculations and row details out of the model inputs.
    rows = pd.concat([data[metadata], matrix], axis=1)
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name in ["train", "validation", "test"]:
        subset = rows.loc[data["split"].eq(name)].reset_index(drop=True)
        subset.to_csv(output / f"{name}.csv.gz", index=False, compression="gzip")
        summary[name] = {"profiles": int(subset.profile_id.nunique()), "rows": len(subset),
                         "labels": {str(k): int(v) for k, v in subset.relevance.value_counts().sort_index().items()}}
    for profile in kept:
        profile["split"] = mapping[profile["profile_id"]]
    (output / "profiles.json").write_text(json.dumps(kept, indent=2), encoding="utf-8")
    pd.DataFrame(audit).to_csv(output / "profile_audit.csv", index=False)
    review = data.groupby("profile_id", sort=False).head(10).copy()
    review["reviewed_relevance"] = pd.NA
    review["reviewer_notes"] = pd.NA
    review[["profile_id", "plan_year", "variant_id", "plan_name", "monthly_premium", "monthly_budget",
            "deductible_individual", "moop_individual", "relevance", "label_source", "reviewed_relevance", "reviewer_notes"]].to_csv(output / "review_template.csv", index=False)
    schema = {"features": list(matrix.columns), "categorical_features": categorical,
              "target": "relevance", "group_id": "profile_id", "label_source": LABEL_SOURCE,
              "categorical_missing": "pandas category code -1", "numeric_missing": "NaN",
              "model": "LGBMRanker"}
    (output / "schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    manifest = {"seed": seed, "requested_profiles": count, "included_profiles": len(kept),
                "splits": summary, "model_features": len(matrix.columns), "label_source": LABEL_SOURCE,
                "source_quality_report_sha256": hashlib.sha256((processed / "quality_report.json").read_bytes()).hexdigest(),
                "limitations": ["All labels are synthetic, not expert-reviewed or observed outcomes.",
                                "Splits hold out profiles; plan products may occur in every split.",
                                "2026 catalog; availability and eligibility unverified.",
                                "Labels omit subsidies, actual utilization, network breadth and provider/drug checks."]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return manifest


def load_split(directory, name):
    """Load one data split using the categories found in the training set."""
    if name not in {"train", "validation", "test"}:
        raise ValueError("Unknown split")
    schema = json.loads((directory / "schema.json").read_text())
    data = pd.read_csv(directory / f"{name}.csv.gz", dtype={"profile_id": "string", "variant_id": "string"})
    data = data.sort_values(["profile_id", "variant_id"]).reset_index(drop=True)
    x = data[schema["features"]].copy()
    # Use the training categories for every split.
    # Treat new categories as missing instead of giving them different codes.
    training_categories = pd.read_csv(
        directory / "train.csv.gz", usecols=schema["categorical_features"], dtype="string"
    )
    for col in x:
        if col in schema["categorical_features"]:
            levels = sorted(training_categories[col].dropna().unique())
            values = x[col].astype("string")
            x[col] = pd.Categorical(values.where(values.isin(levels)), categories=levels)
        else:
            x[col] = pd.to_numeric(x[col], errors="raise").astype(float)
    return x, data[schema["target"]], data[schema["group_id"]].astype(str), schema["categorical_features"]


def ranking_group_sizes(group_ids):
    """Count the plans in each shopper's group for LightGBM."""
    ids = pd.Series(group_ids).reset_index(drop=True)
    if ids.isna().any():
        raise ValueError("Missing ranking group ID")
    blocks = ids.loc[ids.ne(ids.shift())]
    if blocks.duplicated().any():
        raise ValueError("Ranking groups must be contiguous")
    return ids.groupby(ids, sort=False).size().to_numpy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/labeled_synthetic")
    parser.add_argument("--profiles", type=int, default=300)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    create_dataset(args.processed, args.output, args.profiles, args.seed)


if __name__ == "__main__":
    main()
