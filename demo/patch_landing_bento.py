path = "landing.html"

new_content = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RiskGate</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
  :root {
    --bg: #08090b; --panel: #0e1013; --panel-2: #131619; --line: #22262b; --line-bright: #34393f;
    --ink: #eef0f2; --muted: #7a8189; --dim: #4a5058;
    --go: #5eff9d; --go-dim: #1c3d2b; --go-glow: rgba(94,255,157,0.18);
    --stop: #ff5c5c; --amber: #ffb454; --verify: #5ec8ff;
    --mono: 'JetBrains Mono', monospace; --display: 'Space Grotesk', sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink);
    font-family: var(--display);
    background-image: radial-gradient(ellipse 900px 600px at 50% -10%, rgba(94,255,157,0.06), transparent);
  }
  .wrap { max-width: 900px; margin: 0 auto; padding: 56px 24px 70px; text-align: center; }
  .brand { display: flex; align-items: center; justify-content: center; gap: 11px; margin-bottom: 36px; }
  .brand .mark {
    width: 22px; height: 22px; border-radius: 5px;
    background: linear-gradient(135deg, var(--go), #2fd97a); box-shadow: 0 0 16px var(--go-glow);
    position: relative;
  }
  .brand .mark::after { content: ''; position: absolute; inset: 5px; border-radius: 2px; background: var(--bg); }
  .brand h1 { font-size: 18px; font-weight: 700; margin: 0; }

  .eyebrow {
    font-family: var(--mono); font-size: 11px; color: var(--go); letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 18px;
  }
  h2 { font-size: 30px; line-height: 1.38; font-weight: 600; letter-spacing: -0.01em; margin: 0 0 18px; }
  h2 .strike { color: var(--dim); text-decoration: line-through; text-decoration-color: var(--stop); }
  h2 .go { color: var(--go); }
  p.sub { font-size: 14.5px; color: var(--muted); line-height: 1.65; max-width: 560px; margin: 0 auto 34px; }

  .cta {
    font-family: var(--mono); font-size: 13.5px; font-weight: 600; letter-spacing: 0.02em;
    color: var(--bg); background: var(--go); border: none; padding: 14px 28px; border-radius: 9px;
    cursor: pointer; box-shadow: 0 0 24px var(--go-glow); transition: all 0.15s ease;
    text-decoration: none; display: inline-block;
  }
  .cta:hover { transform: translateY(-2px); box-shadow: 0 0 32px var(--go-glow); }

  .steps { display: flex; justify-content: center; gap: 28px; margin: 44px 0 60px; }
  .step { font-family: var(--mono); font-size: 11px; color: var(--dim); max-width: 140px; }
  .step .n {
    width: 22px; height: 22px; border: 1px solid var(--line); border-radius: 50%;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; color: var(--muted);
  }

  .bento-title {
    font-family: var(--mono); font-size: 11px; color: var(--dim); text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 18px; text-align: left;
  }
  .bento {
    display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: 110px;
    gap: 12px; text-align: left; margin-bottom: 20px;
  }
  .bento-card {
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    padding: 16px 18px; display: flex; flex-direction: column; justify-content: space-between;
    transition: border-color 0.15s ease; overflow: hidden;
  }
  .bento-card:hover { border-color: var(--line-bright); }
  .bento-card.big { grid-column: span 2; grid-row: span 2; }
  .bento-card.wide { grid-column: span 2; }
  .bento-card .b-tag {
    font-family: var(--mono); font-size: 9.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--go); margin-bottom: 8px;
  }
  .bento-card .b-num { font-family: var(--mono); font-size: 22px; font-weight: 700; color: var(--ink); }
  .bento-card .b-title { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }
  .bento-card .b-desc { font-size: 11px; color: var(--muted); line-height: 1.5; }
  .bento-card.verify .b-tag { color: var(--verify); }
  .bento-card.amber .b-tag { color: var(--amber); }

  @media (max-width: 720px) {
    .bento { grid-template-columns: repeat(2, 1fr); grid-auto-rows: 130px; }
    .bento-card.big { grid-column: span 2; grid-row: span 1; }
    .steps { flex-direction: column; gap: 16px; align-items: center; }
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="brand"><span class="mark"></span><h1>RiskGate</h1></div>
  <div class="eyebrow">watch it work</div>
  <h2>Every payment used to have a human tap a PIN to confirm it.<br><span class="strike">That moment is gone.</span> <span class="go">Here's what replaces it.</span></h2>
  <p class="sub">An AI agent is about to buy something on a customer's behalf. Watch it happen — then watch RiskGate score and gate the transaction, live, in real time.</p>
  <a class="cta" href="checkout.html">Start the demo &#9656;</a>

  <div class="steps">
    <div class="step"><div class="n">1</div>An agent shops for a customer</div>
    <div class="step"><div class="n">2</div>RiskGate scores the transaction, live</div>
    <div class="step"><div class="n">3</div>See the full decision trail</div>
  </div>

  <div class="bento-title">// what's actually running underneath</div>
  <div class="bento">
    <div class="bento-card big">
      <div>
        <div class="b-tag">model decision</div>
        <div class="b-title">Tested XGBoost vs logistic regression on 284,807 real transactions</div>
      </div>
      <div class="b-desc">Not assumed — validated. Real held-out data (Kaggle Credit Card Fraud), not just our own synthetic benchmark.</div>
    </div>
    <div class="bento-card">
      <div class="b-tag">gating</div>
      <div class="b-num">2-tier</div>
      <div class="b-desc">Full review reserved for high-confidence fraud only</div>
    </div>
    <div class="bento-card">
      <div class="b-tag">tests</div>
      <div class="b-num">39/39</div>
      <div class="b-desc">Passing, including 3 that caught real bugs</div>
    </div>
    <div class="bento-card amber">
      <div class="b-tag">fairness</div>
      <div class="b-num">Audited</div>
      <div class="b-desc">Bootstrap CI on every pincode disparity, not just a raw ratio</div>
    </div>
    <div class="bento-card">
      <div class="b-tag">calibration</div>
      <div class="b-num">0.194</div>
      <div class="b-desc">Brier score, Platt-scaled, verified genuine improvement</div>
    </div>
    <div class="bento-card verify wide">
      <div>
        <div class="b-tag">abuse detection</div>
        <div class="b-title">100% of injected coordinated-abuse rings recovered</div>
      </div>
      <div class="b-desc">Plus a third, independent layer: time-bucketed spike detection for aggregate rate anomalies neither the fraud model nor the ring detector can see alone.</div>
    </div>
  </div>
</div>
</body>
</html>
'''

with open(path, "w") as f:
    f.write(new_content)

print("landing page rewritten successfully")
