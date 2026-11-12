"""Prepare the branch's cleaned CMS archive without modifying source files.

Run from any directory: python -m preprocessing.prepare (from the repo root).
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "plans": "fl_plan_attributes_cleaned_2026.csv",
    "rates": "fl_rates_cleaned_2026.csv",
    "benefits": "fl_benefits_cleaned_2026.csv",
}
PLAN_FIELDS = {
    "BusinessYear": "plan_year", "StateCode": "state_code",
    "IssuerId": "issuer_id", "IssuerMarketPlaceMarketingName": "issuer_name",
    "StandardComponentId": "base_plan_id", "PlanId": "variant_id",
    "PlanMarketingName": "plan_name", "PlanVariantMarketingName": "variant_name",
    "PlanType": "plan_type", "MetalLevel": "metal_level",
    "MarketCoverage": "market_coverage", "DentalOnlyPlan": "dental_only",
    "CSRVariationType": "variant_class", "QHPNonQHPTypeId": "exchange_class",
    "NetworkId": "network_id", "ServiceAreaId": "service_area_id",
    "FormularyId": "formulary_id", "IsHSAEligible": "hsa_eligible",
    "IsReferralRequiredForSpecialist": "referral_required",
    "MedicalDrugDeductiblesIntegrated": "deductibles_integrated",
    "MedicalDrugMaximumOutofPocketIntegrated": "moop_integrated",
    "PlanEffectiveDate": "plan_effective_date",
    "PlanExpirationDate": "plan_expiration_date",
    "URLForSummaryofBenefitsCoverage": "sbc_url",
}
LIMITS = {}
for source, name in [("TEHB", "integrated"), ("MEHB", "medical"), ("DEHB", "drug")]:
    for scope, label in [("Individual", "individual"), ("FamilyPerPerson", "family_per_person"), ("FamilyPerGroup", "family_group")]:
        LIMITS[f"{source}DedInnTier1{scope}"] = f"{name}_deductible_{label}"
        LIMITS[f"{source}InnTier1{scope}MOOP"] = f"{name}_moop_{label}"
PLAN_BOOLS = ["dental_only", "hsa_eligible", "referral_required", "deductibles_integrated", "moop_integrated"]
RATE_FIELDS = {
    "BusinessYear": "plan_year", "StateCode": "state_code", "IssuerId": "issuer_id",
    "PlanId": "base_plan_id", "RatingAreaId": "rating_area_id", "Age": "age_label",
    "Tobacco": "tobacco_category", "RateEffectiveDate": "rate_effective_date",
    "RateExpirationDate": "rate_expiration_date", "IndividualRate": "non_tobacco_premium",
    "IndividualTobaccoRate": "tobacco_premium",
}
BENEFIT_FIELDS = {
    "BusinessYear": "plan_year", "StateCode": "state_code", "IssuerId": "issuer_id",
    "StandardComponentId": "base_plan_id", "PlanId": "variant_id",
    "BenefitName": "benefit_name", "IsCovered": "covered",
    "Exclusions": "exclusions", "Explanation": "explanation",
    "LimitQty": "limit_quantity_raw", "LimitUnit": "limit_unit",
    "IsExclFromInnMOOP": "excluded_from_in_network_moop",
}
COSTS = {
    "CopayInnTier1": "in_network_copay", "CoinsInnTier1": "in_network_coinsurance",
    "CopayOutofNet": "out_of_network_copay", "CoinsOutofNet": "out_of_network_coinsurance",
}
SELECTED_BENEFITS = {
    "Primary Care Visit to Treat an Injury or Illness": "primary_care",
    "Specialist Visit": "specialist", "Generic Drugs": "generic_drugs",
    "Emergency Room Services": "emergency_room",
    "Inpatient Hospital Services (e.g., Hospital Stay)": "inpatient_hospital",
}
KEY = ["plan_year", "state_code"]


def boolean(series):
    """Unknown stays unknown, never False."""
    return series.astype("string").str.strip().str.lower().map(
        {"true": True, "false": False, "yes": True, "no": False,
         "covered": True, "not covered": False}
    ).astype("boolean")


def numeric(series, label, maximum=None):
    result = pd.to_numeric(series, errors="coerce").astype("Float64")
    bad = series.notna() & result.isna()
    if bad.any() or result.lt(0).any() or (maximum is not None and result.gt(maximum).any()):
        raise ValueError(f"Invalid numeric values in {label}")
    return result


def unique(frame, keys, label):
    if frame[keys].isna().any().any():
        raise ValueError(f"Missing {label} keys: {keys}")
    if frame.duplicated(keys).any():
        raise ValueError(f"Conflicting/duplicate {label} keys: {keys}")


def age_bounds(label):
    if label == "0-14":
        return 0, 14
    if label == "64 and over":
        return 64, pd.NA
    if re.fullmatch(r"\d+", str(label)):
        return int(label), int(label)
    raise ValueError(f"Unsupported age category: {label}")


def parse_cost(value, coinsurance=False):
    """Parse only complete supported expressions; retain raw rules separately.

    Numeric extraction from arbitrary prose could mistake a visit count for a price.
    A parsed amount still needs its deductible, basis, coverage, and explanation.
    """
    result = {"amount": pd.NA, "after_deductible": pd.NA,
              "basis": pd.NA, "parse_status": "missing"}
    if pd.isna(value):
        return result
    text = str(value).strip()
    if text.lower() == "not applicable":
        return dict(result, parse_status="not_applicable")
    amount = r"\d[\d,]*(?:\.\d+)?"
    head = rf"(?P<number>{amount})%\s*(?:Coinsurance)?" if coinsurance else rf"\$(?P<number>{amount})"
    head = rf"(?:{head}|(?P<free>No Charge))"
    pattern = head + r"(?:\s+per\s+(?P<basis>Day|Stay|Visit|Prescription))?(?:\s+(?P<when>after|before)\s+deductible)?"
    match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
    if not match:
        return dict(result, parse_status="needs_review")
    value = 0.0 if match["free"] else float(match["number"].replace(",", ""))
    if coinsurance:
        value /= 100
        if value > 1:
            return dict(result, parse_status="needs_review")
    return {"amount": value, "after_deductible": (match["when"] or "").lower() == "after",
            "basis": (match["basis"] or "unspecified").lower(), "parse_status": "parsed"}


def prepare(archive_path, output_dir):
    report = {"source_archive": str(archive_path.resolve()),
              "source_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
              "inputs": {}, "limitations": [
                  "2026 catalog; questionnaire wording currently asks about 2027.",
                  "No ZIP/county availability or county-to-rating-area crosswalk in this branch.",
                  "No subsidy calculation, eligibility determination, claims, or suitability labels.",
                  "Benefit amounts are conditional; preserve raw text and explanation.",
              ]}
    with ZipFile(archive_path) as archive:
        source = {}
        for label, filename in FILES.items():
            with archive.open(filename) as file:
                data = pd.read_csv(file, dtype="string", keep_default_na=False, na_values=[""])
            count = len(data)
            data = data.drop_duplicates().reset_index(drop=True)
            report["inputs"][label] = {"rows": count, "exact_duplicates_removed": count - len(data)}
            source[label] = data

    plans = source["plans"][list(PLAN_FIELDS) + list(LIMITS)].rename(columns=PLAN_FIELDS | LIMITS).copy()
    rates = source["rates"][list(RATE_FIELDS)].rename(columns=RATE_FIELDS).copy()
    benefits = source["benefits"][list(BENEFIT_FIELDS) + list(COSTS)].rename(columns=BENEFIT_FIELDS).copy()
    for table in (plans, rates, benefits):
        table["plan_year"] = numeric(table["plan_year"], "plan_year").astype("Int64")
        table["state_code"] = table["state_code"].str.upper().str.strip()
    for col in PLAN_BOOLS:
        original = plans[col]
        plans[col] = boolean(original)
        if (original.notna() & plans[col].isna()).any():
            raise ValueError(f"Unrecognized boolean values in {col}")
    for col in LIMITS.values():
        plans[col] = numeric(plans[col], col)
    for col in ["non_tobacco_premium", "tobacco_premium"]:
        rates[col] = numeric(rates[col], col)
    for table, prefix in [(plans, "plan"), (rates, "rate")]:
        for suffix in ["effective_date", "expiration_date"]:
            col = f"{prefix}_{suffix}"
            table[col] = pd.to_datetime(table[col], format="%Y-%m-%d", errors="raise")
            if prefix == "rate" and table[col].isna().any():
                raise ValueError(f"Missing {col}")
        if table[f"{prefix}_effective_date"].gt(table[f"{prefix}_expiration_date"]).any():
            raise ValueError(f"Invalid {prefix} date intervals")
    unique(plans, KEY + ["variant_id"], "plan")
    unique(rates, KEY + ["base_plan_id", "rating_area_id", "age_label", "tobacco_category", "rate_effective_date", "rate_expiration_date"], "rate")
    unique(benefits, KEY + ["variant_id", "benefit_name"], "benefit")
    if (plans["variant_id"].str.slice(0, 14) != plans["base_plan_id"]).any():
        raise ValueError("Plan variant/base identifiers disagree")
    bounds = rates["age_label"].map(age_bounds)
    rates["min_age"] = pd.array([x[0] for x in bounds], dtype="Int64")
    rates["max_age"] = pd.array([x[1] for x in bounds], dtype="Int64")
    known_tobacco = {"No Preference", "Tobacco User/Non-Tobacco User"}
    if not set(rates["tobacco_category"].dropna()).issubset(known_tobacco):
        raise ValueError("Unsupported tobacco category")
    for col in ["covered", "excluded_from_in_network_moop"]:
        benefits[col] = boolean(benefits[col])
    report["cost_parsing"] = {}
    for raw, name in COSTS.items():
        parsed = pd.DataFrame([parse_cost(x, raw.startswith("Coins")) for x in benefits[raw]], index=benefits.index)
        parsed.columns = [f"{name}_{x}" for x in parsed.columns]
        parsed[f"{name}_amount"] = pd.to_numeric(parsed[f"{name}_amount"], errors="coerce").astype("Float64")
        parsed[f"{name}_after_deductible"] = parsed[f"{name}_after_deductible"].astype("boolean")
        benefits = pd.concat([benefits, parsed], axis=1)
        benefits = benefits.rename(columns={raw: f"{name}_raw"})
        report["cost_parsing"][name] = parsed[f"{name}_parse_status"].value_counts().to_dict()

    # Strict joins: unmatched keys stop preparation, rather than silently losing rows.
    plan_ids = plans[KEY + ["variant_id", "base_plan_id", "issuer_id"]]
    linked = benefits.merge(plan_ids, on=KEY + ["variant_id", "base_plan_id", "issuer_id"], how="left", indicator=True, validate="many_to_one")
    if linked["_merge"].ne("both").any():
        raise ValueError("Benefits reference unknown plan variants")
    base_ids = plans[KEY + ["base_plan_id", "issuer_id"]].drop_duplicates()
    linked = rates.merge(base_ids, on=KEY + ["base_plan_id", "issuer_id"], how="left", indicator=True, validate="many_to_one")
    if linked["_merge"].ne("both").any():
        raise ValueError("Rates reference unknown base plans")

    features = plans.copy()
    fields = ["covered", "in_network_copay_amount", "in_network_copay_after_deductible",
              "in_network_copay_parse_status", "in_network_copay_basis",
              "in_network_coinsurance_amount", "in_network_coinsurance_after_deductible",
              "in_network_coinsurance_parse_status", "out_of_network_coinsurance_amount",
              "out_of_network_coinsurance_parse_status"]
    for benefit, slug in SELECTED_BENEFITS.items():
        subset = benefits.loc[benefits["benefit_name"].eq(benefit), KEY + ["variant_id"] + fields]
        subset = subset.rename(columns={field: f"{slug}_{field}" for field in fields})
        features = features.merge(subset, on=KEY + ["variant_id"], how="left", validate="one_to_one")
    unique(features, KEY + ["variant_id"], "plan feature")
    report["outputs"] = {name: {"rows": len(table), "columns": len(table.columns)} for name, table in [("plans", plans), ("rates", rates), ("benefits", benefits), ("plan_features", features)]}
    report["plan_years"] = sorted(int(x) for x in plans["plan_year"].unique())
    report["missing_plan_features"] = {k: int(v) for k, v in features.isna().sum().items() if v}
    report["rates_zero_non_tobacco_premium"] = int(rates["non_tobacco_premium"].eq(0).sum())
    report["rates_9999_non_tobacco_premium"] = int(rates["non_tobacco_premium"].eq(9999).sum())
    report["rates_missing_tobacco_premium"] = int(rates["tobacco_premium"].isna().sum())
    output_dir.mkdir(parents=True, exist_ok=True)
    plans.to_csv(output_dir / "plans.csv", index=False)
    rates.to_csv(output_dir / "rates.csv.gz", index=False, compression="gzip")
    benefits.to_csv(output_dir / "benefits.csv.gz", index=False, compression="gzip")
    features.to_csv(output_dir / "plan_features.csv", index=False)
    (output_dir / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return features, rates, benefits, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/fl_cleaned_datasets_2026.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed")
    args = parser.parse_args()
    features, rates, _, report = prepare(args.archive, args.output)
    from recommender.features import build_candidates, model_matrix
    profiles = [
        {"profile_id": "example_budget", "age": 25, "smokes": False, "plan_year": 2026,
         "rating_area_id": "Rating Area 6", "monthly_budget": 500, "healthcare_usage": "Low",
         "priorities": ["Lower monthly premiums"], "referral_preference": "Not important", "out_network": "No"},
        {"profile_id": "example_protection", "age": 25, "smokes": False, "plan_year": 2026,
         "rating_area_id": "Rating Area 6", "monthly_budget": 750, "healthcare_usage": "High",
         "priorities": ["Protection against large medical bills"], "referral_preference": "Not important", "out_network": "No"},
    ]
    examples = pd.concat([build_candidates(features, rates, p) for p in profiles], ignore_index=True)
    examples.to_csv(args.output / "example_candidates.csv", index=False)
    matrix = model_matrix(examples)
    matrix.to_csv(args.output / "example_model_features.csv", index=False)
    examples[["profile_id", "variant_id"]].to_csv(args.output / "example_row_keys.csv", index=False)
    schema = {"row_keys": "example_row_keys.csv", "target": None,
              "categorical_columns": list(matrix.select_dtypes(include="category").columns),
              "columns": {name: str(dtype) for name, dtype in matrix.dtypes.items()},
              "notes": "No imputation/scaling fitted. Fit encoders/imputers on training profiles only; reuse their mappings at inference."}
    (args.output / "feature_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (args.output / "example_profiles.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "tables": report["outputs"],
                      "example_rows": len(examples)}, indent=2))


if __name__ == "__main__":
    main()
