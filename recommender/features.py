"""Prepare the plan features for each person seeking coverage.

The rating area must be supplied. ZIP availability and eligibility still need checking.
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
    """Load the prepared files and restore their column types."""
    plans = pd.read_csv(directory / "plan_features.csv", dtype="string")
    rates = pd.read_csv(directory / "rates.csv.gz", dtype="string")
    for col in PLAN_BOOLS:
        plans[col] = boolean(plans[col])
    for col in plans.columns:
        if col.endswith(("_covered", "_after_deductible")):
            plans[col] = boolean(plans[col])
        if col in LIMITS.values() or col.endswith("_amount") or col == "maternity_example_cost":
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
    """Collect the questionnaire answers for pricing and benefits checks."""
    applicants = []
    def add(prefix, role):
        age = answers.get(prefix + "_age")
        smoke = answers.get(prefix + "_smoke")
        if age is None or smoke not in ("Yes", "No"):
            raise ValueError(f"Complete age and smoking answers for {role}")
        applicants.append({"age": int(age), "smokes": smoke == "Yes", "role": role,
                           "pregnancy": answers.get(prefix + "_pregnant", "Prefer not to say")})
    if answers.get("include_me"):
        add("you", "self")
    if answers.get("include_partner"):
        add("spouse", "partner")
    if answers.get("include_dependents"):
        count = int(answers.get("total_dependents", 0))
        if not 1 <= count <= 30:
            raise ValueError("Enter a supported number of covered dependents (1–30)")
        for i in range(count):
            add(f"dependent_{i}", "dependent")
    if not applicants:
        raise ValueError("Select at least one applicant")
    return {
        "profile_id": profile_id, "age": applicants[0]["age"],
        "smokes": applicants[0]["smokes"], "applicants": applicants, "plan_year": plan_year,
        "rating_area_id": rating_area_id, "monthly_budget": answers["monthly_budget"],
        "healthcare_usage": answers["healthcare_usage"].split(" - ", 1)[0],
        "priorities": list(answers["priorities"]),
        "referral_preference": answers["referral_preference"], "out_network": answers["out_network"],
        "questionnaire_context": {key: answers.get(key) for key in [
            "zip_code", "is_dependent", "dependent_total_household", "married", "jointly",
            "has_dependents", "total_dependents_tax", "income"]},
    }


def _single_candidates(plans, rates, profile):
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
    if "child_only_offering" in p and age >= 21:
        p = p.loc[p["child_only_offering"].ne("Allows Child-Only")].copy()
    r = rates.loc[
        rates["plan_year"].eq(year) & rates["state_code"].eq("FL")
        & rates["rating_area_id"].eq(profile["rating_area_id"])
        & rates["min_age"].le(age) & (rates["max_age"].isna() | rates["max_age"].ge(age))
        & rates["rate_effective_date"].le(as_of) & rates["rate_expiration_date"].ge(as_of)
    ].copy()
    join_keys = KEY + ["issuer_id", "base_plan_id"]
    # Check that only one current rate matches each plan.
    if r.duplicated(join_keys).any():
        raise ValueError("Multiple active rates match this profile")
    r["monthly_premium"] = r["non_tobacco_premium"]
    if profile["smokes"] and age >= 21:
        distinguished = r["tobacco_category"].eq("Tobacco User/Non-Tobacco User")
        r.loc[distinguished, "monthly_premium"] = r.loc[distinguished, "tobacco_premium"]
    c = p.merge(r[join_keys + ["rating_area_id", "age_label", "monthly_premium"]],
                on=join_keys, validate="many_to_one")
    c = c.loc[c["monthly_premium"].gt(0)].copy()
    c["profile_id"] = profile["profile_id"]
    c["age"] = age
    c["smokes"] = profile["smokes"]
    c["monthly_budget"] = budget
    c["healthcare_usage"] = usage  # Keep "Not sure" as its own answer.
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
    # Add the training labels separately.
    return c.sort_values(["profile_id", "variant_id"]).reset_index(drop=True)


def build_candidates(plans, rates, profile):
    """Calculate premiums for the people who need coverage.

    Only the three oldest dependent children under 21 count toward the premium.
    Prices are before subsidies, and joint enrollment still needs checking.
    Health answers do not change the published rates.
    """
    applicants = profile.get("applicants") or [{"age": profile["age"], "smokes": profile["smokes"], "role": "self", "pregnancy": profile.get("pregnancy", "Prefer not to say")}]
    children = sorted([i for i, a in enumerate(applicants) if a.get("role") == "dependent" and a["age"] < 21], key=lambda i: applicants[i]["age"], reverse=True)
    billed = set(range(len(applicants))) - set(children[3:])
    frames = []
    for applicant in applicants:
        part = _single_candidates(plans, rates, dict(profile, age=applicant["age"], smokes=applicant["smokes"]))
        frames.append(part.set_index("variant_id"))
    shared = frames[0].index
    for frame in frames[1:]:
        shared = shared.intersection(frame.index, sort=False)
    c = frames[0].loc[shared].reset_index().copy()
    if len(applicants) > 1:
        c["monthly_premium"] = sum(frames[i].loc[shared, "monthly_premium"].reset_index(drop=True) for i in sorted(billed))
        c["deductible_individual"] = c["integrated_deductible_family_group"].where(c["deductibles_integrated"])
        c["moop_individual"] = c["integrated_moop_family_group"].where(c["moop_integrated"])
    budget = profile["monthly_budget"]
    c["premium_minus_budget"] = c["monthly_premium"] - budget
    c["within_budget"] = c["monthly_premium"].le(budget)
    c["premium_to_budget"] = c["monthly_premium"] / budget if budget > 0 else pd.NA
    c["annual_premium"] = c["monthly_premium"] * 12
    c["annual_premium_plus_moop"] = c["annual_premium"] + c["moop_individual"]
    c["covered_people"] = len(applicants)
    c["billed_people"] = len(billed)
    c["covered_children"] = sum(a.get("role") == "dependent" and a["age"] < 21 for a in applicants)
    c["youngest_age"] = min(a["age"] for a in applicants)
    c["oldest_age"] = max(a["age"] for a in applicants)
    c["pregnancy_count"] = sum(a.get("pregnancy") == "Yes" for a in applicants)
    c["pregnancy_unknown_count"] = sum(a.get("pregnancy", "Prefer not to say") == "Prefer not to say" for a in applicants)
    c["covered_smokers"] = sum(a["smokes"] for a in applicants)
    # Compare out-of-network cost sharing for these services.
    # This does not tell us which doctors are in the network.
    cols = [f"{s}_out_of_network_coinsurance_amount" for s in ["primary_care", "specialist", "inpatient_hospital"]]
    if all(col in c for col in cols):
        c["out_of_network_service_fraction"] = c[cols].astype("Float64").lt(1).where(c[cols].notna()).mean(axis=1)
    else:
        c["out_of_network_service_fraction"] = pd.NA
    return c.sort_values(["profile_id", "variant_id"]).reset_index(drop=True)


def model_matrix(candidates):
    """Select the columns used by the model.

    Keep IDs, descriptions and links out of the training features. Use the same
    training categories for validation and predictions. CSV files lose these
    category types, so they need to be restored when loading the data.
    """
    numeric = ["age", "smokes", "monthly_budget", "monthly_premium", "premium_minus_budget",
               "within_budget", "premium_to_budget", "annual_premium", "deductible_individual",
               "moop_individual", "annual_premium_plus_moop", "referral_required", "hsa_eligible",
               "deductibles_integrated", "moop_integrated"] + list(LIMITS.values()) + list(PRIORITIES.values())
    numeric += ["covered_people", "billed_people", "covered_children", "youngest_age", "oldest_age",
                "pregnancy_count", "pregnancy_unknown_count", "covered_smokers",
                "out_of_network_service_fraction", "maternity_example_cost"]
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
