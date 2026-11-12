import json

import pandas as pd
import pytest

from preprocessing.labeled_dataset import (
    assign_splits, create_dataset, generate_profiles, load_split, ranking_group_sizes, synthetic_labels,
)
from preprocessing.prepare import ROOT


def test_profile_generation_is_reproducible_and_unique():
    profiles = generate_profiles(30, ["Rating Area 6"], 42)
    assert profiles == generate_profiles(30, ["Rating Area 6"], 42)
    signatures = [{k: v for k, v in p.items() if k != "profile_id"} for p in profiles]
    assert len({json.dumps(p, sort_keys=True) for p in signatures}) == 30
    mapping = assign_splits([p["profile_id"] for p in profiles], 42)
    assert pd.Series(mapping).value_counts().to_dict() == {"train": 18, "validation": 6, "test": 6}


def test_rule_penalizes_budget_overrun_and_preserves_ties():
    c = pd.DataFrame({
        "monthly_premium": [200., 200., 300., 400., 500., 600.],
        "deductible_individual": [1000.] * 6, "moop_individual": [5000.] * 6,
        "healthcare_usage": ["Low"] * 6, "priority_premium": [True] * 6,
        "priority_care_cost": [False] * 6, "priority_protection": [False] * 6,
        "referral_preference": ["Not important"] * 6,
        "referral_required": [False] * 6, "monthly_budget": [350.] * 6,
    })
    c["annual_premium_plus_moop"] = c.monthly_premium * 12 + c.moop_individual
    labeled = synthetic_labels(c)
    assert labeled.rule_loss.is_monotonic_increasing
    assert labeled.relevance.is_monotonic_decreasing
    assert labeled.loc[0, "relevance"] == labeled.loc[1, "relevance"]
    assert not labeled.human_reviewed.any()
    assert labeled.label_source.str.startswith("synthetic_").all()
    c.loc[0, "deductible_individual"] = float("nan")
    assert len(synthetic_labels(c)) == 5  # Missing limit is not a zero-cost label.


@pytest.fixture(scope="module")
def labeled(tmp_path_factory):
    output = tmp_path_factory.mktemp("labeled")
    manifest = create_dataset(ROOT / "data/processed", output, count=10, seed=77)
    return output, manifest


def test_split_integrity_and_lightgbm_input_contract(labeled):
    output, manifest = labeled
    ids = []
    for split in ["train", "validation", "test"]:
        x, y, groups, cats = load_split(output, split)
        assert len(x) == len(y) == len(groups) > 0
        assert y.between(0, 4).all()
        assert not {"relevance", "rule_loss", "profile_id", "variant_id", "label_source", "split"} & set(x)
        assert all(isinstance(x[col].dtype, pd.CategoricalDtype) for col in cats)
        sizes = ranking_group_sizes(groups)
        assert sizes.sum() == len(x)
        assert len(sizes) == groups.nunique()
        assert groups.is_monotonic_increasing  # Each group occupies a contiguous block.
        assert groups.nunique() == manifest["splits"][split]["profiles"]
        ids.append(set(groups))
    assert not ids[0] & ids[1] and not ids[0] & ids[2] and not ids[1] & ids[2]
    train, _, _, cats = load_split(output, "train")
    valid, _, _, _ = load_split(output, "validation")
    for col in cats:
        assert train[col].cat.categories.equals(valid[col].cat.categories)


def test_lightgbm_group_sizes_reject_interleaved_groups():
    assert ranking_group_sizes(["a", "a", "b"]).tolist() == [2, 1]
    with pytest.raises(ValueError, match="contiguous"):
        ranking_group_sizes(["a", "b", "a"])


def test_invalid_split_rejected(labeled):
    with pytest.raises(ValueError, match="Unknown split"):
        load_split(labeled[0], "other")
