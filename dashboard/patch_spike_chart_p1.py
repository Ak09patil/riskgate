import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''    <div class="uth-footer">
      Model: calibrated XGBoost, threshold 0.25 / 0.45 (two-tier) - last changed Sept 2, 2026. Full decision history in git, not just this dashboard.
    </div>
  </section>'''

new1 = '''    <div class="section-title" style="margin-top:34px;">// fraud-spike detector \\u2014 top buckets by z-score <span class="uth-src">synthetic, injected ground truth</span></div>
    <div class="spike-note">
      A THIRD, genuinely different detection layer from per-transaction scoring and ring
      detection: does the aggregate fraud RATE over a time window look anomalous, even if
      no single transaction in it looks alarming alone? Method: median + MAD (robust to
      outliers), not mean/std \\u2014 real output from spike_detector.py, 167 buckets scanned,
      11 flagged. Top 10 shown here by z-score.
    </div>
    <div class="spike-chart" id="spike-chart"></div>
    <div class="spike-legend">
      <span class="spike-dot spike-tp"></span> caught a real injected spike (6 of 6 in top 10)
      <span class="spike-dot spike-fp"></span> flagged, but not an injected spike (4 of 10)
    </div>

    <div class="uth-footer">
      Model: calibrated XGBoost, threshold 0.25 / 0.45 (two-tier) - last changed Sept 2, 2026. Full decision history in git, not just this dashboard.
    </div>
  </section>'''

if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "  .card:hover { border-color: var(--line-bright); }"
new2 = '''  .card:hover { border-color: var(--line-bright); }
  .spike-note { font-size: 12px; color: var(--muted); line-height: 1.6; margin-bottom: 16px; max-width: 700px; }
  .spike-chart { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
  .spike-row { display: grid; grid-template-columns: 150px 1fr 90px 50px; align-items: center; gap: 10px; font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .spike-bar-track { height: 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }
  .spike-bar-fill { height: 100%; }
  .spike-bar-fill.spike-tp { background: var(--go); box-shadow: 0 0 8px var(--go-glow) inset; }
  .spike-bar-fill.spike-fp { background: var(--amber); box-shadow: 0 0 8px var(--amber-glow) inset; }
  .spike-legend { font-size: 11px; color: var(--dim); display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
  .spike-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-left: 14px; margin-right: 2px; }
  .spike-dot.spike-tp { background: var(--go); }
  .spike-dot.spike-fp { background: var(--amber); }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("part 1 applied successfully")
