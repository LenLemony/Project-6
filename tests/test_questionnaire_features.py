import pandas as pd
import pytest

from preprocessing.prepare import ROOT
from preprocessing.labeled_dataset import synthetic_labels
from recommender.features import load_catalog, build_candidates, profile_from_answers


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(ROOT / "data/processed")


def profile(members):
    return {"profile_id": "test", "age": members[0]["age"], "smokes": members[0]["smokes"],
            "applicants": members, "plan_year": 2026, "rating_area_id": "Rating Area 6",
            "monthly_budget": 10000, "healthcare_usage": "High",
            "priorities": ["Lower costs when receiving care"],
            "referral_preference": "Very important", "out_network": "Yes"}


def person(age, role="dependent", pregnancy="No", smokes=False):
    return {"age": age, "role": role, "pregnancy": pregnancy, "smokes": smokes}


def test_household_sum_and_three_child_cap(catalog):
    plans, rates = catalog
    people = [person(25, "self"), person(30, "partner"), person(8), person(12), person(15), person(17)]
    c = build_candidates(plans, rates, profile(people)).set_index("variant_id")
    variant = "21525FL0020001-01"
    expected = sum(build_candidates(plans, rates, profile([people[i]])).set_index("variant_id").loc[variant, "monthly_premium"] for i in [0, 1, 3, 4, 5])
    assert c.loc[variant, "monthly_premium"] == pytest.approx(expected)
    assert c.loc[variant, "covered_people"] == 6
    assert c.loc[variant, "billed_people"] == 5
    assert c.loc[variant, "deductible_individual"] == c.loc[variant, "integrated_deductible_family_group"]
    assert c.loc[variant, "moop_individual"] == c.loc[variant, "integrated_moop_family_group"]


def test_pregnancy_and_tax_context_do_not_change_published_premiums(catalog):
    plans, rates = catalog
    no = build_candidates(plans, rates, profile([person(25, "self")]))
    yes = build_candidates(plans, rates, profile([person(25, "self", pregnancy="Yes")]))
    pd.testing.assert_series_equal(no.monthly_premium, yes.monthly_premium)
    assert yes.pregnancy_count.eq(1).all()
    assert no.pregnancy_count.eq(0).all()
    assert (synthetic_labels(yes).rule_loss.to_numpy() >= synthetic_labels(no).rule_loss.to_numpy()).all()


def test_partner_only_and_dependent_answers_preserve_unknowns():
    answers = {"include_me": False, "include_partner": True, "include_dependents": True,
               "spouse_age": 30, "spouse_smoke": "No", "spouse_pregnant": "Prefer not to say",
               "total_dependents": 1, "dependent_0_age": 0, "dependent_0_smoke": "No",
               "dependent_0_pregnant": "No", "monthly_budget": 1000,
               "healthcare_usage": "Not sure", "priorities": ["More freedom to choose doctors"],
               "referral_preference": "Somewhat important", "out_network": "Not sure",
               "zip_code": "32816", "is_dependent": "Not Sure", "income": 50000, "jointly": "Not Sure"}
    p = profile_from_answers(answers, profile_id="test", rating_area_id="Rating Area 6", plan_year=2026)
    assert p["applicants"][0]["pregnancy"] == "Prefer not to say"
    assert p["applicants"][1]["age"] == 0
    assert p["questionnaire_context"]["is_dependent"] == "Not Sure"
    assert p["questionnaire_context"]["income"] == 50000


def test_network_answer_changes_preference_rule(catalog):
    plans, rates = catalog
    p = profile([person(25, "self")])
    yes = synthetic_labels(build_candidates(plans, rates, p))
    no = synthetic_labels(build_candidates(plans, rates, dict(p, out_network="No")))
    assert (yes.rule_loss.to_numpy() >= no.rule_loss.to_numpy()).all()
    assert (yes.rule_loss.to_numpy() > no.rule_loss.to_numpy()).any()
