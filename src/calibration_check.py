"""
Calibration check — closes a real, honestly-named gap: we report
probabilities (e.g. "fraud-risk 0.73") but never verified they mean what
they claim to mean.

Calibration asks: among all the transactions the model scored around
0.7, did roughly 70% of them actually turn out to be fraud? If yes, the
model is "calibrated" — its numbers are trustworthy on their own terms,
not just useful for ranking. If a "0.9" transaction is only fraud 40% of
the time in reality, the model is directionally useful but the number
itself is misleading — dangerous if anyone downstream treats 0.9 as "90%
confident."

We check this with two standard tools:
  - A reliability diagram (bin predictions, compare mean predicted prob
    to actual fraud rate in each bin)
  - Brier score (lower is better — the standard scalar summary of
    calibration + accuracy combined)
Then we fit a calibrated version (Platt scaling / sigmoid) and check
honestly whether it actually improves calibration, the same way we
checked whether the interaction feature actually helped — by measuring,
not assuming.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss
from sklearn.linear_model import LogisticRegression

from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
global_fraud_rate = train_df["is_fraud"].mean()
for d in (train_df, test_df):
    d["is_cod"] = (d["payment_mode"] == "COD").astype(int)
    d["is_new_agent"] = (d["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
    d["high_value"] = (d["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
    d["cod_and_high_value"] = d["is_cod"] * d["high_value"]
train_df = train_df.copy()
test_df = test_df.copy()
train_df["pincode_return_rate"] = train_df["pincode"].map(pincode_rate_map)
test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

FEATURES = FRAUD_FEATURES

# --- the EXISTING deployed model, as-is ---
model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
X_test_scaled = scaler.transform(test_df[FEATURES])
y_test = test_df["is_fraud"]
y_proba_uncalibrated = model.predict_proba(X_test_scaled)[:, 1]


def reliability_table(y_true, y_proba, n_bins=10):
    """Bins predictions and compares mean predicted prob vs actual rate
    in each bin — the core reliability-diagram data, printed as a table
    since we don't have a plotting surface here."""
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.digitize(y_proba, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        rows.append({
            "bin": f"{bins[b]:.1f}-{bins[b+1]:.1f}",
            "count": int(mask.sum()),
            "mean_predicted": round(float(y_proba[mask].mean()), 3),
            "actual_fraud_rate": round(float(y_true[mask].mean()), 3),
        })
    return pd.DataFrame(rows)


print("=== CALIBRATION CHECK — existing (uncalibrated) model ===\n")
table_before = reliability_table(y_test.values, y_proba_uncalibrated)
print(table_before.to_string(index=False))
brier_before = brier_score_loss(y_test, y_proba_uncalibrated)
print(f"\nBrier score (lower is better, 0=perfect): {brier_before:.4f}")
gap = (table_before["mean_predicted"] - table_before["actual_fraud_rate"]).abs().mean()
print(f"Mean absolute gap between predicted and actual (average across bins): {gap:.3f}")

# --- fit a calibrated version and check honestly if it actually helps ---
X_train_scaled = scaler.transform(train_df[FEATURES])
y_train = train_df["is_fraud"]

base_model = LogisticRegression(class_weight="balanced", random_state=42, C=0.1, max_iter=1000)
calibrated_model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
calibrated_model.fit(X_train_scaled, y_train)
y_proba_calibrated = calibrated_model.predict_proba(X_test_scaled)[:, 1]

print("\n=== CALIBRATION CHECK — after Platt scaling (sigmoid calibration) ===\n")
table_after = reliability_table(y_test.values, y_proba_calibrated)
print(table_after.to_string(index=False))
brier_after = brier_score_loss(y_test, y_proba_calibrated)
print(f"\nBrier score: {brier_after:.4f}  (before: {brier_before:.4f})")
gap_after = (table_after["mean_predicted"] - table_after["actual_fraud_rate"]).abs().mean()
print(f"Mean absolute gap: {gap_after:.3f}  (before: {gap:.3f})")

print("\n=== Verdict ===")
if brier_after < brier_before:
    print(f"Calibration genuinely improved (Brier {brier_before:.4f} -> {brier_after:.4f}).")
    print("Saving calibrated model as an alternative artifact — NOT replacing the")
    print("production model automatically, since that decision needs the same")
    print("scrutiny as any other model change, not an automatic swap.")
    joblib.dump(calibrated_model, f"{BASE_DIR}/models/fraud_model_calibrated.pkl")
else:
    print(f"Calibration did NOT clearly improve here (Brier {brier_before:.4f} vs {brier_after:.4f}).")
    print("Reporting this honestly rather than claiming a fix that didn't help.")
