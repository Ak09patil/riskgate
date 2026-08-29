"""
Cost-sensitivity table — turns the precision/recall tradeoff into
something skimmable in five seconds: at each threshold, how many
transactions get held vs how much fraud gets missed, extrapolated to a
realistic daily volume.

This does NOT claim our synthetic numbers predict real-world performance
at scale — see README's "Cost at real scale" section for that caveat.
This table exists to make the OPERATIONAL TRADEOFF concrete and readable,
not to claim precision at production volume.
"""

import pandas as pd
import joblib

# Same fix as drift_test.py / train_fraud_model.py — see there for why.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score

# illustrative daily volume — NOT a claim about Razorpay's real agent-txn
# volume, just large enough to make percentage-point differences concrete
ILLUSTRATIVE_DAILY_VOLUME = 1_000_000

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
global_fraud_rate = train_df["is_fraud"].mean()
test_df = test_df.copy()
test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)
test_df["is_cod"] = (test_df["payment_mode"] == "COD").astype(int)
test_df["is_new_agent"] = (test_df["agent_age_days"] < 15).astype(int)
test_df["high_value"] = (test_df["order_value"] > 5000).astype(int)

FEATURES = [
    "device_ip_consistency", "is_cod", "pincode_return_rate",
    "is_new_agent", "high_value", "agent_age_days", "order_value",
    "user_account_age_days",
]
model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
X_test_scaled = scaler.transform(test_df[FEATURES])
y_test = test_df["is_fraud"]
y_proba = model.predict_proba(X_test_scaled)[:, 1]

print("=== Cost-sensitivity table (illustrative volume: {:,}/day) ===".format(ILLUSTRATIVE_DAILY_VOLUME))
print("threshold | precision | recall | %held (est) | good txns held/day | fraud missed/day")
print("-" * 95)
for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
    y_pred = (y_proba >= t).astype(int)
    p = precision_score(y_test, y_pred, zero_division=0)
    r = recall_score(y_test, y_pred, zero_division=0)
    pct_held = y_pred.mean()
    fraud_rate = y_test.mean()
    # good txns wrongly held per day = (1-fraud_rate)*volume * FPR
    tn_fp = y_pred[y_test == 0]
    fpr = tn_fp.mean() if len(tn_fp) else 0
    fnr = 1 - r
    good_held_per_day = int(ILLUSTRATIVE_DAILY_VOLUME * (1 - fraud_rate) * fpr)
    fraud_missed_per_day = int(ILLUSTRATIVE_DAILY_VOLUME * fraud_rate * fnr)
    print(f"{t:9.2f} | {p:9.3f} | {r:6.3f} | {pct_held*100:9.1f}% | {good_held_per_day:>18,} | {fraud_missed_per_day:>16,}")

print("\nNote: volume is illustrative, not a claim about real agent-transaction")
print("volume at Razorpay. The point is the shape of the tradeoff — lower")
print("thresholds catch more fraud but hold vastly more good transactions,")
print("and at any real production volume that tradeoff has to be tuned")
print("against actual operational cost, not picked by inspection.")
