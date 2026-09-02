import sys

path = "landing3.html"

with open(path, "r") as f:
    content = f.read()

old = '''        <div class="stat-slide active"><span class="stat-hl">F2 0.856</span> vs 0.707 logistic regression \u2014 validated on 284,807 real transactions, not just synthetic data.</div>
        <div class="stat-slide"><span class="stat-hl">100%</span> of injected coordinated-abuse rings recovered, 92.3% precision \u2014 a real detection algorithm, not a heuristic.</div>
        <div class="stat-slide"><span class="stat-hl">2.15x</span> worst-case pincode disparity \u2014 bootstrap-confirmed as statistical noise, not a hidden bias.</div>
        <div class="stat-slide"><span class="stat-hl">39/39</span> tests passing, including 3 that caught real production bugs during migration.</div>'''

new = '''        <div class="stat-slide active">We didn't guess the model. We tested it on <span class="stat-hl">284,807 real transactions</span> before trusting it.</div>
        <div class="stat-slide">Every coordinated fraud ring we planted to test it? <span class="stat-hl">Caught. All 15.</span></div>
        <div class="stat-slide">We asked if our fairness numbers were real, or just noise. <span class="stat-hl">They're noise</span> \u2014 and we can prove it.</div>
        <div class="stat-slide"><span class="stat-hl">39 tests.</span> 3 caught real bugs before they ever shipped.</div>'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
