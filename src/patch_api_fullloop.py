import sys

path = "api.py"

with open(path, "r") as f:
    content = f.read()

old = '''    return jsonify({
        "status": "SCORED",
        "intent": intent,
        "proposed_product": proposal["matched_product"],
        "matched_rule": proposal["matched_rule"],
        "agent_id": row["agent_id"],
        "order_category": proposal["order_category"],
        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        **decision,
    })'''

new = '''    # order_id and timestamp added specifically so the dashboard can carry
    # ONE live transaction's identity through localStorage across pages
    # (checkout -> dashboard), letting Consumer/Merchant/Razorpay/Fraud
    # queue all show the SAME real transaction instead of independent
    # random samples of static replay data.
    import time as _time
    from datetime import datetime as _datetime
    return jsonify({
        "status": "SCORED",
        "order_id": f"live_{int(_time.time() * 1000)}",
        "timestamp": _datetime.now().isoformat(),
        "intent": intent,
        "proposed_product": proposal["matched_product"],
        "matched_rule": proposal["matched_rule"],
        "agent_id": row["agent_id"],
        "order_category": proposal["order_category"],
        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        "pincode": txn["pincode"],
        "payment_mode": txn["payment_mode"],
        **decision,
    })'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
