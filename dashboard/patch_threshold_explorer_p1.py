import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''      <div class="sim-result" id="sim-result"></div>
      <div class="decision-trace" id="decision-trace"></div>
    </div>

    <div class="stat-grid" id="stat-grid"></div>
    <div class="section-title">// decision distribution</div>
    <div class="bar-chart" id="bar-chart"></div>
    <div class="audit-note">
      Every decision above is logged with the exact scores and reasoning that produced it —
      no black-box calls. Fraud-risk and intent-match scores are trained, validated models
      (precision/recall reported on held-out test data); preference-fit is an explicit
      heuristic layer, not overclaimed as statistically validated.
    </div>
    <div class="audit-note" style="background: var(--amber-dim); border-color: rgba(255,180,84,0.25); color: var(--amber); margin-top: 10px;">
      Note on thresholds: this demo gates fraud at 0.5 — a business-realistic
      choice. Our reported metrics use a separately F2-optimized threshold
      (0.3), which favors catching fraud but pushes the false-positive rate
      to ~68%. Those are two different, intentional numbers for two
      different purposes — see the README for the full reasoning.
    </div>
  </section>'''

new1 = '''      <div class="sim-result" id="sim-result"></div>
      <div class="decision-trace" id="decision-trace"></div>
    </div>

    <div class="sim-panel" id="threshold-panel">
      <div class="sim-head">
        <h2>Threshold Explorer</h2>
      </div>
      <div class="sim-sub">
        We spent real effort choosing 0.25 over the alternatives — drag to see why.
        Every point below is a REAL measured value (from train_fraud_model.py's
        threshold scan and cost_sensitivity.py), not interpolated or invented.
      </div>
      <input type="range" id="threshold-slider" min="0" max="9" value="3" step="1" style="width:100%; margin: 18px 0 6px;">
      <div class="threshold-current" id="threshold-current-label"></div>
      <div class="threshold-stats" id="threshold-stats"></div>
      <div class="threshold-cost" id="threshold-cost"></div>
      <div class="threshold-verdict" id="threshold-verdict"></div>
    </div>

    <div class="stat-grid" id="stat-grid"></div>
    <div class="section-title">// decision distribution</div>
    <div class="bar-chart" id="bar-chart"></div>
    <div class="audit-note">
      Every decision above is logged with the exact scores and reasoning that produced it —
      no black-box calls. Fraud-risk and intent-match scores are trained, validated models
      (precision/recall reported on held-out test data); preference-fit is an explicit
      heuristic layer, not overclaimed as statistically validated.
    </div>
  </section>'''

if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "  .card:hover { border-color: var(--line-bright); }"
new2 = '''  .card:hover { border-color: var(--line-bright); }
  #threshold-panel { margin-top: 20px; }
  #threshold-slider {
    -webkit-appearance: none; height: 5px; border-radius: 3px;
    background: var(--line); outline: none;
  }
  #threshold-slider::-webkit-slider-thumb {
    -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%;
    background: var(--go); box-shadow: 0 0 10px var(--go-glow); cursor: pointer;
  }
  .threshold-current {
    font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink);
    margin-bottom: 14px;
  }
  .threshold-current .chosen-tag {
    font-size: 10px; font-weight: 700; color: var(--go); background: var(--go-dim);
    padding: 2px 7px; border-radius: 4px; margin-left: 8px; vertical-align: middle;
  }
  .threshold-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
  .threshold-stats .t-stat { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
  .threshold-stats .t-stat .t-num { font-family: var(--mono); font-size: 18px; font-weight: 700; color: var(--ink); }
  .threshold-stats .t-stat .t-label { font-family: var(--mono); font-size: 10px; color: var(--dim); margin-top: 2px; }
  .threshold-cost {
    font-size: 12.5px; color: var(--muted); line-height: 1.7; margin-bottom: 10px;
    padding: 12px 14px; background: var(--panel-2); border-radius: 8px; border: 1px solid var(--line);
  }
  .threshold-cost b { color: var(--ink); font-family: var(--mono); }
  .threshold-verdict { font-size: 12px; color: var(--dim); line-height: 1.6; }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("part 1 applied successfully")
