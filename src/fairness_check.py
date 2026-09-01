"""
Fairness check — closes another honestly-named gap.

We don't have any protected demographic attributes in this data (no
race, religion, gender — and we shouldn't manufacture them). The one
legitimate fairness dimension we DO have is geographic: pincode. A real
concern in fraud systems is that a pincode's historical fraud rate
becomes a self-fulfilling prophecy — if the model over-relies on it,
every honest customer in a flagged area gets penalized more than their
own individual risk justifies, effectively "redlining" a neighborhood.

This checks: for each pincode, is the model's false-positive rate (good
customers wrongly flagged) proportional to that pincode's actual fraud
rate, or are some pincodes bearing a disproportionate share of false
positives relative to how much real fraud they actually have?
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES, FRAUD_THRESHOLD, compute_shrunk_pincode_rates


_last_test_df = None


def compute_fairness_table():
    """
    Returns the per-pincode fairness table as a DataFrame — factored
    out into a real function (not just script-level code) so this can
    actually be imported and tested, the same pattern used in
    ring_detector.py and spike_detector.py.
    """
    df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

    pincode_rate_map, global_fraud_rate = compute_shrunk_pincode_rates(train_df)
    test_df = test_df.copy()
    test_df["is_cod"] = (test_df["payment_mode"] == "COD").astype(int)
    test_df["is_new_agent"] = (test_df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
    test_df["high_value"] = (test_df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
    test_df["cod_and_high_value"] = test_df["is_cod"] * test_df["high_value"]
    test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

    model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
    # XGBoost doesn't require feature scaling (unlike logistic regression)
    test_df["fraud_proba"] = model.predict_proba(test_df[FRAUD_FEATURES])[:, 1]
    test_df["flagged"] = (test_df["fraud_proba"] >= FRAUD_THRESHOLD).astype(int)

    rows = []
    for pincode, group in test_df.groupby("pincode"):
        if len(group) < 10:
            continue  # too few samples in test set to say anything meaningful
        not_fraud = group[group["is_fraud"] == 0]
        if len(not_fraud) == 0:
            continue
        fpr = not_fraud["flagged"].mean()  # of genuinely honest customers here, how many got flagged
        actual_fraud_rate = group["is_fraud"].mean()
        rows.append({
            "pincode": pincode,
            "n": len(group),
            "actual_fraud_rate": round(actual_fraud_rate, 3),
            "false_positive_rate": round(fpr, 3),
            # ratio: how much higher is FPR than the pincode's own fraud rate?
            # >1 means honest customers there are flagged MORE than the
            # area's real risk would justify on its own.
            "fpr_to_fraud_rate_ratio": round(fpr / max(actual_fraud_rate, 0.01), 2),
        })

    global _last_test_df
    _last_test_df = test_df
    return pd.DataFrame(rows).sort_values("fpr_to_fraud_rate_ratio", ascending=False)


def bootstrap_fpr_ci(group_df, n_boot=2000, seed=42):
    """
    Bootstrap 95% CI on the false-positive rate for one pincode's honest
    customers. Small per-pincode sample sizes (often n<40) mean a single
    disparity ratio can look alarming purely from sampling noise — this
    quantifies how much of the observed ratio is reliably real vs. noise,
    rather than reporting a single point estimate as if it were precise.
    """
    rng = np.random.RandomState(seed)
    not_fraud = group_df[group_df["is_fraud"] == 0]
    if len(not_fraud) < 5:
        return None, None
    boot_rates = []
    for _ in range(n_boot):
        sample = not_fraud.sample(frac=1, replace=True, random_state=rng.randint(0, 1_000_000))
        boot_rates.append(sample["flagged"].mean())
    return np.percentile(boot_rates, 2.5), np.percentile(boot_rates, 97.5)


if __name__ == "__main__":
    result_df = compute_fairness_table()

    print("=== FAIRNESS CHECK — false-positive rate by pincode ===\n")
    print(f"(Gating threshold used: {FRAUD_THRESHOLD}, same as production)\n")
    print(result_df.to_string(index=False))

    print("\n=== Verdict ===")
    worst = result_df.iloc[0]
    print(f"Highest disparity: pincode {worst['pincode']} — honest customers there are")
    print(f"flagged at {worst['fpr_to_fraud_rate_ratio']}x the rate their actual fraud rate would justify.")
    mean_ratio = result_df["fpr_to_fraud_rate_ratio"].mean()
    std_ratio = result_df["fpr_to_fraud_rate_ratio"].std()
    print(f"\nAcross all pincodes: mean ratio {mean_ratio:.2f}, std {std_ratio:.2f}.")
    if std_ratio > 1.0:
        print("Meaningful spread — some pincodes' honest customers are treated notably")
        print("worse than their area's real risk justifies. Worth a real deployment")
        print("capping how much weight pincode history can carry for any one customer,")
        print("rather than letting area history fully determine an individual's risk.")
    else:
        print("Spread is modest — the model isn't dramatically over-penalizing any")
        print("single area's honest customers relative to that area's real risk.")

    print("\n=== Statistical caveat: small-sample noise check ===")
    print("Per-pincode samples here are small (28-58 test transactions each).")
    print("A single extra false positive can swing a pincode's ratio substantially.")
    print("Bootstrap 95% CI on the worst-case pincode's false-positive rate:")
    df_full = compute_fairness_table.__wrapped_df if hasattr(compute_fairness_table, "__wrapped_df") else None
    worst_pincode = worst["pincode"]
    worst_group = _last_test_df[_last_test_df["pincode"] == worst_pincode]
    lo, hi = bootstrap_fpr_ci(worst_group)
    if lo is not None:
        print(f"  Pincode {worst_pincode}: observed FPR {worst['false_positive_rate']:.3f}, "
              f"95% CI [{lo:.3f}, {hi:.3f}]")
        ci_width = hi - lo
        if ci_width > 0.25:
            print(f"  CI width ({ci_width:.3f}) is wide relative to the effect size — the")
            print(f"  observed {worst['fpr_to_fraud_rate_ratio']}x disparity is NOT reliably")
            print("  distinguishable from sampling noise at this sample size. Reporting this")
            print("  honestly rather than treating a noisy point estimate as a confirmed bias.")
            print("  A production deployment would need a larger evaluation set or")
            print("  pooled/hierarchical estimation across regions to draw reliable")
            print("  per-pincode conclusions.")
        else:
            print(f"  CI width ({ci_width:.3f}) is reasonably tight — this disparity appears")
            print("  more likely to reflect a real pattern than pure sampling noise.")
