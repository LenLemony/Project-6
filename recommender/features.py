"""Build single-applicant features for a *supplied* rating area.

This module does not infer ZIP availability, subsidies, or variant eligibility.
"""

from datetime import date
import math

import pandas as pd

from preprocessing.prepare import KEY, LIMITS, PLAN_BOOLS, boolean

PRIORITIES = {
    "Lower monthly premiums": "priority_premium",
    "Lower costs when receiving care": "priority_care_cost",
    "Protection against large medical bills": "priority_protection",
    "More freedom to choose doctors": "priority_doctor_freedom",
}


def load_catalog(directory):
    """Restore CSV types explicitly; blank values remain missing."""
    plans = pd.read_csv(directory / "plan_features.csv", dtype="string")
    rates = pd.read_csv(directory / "rates.csv.gz", dtype="string")
    for col in PLAN_BOOLS:
        plans[col] = boolean(plans[col])
    for col in plans.columns:
        if col.endswith(("_covered", "_after_deductible")):
            plans[col] = boolean(plans[col])
        if col in LIMITS.values() or col.endswith("_amount"):
            plans[col] = pd.to_numeric(plans[col], errors="raise").astype("Float64")
    for frame in (plans, rates):
        frame["plan_year"] = frame["plan_year"].astype("Int64")
    for col in ["min_age", "max_age"]:
        rates[col] = rates[col].astype("Int64")
    for col in ["non_tobacco_premium", "tobacco_premium"]:
        rates[col] = rates[col].astype("Float64")
    for frame, prefix in [(plans, "plan"), (rates, "rate")]:
        for suffix in ["effective_date", "expiration_date"]:
            frame[f"{prefix}_{suffix}"] = pd.to_datetime(frame[f"{prefix}_{suffix}"])
    return plans, rates


def profile_from_answers(answers, *, profile_id, rating_area_id, plan_year):
    """Adapt questionnaire session state after geography/year are resolved externally."""
    if (not answers.get("include_me") or answers.get("include_partner")
            or answers.get("include_dependents")):
        raise ValueError("First prototype supports one applicant only; family pricing is not implemented")
    if answers.get("you_smoke") not in ("Yes", "No"):
        raise ValueError("A smoking answer is required")
    return {
        "profile_id": profile_id, "age": answers["you_age"],
        "smokes": answers["you_smoke"] == "Yes", "plan_year": plan_year,
        "rating_area_id": rating_area_id, "monthly_budget": answers["monthly_budget"],
        "healthcare_usage": answers["healthcare_usage"].split(" - ", 1)[0],
        "priorities": list(answers["priorities"]),
        "referral_preference": answers["referral_preference"], "out_network": answers["out_network"],
    }


def build_candidates(plans, rates, profile):
    age, budget = profile["age"], profile["monthly_budget"]
    if isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120:
        raise ValueError("age must be a whole number from 0 to 120")
    if not isinstance(profile["smokes"], bool):
        raise ValueError("smokes must be True or False")
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("monthly_budget must be a finite nonnegative number")
    usage = profile.get("healthcare_usage", "Not sure")
    if usage not in ("Low", "Moderate", "High", "Not sure"):
        raise ValueError("Unknown healthcare usage category")
    if set(profile.get("priorities", [])) - set(PRIORITIES):
        raise ValueError("Unknown priority")
    year = profile["plan_year"]
    as_of = pd.Timestamp(profile.get("coverage_date", date(year, 1, 1)))
    if as_of.year != year or year not in plans["plan_year"].unique():
        raise ValueError("Coverage year/date does not match the catalog")
    p = plans.loc[
        plans["plan_year"].eq(year) & plans["state_code"].eq("FL")
        & plans["market_coverage"].eq("Individual") & plans["dental_only"].eq(False)
        & plans["variant_class"].str.match(r"^Standard .* On Exchange Plan$", na=False)
        & plans["metal_level"].ne("Catastrophic")
        & plans["plan_effective_date"].le(as_of)
        & (plans["plan_expiration_date"].isna() | plans["plan_expiration_date"].ge(as_of))
    ].copy()
    r = rates.loc[
        rates["plan_year"].eq(year) & rates["state_code"].eq("FL")
        & rates["rating_area_id"].eq(profile["rating_area_id"])
        & rates["min_age"].le(age) & (rates["max_age"].isna() | rates["max_age"].ge(age))
        & rates["rate_effective_date"].le(as_of) & rates["rate_expiration_date"].ge(as_of)
    ].copy()
    join_keys = KEY + ["issuer_id", "base_plan_id"]
    # One active rate per plan/profile is required; never pick an arbitrary revision.
    if r.duplicated(join_keys).any():
        raise ValueError("Multiple active rates match this profile")
    r["monthly_premium"] = r["non_tobacco_premium"]
    if profile["smokes"]:
        distinguished = r["tobacco_category"].eq("Tobacco User/Non-Tobacco User")
        r.loc[distinguished, "monthly_premium"] = r.loc[distinguished, "tobacco_premium"]
    c = p.merge(r[join_keys + ["rating_area_id", "age_label", "monthly_premium"]],
                on=join_keys, validate="many_to_one")
    c = c.loc[c["monthly_premium"].gt(0)].copy()
    c["profile_id"] = profile["profile_id"]
    c["age"] = age
    c["smokes"] = profile["smokes"]
    c["monthly_budget"] = budget
    c["healthcare_usage"] = usage  # categorical; "Not sure" is not zero usage
    c["premium_minus_budget"] = c["monthly_premium"] - budget
    c["within_budget"] = c["monthly_premium"].le(budget)
    c["premium_to_budget"] = c["monthly_premium"] / budget if budget > 0 else pd.NA
    c["annual_premium"] = 12 * c["monthly_premium"]
    c["deductible_individual"] = c["integrated_deductible_individual"].where(c["deductibles_integrated"])
    c["moop_individual"] = c["integrated_moop_individual"].where(c["moop_integrated"])
    c["annual_premium_plus_moop"] = c["annual_premium"] + c["moop_individual"]
    for label, col in PRIORITIES.items():
        c[col] = label in profile.get("priorities", [])
    c["referral_preference"] = profile.get("referral_preference", "Not important")
    c["out_network_preference"] = profile.get("out_network", "Not sure")
    c["geographic_availability_verified"] = False
    c["eligibility_verified"] = False
    c["plan_expiration_date_missing"] = c["plan_expiration_date"].isna()
    # No target column: real suitability labels must be added separately.
    return c.sort_values(["profile_id", "variant_id"]).reset_index(drop=True)


def model_matrix(candidates):
    """Explicit model inputs; exclude identifiers, prose, URLs, and audit fields.

    Categories are suitable for LightGBM. When splitting a dataset, establish
    categorical vocabularies using training profiles and reuse them on validation
    and live inputs. CSV does not retain categorical dtypes; see feature_schema.json.
    """
    numeric = ["age", "smokes", "monthly_budget", "monthly_premium", "premium_minus_budget",
               "within_budget", "premium_to_budget", "annual_premium", "deductible_individual",
               "moop_individual", "annual_premium_plus_moop", "referral_required", "hsa_eligible",
               "deductibles_integrated", "moop_integrated"] + list(LIMITS.values()) + list(PRIORITIES.values())
    numeric += [col for col in candidates.columns if col.endswith(("_covered", "_amount", "_after_deductible"))]
    numeric = list(dict.fromkeys(numeric))
    categorical = ["plan_type", "metal_level", "healthcare_usage", "referral_preference", "out_network_preference"]
    categorical += [col for col in candidates.columns if col.endswith(("_parse_status", "_basis"))]
    result = candidates[numeric + categorical].copy()
    for col in numeric:
        result[col] = pd.to_numeric(result[col], errors="raise").astype("float64")
    for col in categorical:
        result[col] = result[col].astype("category")
    return result
