import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''const demoData = JSON.parse(document.getElementById('demo-data').textContent);
const aggStats = JSON.parse(document.getElementById('agg-stats').textContent);'''
new1 = '''const demoData = JSON.parse(document.getElementById('demo-data').textContent);
const aggStats = JSON.parse(document.getElementById('agg-stats').textContent);

// Read the carried transaction (from checkout.html's "See what RiskGate
// did" link) BEFORE any tab renders, and unshift it into demoData with a
// _isLive flag. Consumer, Merchant, and the Fraud queue review card all
// iterate over demoData already, so this one change makes all three
// (plus Razorpay's sim panel, handled separately below) show the SAME
// real transaction — the actual point of the demo.
let liveTxn = null;
try {
  const _params = new URLSearchParams(window.location.search);
  const _carried = _params.get('result');
  if (_carried) {
    liveTxn = JSON.parse(decodeURIComponent(_carried));
    liveTxn._isLive = true;
    demoData.unshift(liveTxn);
  }
} catch (e) { /* malformed/missing param — proceed with replay data only */ }'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''  div.innerHTML = `
    <div class="card-row">
      <div>
        <div class="agent-line">${d.agent_id} · on your behalf</div>
        <div class="item-line">${d.order_category[0].toUpperCase()+d.order_category.slice(1)} order</div>
        <div class="price">₹${d.order_price.toLocaleString('en-IN')} · intent budget ₹${d.intent_max_price.toLocaleString('en-IN')}</div>
      </div>
      <span class="badge ${b.cls}">${b.label}</span>
    </div>
    <div class="reason">${d.reason}</div>
  `;'''
new2 = '''  if (d._isLive) div.classList.add('live-highlight');
  div.innerHTML = `
    <div class="card-row">
      <div>
        <div class="agent-line">${d._isLive ? '\\u25cf LIVE \\u00b7 ' : ''}${d.agent_id} · on your behalf</div>
        <div class="item-line">${d.order_category[0].toUpperCase()+d.order_category.slice(1)} order</div>
        <div class="price">₹${d.order_price.toLocaleString('en-IN')} · intent budget ₹${d.intent_max_price.toLocaleString('en-IN')}</div>
      </div>
      <span class="badge ${b.cls}">${b.label}</span>
    </div>
    <div class="reason">${d.reason}</div>
  `;'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''    const tr = document.createElement('tr');
    tr.style.animationDelay = `${Math.min(i * 18, 400)}ms`;
    tr.innerHTML = `
      <td class="mono">${d.order_id}</td>'''
new3 = '''    const tr = document.createElement('tr');
    tr.style.animationDelay = `${Math.min(i * 18, 400)}ms`;
    if (d._isLive) tr.classList.add('live-highlight');
    tr.innerHTML = `
      <td class="mono">${d._isLive ? '\\u25cf LIVE ' : ''}${d.order_id}</td>'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = '''const reviewCard = document.getElementById('review-card');
const flaggedExample = demoData.find(d => d.decision === 'HOLD_FRAUD_REVIEW') || demoData[0];'''
new4 = '''const reviewCard = document.getElementById('review-card');
const HOLD_DECISIONS = ['HOLD_FRAUD_REVIEW', 'HOLD_QUICK_VERIFY', 'HOLD_CONFIRM_WITH_HUMAN', 'HOLD_LIKELY_MISMATCH'];
const flaggedExample = (liveTxn && HOLD_DECISIONS.includes(liveTxn.decision))
  ? liveTxn
  : (demoData.find(d => d.decision === 'HOLD_FRAUD_REVIEW') || demoData[0]);'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

old5 = '''    <span class="badge fraud">Fraud review</span>
  </div>
  <div class="review-signals">
    <div class="review-signal"><span class="label">fraud_risk_score</span><span class="value flag">${flaggedExample.fraud_risk_score}</span></div>'''
new5 = '''    <span class="badge ${badgeInfo(flaggedExample.decision).cls}">${badgeInfo(flaggedExample.decision).label}</span>
  </div>
  <div class="review-signals">
    <div class="review-signal"><span class="label">fraud_risk_score</span><span class="value flag">${flaggedExample.fraud_risk_score}</span></div>'''
if old5 not in content:
    print("PATTERN 5 NOT FOUND")
    sys.exit(1)
content = content.replace(old5, new5)

old6 = "  .card:hover { border-color: var(--line-bright); }"
new6 = '''  .card:hover { border-color: var(--line-bright); }
  .card.live-highlight, tr.live-highlight { border-color: var(--go); box-shadow: 0 0 0 1px var(--go), 0 0 16px var(--go-glow); }
  tr.live-highlight { background: rgba(94,255,157,0.04); }'''
if old6 not in content:
    print("PATTERN 6 NOT FOUND")
    sys.exit(1)
content = content.replace(old6, new6)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
