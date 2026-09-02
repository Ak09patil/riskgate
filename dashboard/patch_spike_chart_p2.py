import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old = "renderThresholdExplorer(3);"

new = old + '''

// SPIKE DETECTOR CHART - real output from a spike_detector.py run
// tonight (167 buckets scanned, top 10 shown by z-score).
const SPIKE_BUCKETS = [
  { date: '2026-01-02 18:00', fraudRate: 0.700, zScore: 6.24, truePositive: true },
  { date: '2026-01-09 18:00', fraudRate: 0.621, zScore: 5.03, truePositive: true },
  { date: '2026-01-06 14:00', fraudRate: 0.571, zScore: 4.27, truePositive: true },
  { date: '2026-01-06 12:00', fraudRate: 0.571, zScore: 4.27, truePositive: true },
  { date: '2026-01-09 16:00', fraudRate: 0.565, zScore: 4.18, truePositive: true },
  { date: '2026-01-13 04:00', fraudRate: 0.560, zScore: 4.10, truePositive: true },
  { date: '2026-01-03 06:00', fraudRate: 0.556, zScore: 4.03, truePositive: false },
  { date: '2026-01-09 06:00', fraudRate: 0.520, zScore: 3.49, truePositive: false },
  { date: '2026-01-14 20:00', fraudRate: 0.500, zScore: 3.18, truePositive: false },
  { date: '2026-01-05 10:00', fraudRate: 0.500, zScore: 3.18, truePositive: false },
];

function renderSpikeChart() {
  const el = document.getElementById('spike-chart');
  const maxRate = Math.max(...SPIKE_BUCKETS.map(b => b.fraudRate));
  el.innerHTML = SPIKE_BUCKETS.map(b => {
    const cls = b.truePositive ? 'spike-tp' : 'spike-fp';
    const pct = (b.fraudRate / maxRate) * 100;
    return `
      <div class="spike-row">
        <div>${b.date}</div>
        <div class="spike-bar-track"><div class="spike-bar-fill ${cls}" style="width:${pct}%"></div></div>
        <div>fraud rate ${(b.fraudRate * 100).toFixed(0)}%</div>
        <div>z=${b.zScore.toFixed(2)}</div>
      </div>`;
  }).join('');
}
renderSpikeChart();'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("part 2 applied successfully")
