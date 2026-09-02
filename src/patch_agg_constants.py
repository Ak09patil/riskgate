import sys

path = "build_dashboard_data.py"

with open(path, "r") as f:
    content = f.read()

old1 = "from pipeline import FRAUD_THRESHOLD, FRAUD_THRESHOLD_HIGH"
new1 = "from pipeline import (FRAUD_THRESHOLD, FRAUD_THRESHOLD_HIGH, CIRCUIT_BREAKER_MAX_ORDER_VALUE,\n                       FRAUD_BORDERLINE_BAND, TRUST_OVERRIDE_HISTORY_THRESHOLD, PREF_FIT_THRESHOLD)"
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''    "intent_threshold": intent_threshold,
    "fraud_threshold": FRAUD_THRESHOLD,  # imported live from pipeline.py, not hardcoded
    "fraud_threshold_high": FRAUD_THRESHOLD_HIGH,
}'''
new2 = '''    "intent_threshold": intent_threshold,
    "fraud_threshold": FRAUD_THRESHOLD,  # imported live from pipeline.py, not hardcoded
    "fraud_threshold_high": FRAUD_THRESHOLD_HIGH,
    # Added for the dashboard's Decision Trace, which walks the SAME
    # gating order as score_transaction() step by step, using the SAME
    # constants - not a separate hardcoded copy in the frontend.
    "circuit_breaker_max_order_value": CIRCUIT_BREAKER_MAX_ORDER_VALUE,
    "fraud_borderline_band": FRAUD_BORDERLINE_BAND,
    "trust_override_history_threshold": TRUST_OVERRIDE_HISTORY_THRESHOLD,
    "pref_fit_threshold": PREF_FIT_THRESHOLD,
}'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
