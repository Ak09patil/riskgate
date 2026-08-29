"""
Build dashboard data — merges transactions with gating decisions and
produces the demo_data.json / agg_stats.json the dashboard reads for its
"replay" mode (when the live API isn't running).

This step previously existed only as ad-hoc commands run manually — never
saved as a real script, which meant a fresh clone of this repo had no way
to actually reproduce the dashboard's replay data. Fixed by making this a
real, run-able part of the pipeline.

Run this AFTER gating.py, before opening the dashboard.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import json
import joblib

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
gate = pd.read_csv(f"{BASE_DIR}/data/gating_decisions.csv")
merged = df.merge(gate, on="order_id")
merged.to_csv(f"{BASE_DIR}/data/full_merged.csv", index=False)
print(f"Merged {len(merged)} rows -> data/full_merged.csv")

samples = [
    merged[merged["decision"] == d].head(15)
    for d in ["AUTO_APPROVE", "HOLD_FRAUD_REVIEW", "HOLD_CONFIRM_WITH_HUMAN", "HOLD_LIKELY_MISMATCH"]
]
demo_df = pd.concat(samples).reset_index(drop=True)
cols = [
    "order_id", "user_id", "agent_id", "order_category", "order_price",
    "intent_category", "intent_max_price", "payment_mode", "pincode",
    "timestamp", "fraud_risk_score", "intent_match_confidence",
    "preference_fit_score", "decision", "reason",
]
demo_data = demo_df[cols].to_dict(orient="records")
with open(f"{BASE_DIR}/dashboard/demo_data.json", "w") as f:
    json.dump(demo_data, f, indent=2)
print(f"Saved {len(demo_data)} sample records -> dashboard/demo_data.json")

intent_threshold = joblib.load(f"{BASE_DIR}/models/intent_threshold.pkl")
agg = {
    "total_transactions": len(merged),
    "decision_counts": merged["decision"].value_counts().to_dict(),
    "avg_fraud_risk": round(merged["fraud_risk_score"].mean(), 3),
    "avg_intent_match": round(merged["intent_match_confidence"].mean(), 3),
    "intent_threshold": intent_threshold,
    "fraud_threshold": 0.5,  # matches pipeline.py's FRAUD_THRESHOLD (fixed business value)
}
with open(f"{BASE_DIR}/dashboard/agg_stats.json", "w") as f:
    json.dump(agg, f, indent=2)
print("Saved aggregate stats -> dashboard/agg_stats.json")
print(agg)

print("\nNOTE: dashboard/index.html has this data EMBEDDED directly in the")
print("HTML (for a portable, single-file demo). After running this script,")
print("re-embed with the snippet in README's 'Running it for real' section,")
print("or just use the dashboard's live mode (start src/api.py) which reads")
print("fresh data on every click and doesn't need re-embedding at all.")
