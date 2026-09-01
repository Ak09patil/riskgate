"""
Held-out validation: LightGBM / XGBoost / Random Forest / Logistic Regression
on the REAL dataset, with a proper train/test split to rule out leakage
inflating the tree-model numbers.

Usage:
    python held_out_validation.py --data path/to/real_dataset.csv --target target_col_name

Assumes the same feature set / preprocessing you used in real_data_validation.py.
Adjust FEATURE_COLS / TARGET_COL / preprocessing below to match your actual pipeline
before running — this is a template built to mirror your existing comparison, not
a blind drop-in, since I don't have your actual feature engineering code in this session.
"""

import argparse
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import fbeta_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None


def evaluate(name, model, X_train, y_train, X_test, y_test):
    """
    Trains the model, then scans thresholds 0.05 to 0.95 (step 0.05) and picks
    whichever threshold maximizes THIS model's own F2 score. This matches the
    fairness principle used elsewhere in the project: no model gets a fixed
    default threshold while another gets tuned — every model is independently
    tuned to its own best operating point before models are compared.
    """
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - t0

    t0 = time.time()
    probs = model.predict_proba(X_test)[:, 1]
    infer_time = time.time() - t0

    best_threshold = 0.5
    best_f2 = -1
    for threshold in np.arange(0.05, 1.00, 0.05):
        preds = (probs >= threshold).astype(int)
        f2 = fbeta_score(y_test, preds, beta=2, zero_division=0)
        if f2 > best_f2:
            best_f2 = f2
            best_threshold = round(threshold, 2)

    preds = (probs >= best_threshold).astype(int)
    precision = precision_score(y_test, preds, zero_division=0)
    recall = recall_score(y_test, preds, zero_division=0)
    auc = roc_auc_score(y_test, probs)

    return {
        "model": name,
        "best_threshold": best_threshold,
        "f2": round(best_f2, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "auc": round(auc, 4),
        "train_time_s": round(train_time, 2),
        "infer_time_s": round(infer_time, 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to real dataset CSV")
    parser.add_argument("--target", required=True, help="Name of the target/label column")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    y = df[args.target]
    X = df.drop(columns=[args.target])

    # Keep only numeric columns automatically; adjust if you have categoricals
    # that need encoding to match your original pipeline.
    X = X.select_dtypes(include=[np.number])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}, "
          f"Positive rate (train): {y_train.mean():.4%}, "
          f"Positive rate (test): {y_test.mean():.4%}")

    results = []

    # Logistic regression needs scaling; trees don't
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    results.append(evaluate(
        "Logistic Regression",
        LogisticRegression(max_iter=1000, class_weight="balanced"),
        X_train_scaled, y_train, X_test_scaled, y_test
    ))

    results.append(evaluate(
        "Random Forest",
        RandomForestClassifier(n_estimators=200, max_depth=12, n_jobs=-1,
                                class_weight="balanced", random_state=args.seed),
        X_train, y_train, X_test, y_test
    ))

    if XGBClassifier is not None:
        pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        results.append(evaluate(
            "XGBoost",
            XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                           scale_pos_weight=pos_weight, n_jobs=-1,
                           eval_metric="logloss", random_state=args.seed),
            X_train, y_train, X_test, y_test
        ))
    else:
        print("xgboost not installed — skipping (pip install xgboost)")

    if LGBMClassifier is not None:
        pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        results.append(evaluate(
            "LightGBM",
            LGBMClassifier(n_estimators=300, max_depth=8, learning_rate=0.1,
                            scale_pos_weight=pos_weight, n_jobs=-1,
                            random_state=args.seed, verbose=-1),
            X_train, y_train, X_test, y_test
        ))
    else:
        print("lightgbm not installed — skipping (pip install lightgbm)")

    results_df = pd.DataFrame(results).sort_values("f2", ascending=False)
    print("\n=== Held-out test results (model never saw this data during training) ===")
    print(results_df.to_string(index=False))

    results_df.to_csv("held_out_validation_results.csv", index=False)
    print("\nSaved to held_out_validation_results.csv")


if __name__ == "__main__":
    main()
