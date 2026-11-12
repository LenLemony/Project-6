"""Local integration check with the exported model and prepared catalog."""

from pathlib import Path

import pytest

from preprocessing.prepare import ROOT


@pytest.mark.skipif(not (ROOT / "models/feature_schema.json").exists(), reason="Exported model/schema required")
def test_last_next_renders_results_and_budget_change_updates_them():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "app/app.py"))
    answers = {
        "page": 13, "include_me": True, "include_partner": False,
        "include_dependents": False, "you_age": 25, "you_smoke": "No",
        "monthly_budget": 750,
        "healthcare_usage": "Low - Mostly preventive care and occasional doctor visits",
        "priorities": ["Lower monthly premiums"], "referral_preference": "Not important",
    }
    for key, value in answers.items():
        app.session_state[key] = value
    app.run(timeout=30)
    app.radio[0].set_value("No").run(timeout=30)
    next(button for button in app.button if button.label == "Next →").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["page"] == 14
    assert app.title[0].value == "Your top five plan comparisons"
    assert len(app.dataframe) == 1
    assert 0 < len(app.dataframe[0].value) <= 5
    assert app.dataframe[0].value.monthly_premium.le(750).all()

    app.slider(key="results_budget").set_value(0).run(timeout=15)
    assert not app.exception
    assert not app.dataframe
    assert any("No matching plans" in message.value for message in app.info)
