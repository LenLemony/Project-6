from pathlib import Path

import pandas as pd
import pytest

from preprocessing.prepare import ROOT, age_bounds, parse_cost, prepare
from recommender.features import build_candidates, load_catalog, model_matrix, profile_from_answers


@pytest.fixture(scope="module")
def catalog(tmp_path_factory):
    output = tmp_path_factory.mktemp("prepared")
    plans, rates, benefits, report = prepare(ROOT / "data/fl_cleaned_datasets_2026.zip", output)
    return plans, rates, benefits, report, output


@pytest.fixture
def profile():
    return {"profile_id": "test", "age": 25, "smokes": False, "plan_year": 2026,
            "rating_area_id": "Rating Area 6", "monthly_budget": 500,
            "healthcare_usage": "Low", "priorities": ["Lower monthly premiums"]}


def test_conditional_costs_and_prose_are_not_free_care():
    parsed = parse_cost("No Charge after deductible")
    assert parsed["amount"] == 0
    assert parsed["after_deductible"] is True
    assert parse_cost("40.00% Coinsurance after deductible", True)["amount"] == .4
    assert parse_cost("$250 per Day after deductible")["basis"] == "day"
    for text in ["Not Applicable", "$25 for the first 3 visits", pd.NA]:
        assert pd.isna(parse_cost(text)["amount"])


def test_source_counts_and_safe_benefit_join(catalog):
    plans, rates, benefits, report, _ = catalog
    assert (len(plans), len(rates), len(benefits)) == (2201, 567681, 154745)
    assert not plans.duplicated(["plan_year", "state_code", "variant_id"]).any()
    assert report["plan_years"] == [2026]
    assert plans["plan_expiration_date"].isna().any()
    assert not plans["plan_expiration_date"].eq(pd.Timestamp("2026-12-31")).all()


def test_known_real_plan_prices_and_benefit_conditions(catalog, profile):
    plans, rates, _, _, _ = catalog
    c = build_candidates(plans, rates, profile).set_index("variant_id")
    assert c.loc["21525FL0020004-01", "monthly_premium"] == 393.72
    assert c.loc["44228FL0040009-01", "annual_premium_plus_moop"] == pytest.approx(12549.44)
    assert c.loc["21525FL0020001-01", "primary_care_in_network_copay_amount"] == 50
    assert c.loc["21525FL0020004-01", "primary_care_in_network_coinsurance_after_deductible"]
    assert pd.isna(c.loc["21525FL0020004-01", "primary_care_in_network_copay_amount"])
    assert not c["geographic_availability_verified"].any()
    assert "target" not in c


def test_tobacco_price_uses_explicit_source_category(catalog, profile):
    plans, rates, _, _, _ = catalog
    c = build_candidates(plans, rates, dict(profile, smokes=True)).set_index("variant_id")
    assert c.loc["21525FL0020004-01", "monthly_premium"] == 413.4
    # This source category explicitly does not distinguish tobacco prices.
    assert c.loc["44228FL0040009-01", "monthly_premium"] == 629.12
    changed = rates.copy()
    changed.loc[changed.base_plan_id.eq("21525FL0020004"), "tobacco_premium"] = pd.NA
    c = build_candidates(plans, changed, dict(profile, smokes=True))
    assert not c.variant_id.eq("21525FL0020004-01").any()


@pytest.mark.parametrize("age,label", [(0, "0-14"), (14, "0-14"), (15, "15"), (64, "64 and over"), (70, "64 and over")])
def test_source_age_bands(catalog, profile, age, label):
    plans, rates, _, _, _ = catalog
    c = build_candidates(plans, rates, dict(profile, age=age))
    assert len(c)
    assert set(c.age_label) == {label}


def test_zero_budget_and_unknown_usage(catalog, profile):
    plans, rates, _, _, _ = catalog
    c = build_candidates(plans, rates, dict(profile, monthly_budget=0, healthcare_usage="Not sure"))
    assert c.premium_to_budget.isna().all()
    assert not c.within_budget.any()
    assert set(c.healthcare_usage) == {"Not sure"}
    x = model_matrix(c)
    assert x.premium_to_budget.isna().all()
    assert not {"variant_id", "profile_id", "plan_name", "sbc_url", "target"} & set(x.columns)


def test_reject_wrong_year_overlapping_rates_and_households(catalog, profile):
    plans, rates, _, _, _ = catalog
    with pytest.raises(ValueError, match="year"):
        build_candidates(plans, rates, dict(profile, plan_year=2027))
    with pytest.raises(ValueError, match="Multiple active rates"):
        build_candidates(plans, pd.concat([rates, rates], ignore_index=True), profile)
    with pytest.raises(ValueError, match="one applicant"):
        profile_from_answers({"include_me": True, "include_partner": True}, profile_id="x", rating_area_id="Rating Area 6", plan_year=2026)


def test_saved_catalog_round_trip(catalog, profile):
    plans, rates, _, _, output = catalog
    loaded_plans, loaded_rates = load_catalog(Path(output))
    before = build_candidates(plans, rates, profile)
    after = build_candidates(loaded_plans, loaded_rates, profile)
    pd.testing.assert_frame_equal(before, after, check_dtype=False)
