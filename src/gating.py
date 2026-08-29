"""
RiskGate batch gating — runs score_transaction() (from pipeline.py) over
the whole transaction dataset and saves the results.

This used to be a SECOND, separate implementation of the scoring/gating
logic, duplicating pipeline.py. That was a real bug waiting to happen —
and it did: pipeline.py's INTENT_THRESHOLD got fixed to load from a
training artifact (so it can never silently go stale again), but this
file still had its own hardcoded copy that could drift independently.
Fixed by making this a thin wrapper: ONE gating implementation
(pipeline.score_transaction), called here for batch scoring instead of
live API calls.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import json

from pipeline import score_transaction


def row_to_txn(row):
    """Adapt a transactions.csv row into the dict shape score_transaction() expects."""
    return {
        "order_price": row["order_price"],
        "order_category": row["order_category"],
        "order_key_attribute": row["order_key_attribute"],
        "payment_mode": row["payment_mode"],
        "pincode": row["pincode"],
        "agent_age_days": row["agent_age_days"],
        "intent_category": row["intent_category"],
        "intent_max_price": row["intent_max_price"],
        "intent_key_attribute": row["intent_key_attribute"],
        "user_historical_category": row["user_historical_category"],
        "user_past_over_budget_kept_rate": row["user_past_over_budget_kept_rate"],
        "device_ip_consistency": row["device_ip_consistency"],
        "user_account_age_days": row["user_account_age_days"],
    }


if __name__ == "__main__":
    df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

    results = []
    for _, row in df.iterrows():
        txn = row_to_txn(row)
        decision = score_transaction(txn)
        decision["order_id"] = row["order_id"]
        results.append(decision)

    results_df = pd.DataFrame(results)

    print("=== GATING DECISIONS — distribution across all transactions ===")
    print(results_df["decision"].value_counts())
    print()
    print("=== Sample decisions ===")
    for i in [0, 1, 2, 3, 4]:
        print(json.dumps(results[i], indent=2))
        print()

    results_df.to_csv(f"{BASE_DIR}/data/gating_decisions.csv", index=False)
    print("Saved to data/gating_decisions.csv")
