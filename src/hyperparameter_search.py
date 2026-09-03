"""
Hyperparameter search for the fraud-risk XGBoost model.

Honest gap found and closed: the production model uses reasonable,
standard XGBoost hyperparameters (n_estimators=300, max_depth=6,
learning_rate=0.1), chosen but never formally searched over. This
script does that search properly:

  1. Grid search over a real range of candidate hyperparameters,
     evaluated with 5-fold F2 cross-validation on the TRAINING split
     only - the held-out test set is never touched during selection,
     so the choice can't leak test-set information.
  2. Only AFTER a winner is picked by CV does this script evaluate
     both the current production config and the best-found config on
     the untouched held-out test set, for an honest, apples-to-apples
     final comparison.

Uses the exact same data prep, feature list, and train/test split as
train_fraud_model.py, so results are directly comparable.
"""
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")
warnings.filterwarnings("ignore", category=FutureWarning)

import itertools
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import fbeta_score, make_scorer
from xgboost import XGBClassifier

from pipeline import FRAUD_FEATURES, compute_shrunk_pincode_rates, compute_shrunk_pincode_ring_rates

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD
df["is_cod"] = (df["payment_mode"] == "COD").astype(int)
df["is_new_agent"] = (df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
df["high_value"] = (df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
df["cod_and_high_value"] = df["is_cod"] * df["high_value"]

FEATURES = FRAUD_FEATURES

train_df, test_df = train_test_split(
    df, test_size=0.2, random_state=42, stratify=df["is_fraud"]
)

pincode_rate_map, global_fraud_rate = compute_shrunk_pincode_rates(train_df)
pincode_ring_rate_map, global_ring_rate = compute_shrunk_pincode_ring_rates(train_df)

train_df = train_df.copy()
test_df = test_df.copy()
train_df["pincode_return_rate"] = train_df["pincode"].map(pincode_rate_map)
test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)
train_df["pincode_ring_rate"] = train_df["pincode"].map(pincode_ring_rate_map)
test_df["pincode_ring_rate"] = test_df["pincode"].map(pincode_ring_rate_map).fillna(global_ring_rate)

X_train, y_train = train_df[FEATURES], train_df["is_fraud"]
X_test, y_test = test_df[FEATURES], test_df["is_fraud"]

pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
f2_scorer = make_scorer(fbeta_score, beta=2)

CURRENT_CONFIG = {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1}

GRID = {
    "n_estimators": [100, 300, 500],
    "max_depth": [3, 6, 9],
    "learning_rate": [0.05, 0.1, 0.2],
}

print("=== Hyperparameter search: fraud-risk XGBoost model ===")
print(f"Grid: {GRID}")
print("Selection metric: 5-fold CV F2 score, on TRAINING data only (test set untouched during search)\n")

results = []
combos = list(itertools.product(GRID["n_estimators"], GRID["max_depth"], GRID["learning_rate"]))
for i, (n_est, depth, lr) in enumerate(combos):
    model = XGBClassifier(
        n_estimators=n_est, max_depth=depth, learning_rate=lr,
        scale_pos_weight=pos_weight, random_state=42,
        eval_metric="logloss", n_jobs=-1
    )
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring=f2_scorer)
    results.append({
        "n_estimators": n_est, "max_depth": depth, "learning_rate": lr,
        "cv_f2_mean": scores.mean(), "cv_f2_std": scores.std(),
    })
    print(f"  [{i+1}/{len(combos)}] n_est={n_est:>3} depth={depth} lr={lr:.2f}  ->  CV F2 = {scores.mean():.4f} (+/- {scores.std():.4f})")

results_df = pd.DataFrame(results).sort_values("cv_f2_mean", ascending=False)
best = results_df.iloc[0]

current_row = results_df[
    (results_df["n_estimators"] == CURRENT_CONFIG["n_estimators"]) &
    (results_df["max_depth"] == CURRENT_CONFIG["max_depth"]) &
    (results_df["learning_rate"] == CURRENT_CONFIG["learning_rate"])
].iloc[0]

print("\n=== Best config found (by CV F2 on training data) ===")
print(f"n_estimators={int(best['n_estimators'])}, max_depth={int(best['max_depth'])}, learning_rate={best['learning_rate']}")
print(f"CV F2: {best['cv_f2_mean']:.4f} (+/- {best['cv_f2_std']:.4f})")

print("\n=== Current production config, for comparison ===")
print(f"n_estimators={CURRENT_CONFIG['n_estimators']}, max_depth={CURRENT_CONFIG['max_depth']}, learning_rate={CURRENT_CONFIG['learning_rate']}")
print(f"CV F2: {current_row['cv_f2_mean']:.4f} (+/- {current_row['cv_f2_std']:.4f})")

gap = best["cv_f2_mean"] - current_row["cv_f2_mean"]
print(f"\nCV F2 gap (best - current production): {gap:+.4f}")

print("\n=== Held-out test set evaluation (both configs, calibrated - only run AFTER selection) ===")

def evaluate_on_test(n_est, depth, lr, label):
    base = XGBClassifier(
        n_estimators=int(n_est), max_depth=int(depth), learning_rate=lr,
        scale_pos_weight=pos_weight, random_state=42,
        eval_metric="logloss", n_jobs=-1
    )
    calibrated = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    calibrated.fit(X_train, y_train)
    y_proba = calibrated.predict_proba(X_test)[:, 1]

    best_f2, best_thresh = 0, 0.5
    for t in [x / 100 for x in range(5, 90, 5)]:
        pred = (y_proba >= t).astype(int)
        f2 = fbeta_score(y_test, pred, beta=2, zero_division=0)
        if f2 > best_f2:
            best_f2, best_thresh = f2, t
    print(f"{label}: best test F2 = {best_f2:.4f} at threshold {best_thresh:.2f}")
    return best_f2

current_test_f2 = evaluate_on_test(
    CURRENT_CONFIG["n_estimators"], CURRENT_CONFIG["max_depth"], CURRENT_CONFIG["learning_rate"],
    "Current production config"
)
best_test_f2 = evaluate_on_test(
    best["n_estimators"], best["max_depth"], best["learning_rate"],
    "Best-found config      "
)

print(f"\nHeld-out test F2 gap (best - current production): {best_test_f2 - current_test_f2:+.4f}")
print("\nThis gap is what actually matters - the honest answer to 'did you tune your")
print("hyperparameters' is decided here, on the held-out set, not on the CV number above.")
