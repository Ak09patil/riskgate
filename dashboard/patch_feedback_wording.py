import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old = "text.textContent = `${data.count} outcome(s) recorded so far this session \\u2014 model's HOLD_FRAUD_REVIEW decision matched the confirmed real outcome ${pct}% of the time (${data.confirmed_fraud_count} confirmed fraud, ${data.confirmed_not_fraud_count} confirmed not-fraud). This is exactly the shadow-mode check a real deployment would run before trusting a retrain \\u2014 see src/feedback_loop.py.`;"

new = "text.textContent = `${data.count} outcome(s) recorded in total (data/outcomes_log.csv, across every session, not just this page load) \\u2014 model's HOLD_FRAUD_REVIEW decision matched the confirmed real outcome ${pct}% of the time (${data.confirmed_fraud_count} confirmed fraud, ${data.confirmed_not_fraud_count} confirmed not-fraud). This is exactly the shadow-mode check a real deployment would run before trusting a retrain \\u2014 see src/feedback_loop.py.`;"

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
