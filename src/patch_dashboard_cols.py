import sys

path = "build_dashboard_data.py"

with open(path, "r") as f:
    content = f.read()

old = '''cols = [
    "order_id", "user_id", "agent_id", "order_category", "order_price",
    "intent_category", "intent_max_price", "payment_mode", "pincode",
    "timestamp", "fraud_risk_score", "intent_match_confidence",
    "preference_fit_score", "decision", "reason",
]'''

new = '''cols = [
    "order_id", "user_id", "agent_id", "order_category", "order_price",
    "intent_category", "intent_max_price", "payment_mode", "pincode",
    "timestamp", "fraud_risk_score", "intent_match_confidence",
    "preference_fit_score", "decision", "reason",
    # Raw feature fields, added for the dashboard's Decision Trace
    # (a step-through of the actual gating logic - circuit-breaker,
    # two-tier fraud threshold, trust override, intent-match, pref-fit -
    # which needs the underlying signal values, not just the final scores).
    "agent_age_days", "device_ip_consistency", "user_past_over_budget_kept_rate",
]'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
