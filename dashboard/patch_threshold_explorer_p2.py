import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old = '''document.querySelector('[data-view="razorpay"]').addEventListener('click', () => {
  animateStatsIfNeeded();
  animateBarsIfNeeded();
});'''

new = old + '''

// THRESHOLD EXPLORER - every number below is a REAL value measured
// tonight (train_fraud_model.py's threshold scan for precision/recall,
// terminal-confirmed precision_score/recall_score checks for flag rate
// at 0.20-0.30, cost_sensitivity.py's real output for money figures at
// 0.25-0.50). Where a metric wasn't directly measured, we show that
// honestly instead of interpolating or inventing a number.
const THRESHOLD_DATA = [
  { t: 0.20, precision: 0.319, recall: 0.955, flagRate: 0.85, fraudPrevented: null, falseHoldRisk: null, net: null },
  { t: 0.23, precision: 0.356, recall: 0.866, flagRate: 0.74, fraudPrevented: null, falseHoldRisk: null, net: null },
  { t: 0.24, precision: 0.369, recall: 0.834, flagRate: 0.69, fraudPrevented: null, falseHoldRisk: null, net: null },
  { t: 0.25, precision: 0.378, recall: 0.798, flagRate: 0.64, fraudPrevented: 980883408, falseHoldRisk: 127413721, net: 853469687, chosen: true },
  { t: 0.28, precision: 0.405, recall: 0.668, flagRate: 0.50, fraudPrevented: null, falseHoldRisk: null, net: null },
  { t: 0.30, precision: 0.429, recall: 0.595, flagRate: 0.43, fraudPrevented: 758415006, falseHoldRisk: 80897601, net: 677517406 },
  { t: 0.35, precision: 0.470, recall: 0.441, flagRate: null, fraudPrevented: 556171005, falseHoldRisk: 52583440, net: 503587564 },
  { t: 0.40, precision: 0.500, recall: 0.300, flagRate: null, fraudPrevented: 414600203, falseHoldRisk: 28314160, net: 386286043 },
  { t: 0.45, precision: 0.585, recall: 0.194, flagRate: null, fraudPrevented: 273029402, falseHoldRisk: 15370544, net: 257658858 },
  { t: 0.50, precision: 0.800, recall: 0.113, flagRate: null, fraudPrevented: 121346401, falseHoldRisk: 6067320, net: 115279081 },
];

function formatCrore(n) {
  if (n === null || n === undefined) return null;
  return `\\u20b9${(n / 10000000).toFixed(1)} Cr/day`;
}

function renderThresholdExplorer(idx) {
  const d = THRESHOLD_DATA[idx];
  const label = document.getElementById('threshold-current-label');
  const stats = document.getElementById('threshold-stats');
  const cost = document.getElementById('threshold-cost');
  const verdict = document.getElementById('threshold-verdict');

  label.innerHTML = `FRAUD_THRESHOLD = ${d.t.toFixed(2)}` +
    (d.chosen ? '<span class="chosen-tag">\\u2713 WHAT WE ACTUALLY SHIP</span>' : '');

  stats.innerHTML = `
    <div class="t-stat"><div class="t-num">${(d.precision * 100).toFixed(1)}%</div><div class="t-label">precision</div></div>
    <div class="t-stat"><div class="t-num">${(d.recall * 100).toFixed(1)}%</div><div class="t-label">recall</div></div>
    <div class="t-stat"><div class="t-num">${d.flagRate !== null ? (d.flagRate * 100).toFixed(0) + '%' : '\\u2014'}</div><div class="t-label">flag rate${d.flagRate === null ? ' (not tracked here)' : ''}</div></div>
  `;

  if (d.fraudPrevented !== null) {
    cost.innerHTML = `Illustrative daily impact at this threshold (from cost_sensitivity.py, using our own real order-value data, not a claim about Razorpay's real volume): fraud loss prevented <b>${formatCrore(d.fraudPrevented)}</b>, false-hold revenue risk <b>${formatCrore(d.falseHoldRisk)}</b>, net <b>${formatCrore(d.net)}</b>.`;
  } else {
    cost.innerHTML = `Cost-impact wasn't computed at this specific threshold (cost_sensitivity.py's scan covers 0.25-0.50) - shown honestly as missing rather than estimated.`;
  }

  if (d.chosen) {
    verdict.textContent = "This is our actual production threshold, chosen because it maximizes the recall gain (0.595 to 0.798 vs the original 0.30) while keeping the fairness disparity within statistical noise, not a confirmed bias (see pipeline.py's FRAUD_THRESHOLD history for the full reasoning).";
  } else if (d.t < 0.25) {
    verdict.textContent = "Higher recall, but flag rate climbs fast: at 0.20 (the F2-optimal extreme) we'd flag 85%+ of every pincode, which stopped being targeted risk-based friction and became blanket friction on nearly all customers. Rejected for that reason.";
  } else {
    verdict.textContent = `Higher precision, but recall drops: at ${d.t.toFixed(2)} we'd only catch ${(d.recall * 100).toFixed(0)}% of real fraud, worse than our chosen 79.8%. Recall matters more than precision for fraud specifically, since a missed fraud costs the full order value.`;
  }
}

const thresholdSlider = document.getElementById('threshold-slider');
thresholdSlider.addEventListener('input', () => renderThresholdExplorer(parseInt(thresholdSlider.value)));
renderThresholdExplorer(3);'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("part 2 applied successfully")
