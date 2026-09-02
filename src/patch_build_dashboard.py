import sys

path = "build_dashboard_data.py"

with open(path, "r") as f:
    content = f.read()

old1 = '''import pandas as pd
import json
import joblib

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")'''
new1 = '''import pandas as pd
import json
import joblib

from pipeline import FRAUD_THRESHOLD, FRAUD_THRESHOLD_HIGH

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''samples = [
    merged[merged["decision"] == d].head(15)
    for d in ["AUTO_APPROVE", "HOLD_FRAUD_REVIEW", "HOLD_CONFIRM_WITH_HUMAN", "HOLD_LIKELY_MISMATCH"]
]'''
new2 = '''samples = [
    merged[merged["decision"] == d].head(15)
    for d in ["AUTO_APPROVE", "HOLD_QUICK_VERIFY", "HOLD_FRAUD_REVIEW", "HOLD_CONFIRM_WITH_HUMAN", "HOLD_LIKELY_MISMATCH"]
]'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''    "intent_threshold": intent_threshold,
    "fraud_threshold": 0.5,  # matches pipeline.py's FRAUD_THRESHOLD (fixed business value)
}'''
new3 = '''    "intent_threshold": intent_threshold,
    "fraud_threshold": FRAUD_THRESHOLD,  # imported live from pipeline.py, not hardcoded
    "fraud_threshold_high": FRAUD_THRESHOLD_HIGH,
}'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
