#Train and check the 2026 ranker using the example questionnaire answers."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score

from preprocessing.prepare import ROOT
from preprocessing.labeled_dataset import create_dataset, load_split, ranking_group_sizes


def grouped_ndcg(y, predictions, ids):
    scores = []
    for positions in pd.Series(ids).reset_index(drop=True).groupby(list(ids), sort=False).indices.values():
        gains = np.exp2(np.asarray(y)[positions]) - 1
        scores.append(ndcg_score(gains.reshape(1, -1), np.asarray(predictions)[positions].reshape(1, -1), k=5))
    return float(np.mean(scores))


def train(profiles=600):
    data = ROOT / "data/processed/labeled_synthetic"
    manifest = create_dataset(ROOT / "data/processed", data, count=profiles, seed=2026)
    xt, yt, gt, cats = load_split(data, "train")
    xv, yv, gv, _ = load_split(data, "validation")
    xs, ys, gs, _ = load_split(data, "test")
    model = lgb.LGBMRanker(objective="lambdarank", n_estimators=300, num_leaves=31,
                           learning_rate=.05, random_state=2026, n_jobs=4, verbosity=-1)
    model.fit(xt, yt, group=ranking_group_sizes(gt), eval_X=xv, eval_y=yv,
              eval_group=[ranking_group_sizes(gv)], eval_metric="ndcg", eval_at=[5],
              categorical_feature=cats, callbacks=[lgb.early_stopping(30, verbose=False)])
    report = {"version": "questionnaire_v2", "coverage_year": 2026,
              "label_source": manifest["label_source"], "features": len(xt.columns),
              "best_iteration": model.best_iteration_, "profiles": manifest["included_profiles"],
              "splits": manifest["splits"],
              "validation_ndcg_at_5": grouped_ndcg(yv, model.predict(xv), gv),
              "test_ndcg_at_5": grouped_ndcg(ys, model.predict(xs), gs),
              "test_premium_baseline_ndcg_at_5": grouped_ndcg(ys, -xs.monthly_premium.to_numpy(), gs),
              "interpretation": "Agreement with synthetic preference labels, not insurance recommendation accuracy.",
              "unsupported": ["ZIP-to-county availability mapping", "subsidy amounts and final eligibility", "named provider/drug verification"],
              "top_features": dict(sorted(zip(xt.columns, model.booster_.feature_importance(importance_type="gain").tolist()), key=lambda x: -x[1])[:15])}
    schema = {"columns": xt.columns.tolist(), "categories": {col: xt[col].cat.categories.tolist() for col in cats},
              "version": "questionnaire_v2", "plan_year": 2026}
    folder = ROOT / "models"
    archive = folder / "archive" / datetime.now(timezone.utc).strftime("before-publish-%Y%m%dT%H%M%S%fZ")
    archive.mkdir(parents=True, exist_ok=False)
    for name in ["insurance_ranker.txt", "feature_schema.json", "training_report.json"]:
        if (folder / name).exists():
            shutil.copy2(folder / name, archive / name)
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        staging = Path(temporary)
        model.booster_.save_model(staging / "insurance_ranker.txt")
        (staging / "feature_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
        (staging / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        for name in ["insurance_ranker.txt", "feature_schema.json", "training_report.json"]:
            (staging / name).replace(folder / name)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=int, default=600)
    train(parser.parse_args().profiles)
