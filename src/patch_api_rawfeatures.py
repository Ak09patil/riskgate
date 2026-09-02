import sys

path = "api.py"

with open(path, "r") as f:
    content = f.read()

old = '''        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        "pincode": txn["pincode"],
        "payment_mode": txn["payment_mode"],
        **decision,
    })'''

new = '''        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        "pincode": txn["pincode"],
        "payment_mode": txn["payment_mode"],
        # Raw feature fields, added for the dashboard's Decision Trace -
        # same fields as build_dashboard_data.py exports for replay data,
        # so live and replay transactions have an identical shape.
        "agent_age_days": txn["agent_age_days"],
        "device_ip_consistency": txn["device_ip_consistency"],
        "user_past_over_budget_kept_rate": txn["user_past_over_budget_kept_rate"],
        **decision,
    })'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
