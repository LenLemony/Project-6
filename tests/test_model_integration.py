from pathlib import Path

import pandas as pd

from preprocessing.prepare import ROOT
from recommender.inference import load_assets, recommend
from recommender.presentation import plan_cards


def answers(page=13):
    return {
        "page": page, "include_me": True, "include_partner": False,
        "include_dependents": False, "you_age": 25, "you_smoke": "No",
        "you_pregnant": "No", "monthly_budget": 750,
        "healthcare_usage": "Low - Mostly preventive care and occasional doctor visits",
        "priorities": ["Lower monthly premiums"], "referral_preference": "Not important",
        "out_network": "No", "is_dependent": "No", "married": "No",
        "has_dependents": "No", "income": 60000, "zip_code": "32816",
    }


def make_app(state):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app/app.py"))
    for key, value in state.items():
        app.session_state[key] = value
    return app.run(timeout=30)


def test_questionnaire_benefits_model_cards_and_live_budget():
    app = make_app(answers())
    next(b for b in app.button if b.label == "View Results →").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["page"] == 14
    next(b for b in app.button if b.label == "See Recommendations →").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["page"] == 15
    assert not app.exception and not app.warning
    assert not app.selectbox and not app.slider  # Check that the results page still uses the same layout.
    assert len(app.metric) == 15  # Each of the five plans shows three costs.
    assert len(app.subheader) == 5
    assert not any(item.value in {"Plan 1", "Plan 2", "Plan 3"} for item in app.subheader)

    from recommender.features import profile_from_answers
    profile = profile_from_answers(answers(), profile_id="test", rating_area_id="Rating Area 6", plan_year=2026)
    expected = recommend(profile, load_assets())
    assert [item.value for item in app.subheader] == expected.plan_name.tolist()
    assert any(item.label == "Individual maximum out-of-pocket" for item in app.metric)

    # Change the budget through the questionnaire and check the results again.
    app.session_state["page"] = 11
    app.run(timeout=30)
    app.slider(key="monthly_budget").set_value(0).run(timeout=30)
    app.session_state["page"] = 15
    app.run(timeout=30)
    assert not app.exception and not app.metric
    assert any("No matching plans" in item.value for item in app.info)

    app.button(key="recommendations_back").click().run(timeout=30)
    assert app.session_state["page"] == 14


def test_incomplete_household_answers_do_not_receive_single_person_quotes():
    state = answers(page=15)
    state["include_partner"] = True
    app = make_app(state)
    assert not app.exception and not app.metric
    assert any("Complete age" in item.value for item in app.warning)


def test_household_cards_use_family_limits_and_no_extra_controls():
    state = answers(page=15)
    state.update(include_partner=True, spouse_age=30, spouse_smoke="No", spouse_pregnant="Yes", monthly_budget=2000)
    app = make_app(state)
    assert not app.exception and not app.warning
    assert len(app.metric) == 15
    assert not app.selectbox and not app.slider
    assert any(item.label == "Household maximum out-of-pocket" for item in app.metric)


def test_missing_limits_and_referrals_are_not_zero_or_false():
    rows = pd.DataFrame([{
        "variant_id": "sample", "plan_name": "Example", "issuer_name": "Example issuer",
        "plan_type": "HMO", "metal_level": "Gold", "monthly_premium": 100.,
        "annual_premium": 1200., "deductible_individual": pd.NA,
        "moop_individual": float("nan"), "referral_required": pd.NA, "ranking_score": .3,
    }])
    card = plan_cards(rows)[0]
    assert card["deductible"] is None and card["moop"] is None
    assert card["referrals_required"] is None
    assert card["out_of_network_covered"] is None
