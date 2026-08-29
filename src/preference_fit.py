"""
Preference-fit score — model 3 of 3 (LIGHTER, DIRECTIONAL — by design).

This script does NOT reimplement the preference-fit formula — that logic
lives in exactly one place, pipeline.score_transaction() (same fix as
gating.py: a second copy of this logic previously existed here, went
stale, and produced a dead file (transactions_scored.csv) nothing else
used. Removed for the same reason gating.py was refactored).

This script instead calls the real pipeline on real rows from the dataset
and reports whether the heuristic behaves sensibly — a sanity check on
the ACTUAL system, not a parallel implementation of it.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from pipeline import score_transaction
from gating import row_to_txn

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

print("=== PREFERENCE-FIT SCORE — sanity check on the REAL pipeline (not a duplicate) ===")
sample = df.sample(min(500, len(df)), random_state=1)
scores = []
for _, row in sample.iterrows():
    txn = row_to_txn(row)
    result = score_transaction(txn)
    scores.append({
        "order_category": row["order_category"],
        "user_historical_category": row["user_historical_category"],
        "user_account_age_days": row["user_account_age_days"],
        "preference_fit_score": result["preference_fit_score"],
    })
scores_df = pd.DataFrame(scores)

match = scores_df[scores_df["order_category"] == scores_df["user_historical_category"]]
mismatch = scores_df[scores_df["order_category"] != scores_df["user_historical_category"]]
new_users = scores_df[scores_df["user_account_age_days"] < 30]

print(f"Average preference_fit_score when category matches history: {match['preference_fit_score'].mean():.3f}")
print(f"Average preference_fit_score when category does NOT match: {mismatch['preference_fit_score'].mean():.3f}")
print(f"Average preference_fit_score for NEW users (<30 days, cold-start): {new_users['preference_fit_score'].mean():.3f}")
print("(new users should average close to 0.5 — the neutral cold-start default,")
print(" not penalized for lacking history — see README/SPEC for why)")
