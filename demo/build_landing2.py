path = "landing2.html"

new_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RiskGate</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
  :root {
    --bg: #080808; --panel: #0f0f0f; --line: #1e1e1e; --line-bright: #00ff66;
    --ink: #f2f2f0; --muted: #8a8a86; --dim: #4a4a48;
    --neon: #00ff66; --neon-glow: rgba(0,255,102,0.28); --neon-dim: rgba(0,255,102,0.08);
    --red: #ff3b3b;
    --mono: 'JetBrains Mono', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--bg); color: var(--ink); font-family: var(--mono);
    overflow-x: hidden;
  }

  /* fixed pinned background: subtle animated grid, scanline feel */
  .bg-fixed {
    position: fixed; inset: 0; z-index: -1;
    background-image:
      linear-gradient(rgba(0,255,102,0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,102,0.035) 1px, transparent 1px);
    background-size: 42px 42px;
    background-color: var(--bg);
  }
  .bg-fixed::after {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse 900px 700px at 50% 30%, rgba(0,255,102,0.07), transparent 65%);
    animation: pulse 6s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 0.6; } 50% { opacity: 1; } }

  nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 40;
    display: flex; align-items: center; justify-content: space-between;
    padding: 22px 40px; border-bottom: 1px solid var(--line);
    background: rgba(8,8,8,0.7); backdrop-filter: blur(10px);
  }
  .brand { font-size: 14px; font-weight: 800; letter-spacing: 0.02em; color: var(--neon); }
  .brand span { color: var(--ink); }
  .nav-right { display: flex; align-items: center; gap: 26px; font-size: 11px; color: var(--muted); }
  .nav-right a { color: inherit; text-decoration: none; transition: color 0.15s ease; }
  .nav-right a:hover { color: var(--neon); }
  .sound-toggle {
    display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--muted);
    border: 1px solid var(--line); padding: 6px 12px; border-radius: 100px; font-size: 10px;
  }
  .sound-toggle:hover { border-color: var(--neon); color: var(--neon); }
  .demo-btn {
    font-size: 11px; font-weight: 700; color: var(--bg); background: var(--neon);
    padding: 9px 18px; border-radius: 4px; text-decoration: none; box-shadow: 0 0 20px var(--neon-glow);
  }

  /* hero */
  .hero {
    height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
    text-align: center; padding: 0 24px; position: sticky; top: 0;
  }
  .hero-inner { transition: opacity 0.3s ease, transform 0.3s ease; }
  .hero .tag {
    font-size: 11px; color: var(--neon); letter-spacing: 0.15em; text-transform: uppercase;
    margin-bottom: 26px; display: flex; align-items: center; gap: 8px; justify-content: center;
  }
  .hero .tag::before { content: ''; width: 6px; height: 6px; background: var(--neon); box-shadow: 0 0 10px var(--neon-glow); }
  .hero h1 {
    font-size: 72px; font-weight: 800; line-height: 1.02; letter-spacing: -0.02em;
    text-transform: uppercase; margin-bottom: 24px;
  }
  .hero h1 .neon { color: var(--neon); text-shadow: 0 0 30px var(--neon-glow); }
  .hero p.sub { font-size: 14px; color: var(--muted); max-width: 480px; margin: 0 auto 36px; line-height: 1.7; }
  .cta {
    font-size: 12px; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;
    color: var(--bg); background: var(--neon); border: none; padding: 15px 30px;
    text-decoration: none; display: inline-block; box-shadow: 0 0 30px var(--neon-glow);
    transition: transform 0.15s ease;
  }
  .cta:hover { transform: translateY(-2px); }
  .scroll-hint { position: absolute; bottom: 40px; font-size: 10px; color: var(--dim); letter-spacing: 0.1em; }

  /* spacer to allow hero fade-out via scroll */
  .hero-spacer { height: 60vh; position: relative; z-index: 1; }

  .section { position: relative; z-index: 1; max-width: 960px; margin: 0 auto; padding: 100px 24px; background: var(--bg); }
  .reveal { opacity: 0; transform: translateY(24px); transition: opacity 0.6s ease, transform 0.6s ease; }
  .reveal.in-view { opacity: 1; transform: none; }

  .section-label {
    font-size: 10px; color: var(--dim); letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 20px;
  }

  /* legacy vs riskgate comparison */
  .compare-row {
    display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 28px 0;
    border-bottom: 1px solid var(--line); align-items: center;
  }
  .compare-row:first-of-type { border-top: 1px solid var(--line); }
  .compare-old { font-size: 20px; color: var(--dim); text-decoration: line-through; text-decoration-color: var(--red); }
  .compare-new { font-size: 20px; color: var(--neon); font-weight: 700; }
  .compare-new .cite { display: block; font-size: 10px; color: var(--muted); font-weight: 400; margin-top: 6px; text-decoration: none; }

  /* numbered steps */
  .steps-list { display: flex; flex-direction: column; gap: 0; }
  .step-row {
    display: grid; grid-template-columns: 90px 1fr; gap: 24px; padding: 30px 0;
    border-bottom: 1px solid var(--line); align-items: start;
  }
  .step-row:first-child { border-top: 1px solid var(--line); }
  .step-num { font-size: 40px; font-weight: 800; color: var(--neon); opacity: 0.5; }
  .step-body h3 { font-size: 17px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.01em; }
  .step-body p { font-size: 12.5px; color: var(--muted); line-height: 1.7; max-width: 500px; }

  /* tabbed capabilities */
  .tabs-wrap { display: grid; grid-template-columns: 220px 1fr; gap: 30px; }
  .tabs-sidebar { display: flex; flex-direction: column; gap: 2px; }
  .tab-item {
    text-align: left; background: none; border: none; color: var(--muted); font-family: var(--mono);
    font-size: 12px; padding: 14px 16px; cursor: pointer; border-left: 2px solid var(--line);
    transition: all 0.15s ease;
  }
  .tab-item:hover { color: var(--ink); }
  .tab-item.active { color: var(--neon); border-left-color: var(--neon); background: var(--neon-dim); }
  .tab-panel { background: var(--panel); border: 1px solid var(--line); padding: 30px; min-height: 260px; }
  .tab-panel h3 { font-size: 20px; margin-bottom: 16px; color: var(--neon); }
  .tab-panel .why-now { font-size: 10px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
  .tab-panel p { font-size: 13px; color: var(--muted); line-height: 1.75; margin-bottom: 18px; }
  .tab-panel .stat-line { font-size: 24px; font-weight: 800; color: var(--ink); margin-bottom: 4px; }
  .tab-cta {
    display: inline-block; font-size: 11px; font-weight: 700; color: var(--neon);
    border: 1px solid var(--neon); padding: 9px 18px; text-decoration: none; margin-top: 8px;
  }
  .tab-cta:hover { background: var(--neon); color: var(--bg); }

  .final { text-align: center; padding: 120px 24px; }
  .final h2 { font-size: 30px; font-weight: 800; text-transform: uppercase; margin-bottom: 30px; }
  .final h2 .neon { color: var(--neon); }

  @media (max-width: 800px) {
    .hero h1 { font-size: 40px; }
    .compare-row { grid-template-columns: 1fr; gap: 10px; }
    .tabs-wrap { grid-template-columns: 1fr; }
    .nav-right a:not(.demo-btn) { display: none; }
  }
</style>
</head>
<body>
<div class="bg-fixed"></div>

<nav>
  <div class="brand">RISK<span>GATE</span></div>
  <div class="nav-right">
    <a href="#tracks">Capabilities</a>
    <div class="sound-toggle" id="sound-toggle">&#9834; SOUND OFF</div>
    <a class="demo-btn" href="checkout.html">Deploy Sentinel</a>
  </div>
</nav>

<section class="hero" id="hero">
  <div class="hero-inner" id="hero-inner">
    <div class="tag">agent-transaction risk layer</div>
    <h1>Stop Fraud<br>Before It <span class="neon">Ships.</span></h1>
    <p class="sub">When an AI agent buys on someone's behalf, it can be fully authorized and still get it wrong. RiskGate scores fraud-risk, intent-match, and preference-fit — live, on every transaction.</p>
    <a class="cta" href="checkout.html">Deploy Sentinel &#9656;</a>
  </div>
  <div class="scroll-hint">SCROLL TO SEE HOW &#8595;</div>
</section>
<div class="hero-spacer"></div>

<section class="section">
  <div class="reveal">
    <div class="section-label">// legacy rules vs. real-time proof</div>
    <div class="compare-row">
      <div class="compare-old">Static Rule-Based Blocking</div>
      <div class="compare-new">Tested on 284,807 Real Transactions<span class="cite">XGBoost vs logistic regression, held-out Kaggle validation</span></div>
    </div>
    <div class="compare-row">
      <div class="compare-old">One Threshold, One Bucket</div>
      <div class="compare-new">Two-Tier Gating<span class="cite">Full review reserved for high-confidence fraud only</span></div>
    </div>
    <div class="compare-row">
      <div class="compare-old">Trust the Score Blindly</div>
      <div class="compare-new">Bootstrap-Audited Fairness<span class="cite">Every geographic disparity checked against noise, not assumed real</span></div>
    </div>
    <div class="compare-row">
      <div class="compare-old">Black-Box Decisions</div>
      <div class="compare-new">SHAP-Explained, Per Transaction<span class="cite">Every flag traceable to the exact signals behind it</span></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="reveal">
    <div class="section-label">// the loop</div>
    <div class="steps-list">
      <div class="step-row">
        <div class="step-num">01</div>
        <div class="step-body">
          <h3>Agent Proposes a Purchase</h3>
          <p>A real human intent goes to the shopping agent, which proposes an actual catalog match — in or out of budget.</p>
        </div>
      </div>
      <div class="step-row">
        <div class="step-num">02</div>
        <div class="step-body">
          <h3>RiskGate Scores It, Live</h3>
          <p>Fraud-risk, intent-match, and preference-fit are computed in one call — no black-box, every score traceable.</p>
        </div>
      </div>
      <div class="step-row">
        <div class="step-num">03</div>
        <div class="step-body">
          <h3>Gate Decides</h3>
          <p>Approve, quick-verify, confirm-with-human, or hold for fraud review — the right action for the right confidence level.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section" id="tracks">
  <div class="reveal">
    <div class="section-label">// capabilities</div>
    <div class="tabs-wrap">
      <div class="tabs-sidebar" id="tabs-sidebar">
        <button class="tab-item active" data-tab="0">01 Fraud Scoring</button>
        <button class="tab-item" data-tab="1">02 Ring Detection</button>
        <button class="tab-item" data-tab="2">03 Spike Detection</button>
        <button class="tab-item" data-tab="3">04 Fairness Audit</button>
      </div>
      <div class="tab-panel" id="tab-panel"></div>
    </div>
  </div>
</section>

<div class="final reveal">
  <h2>See It <span class="neon">Decide,</span> Live.</h2>
  <a class="cta" href="checkout.html">Deploy Sentinel &#9656;</a>
</div>

<script>
  // hero fade on scroll
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    const fade = Math.max(0, 1 - y / 400);
    const heroInner = document.getElementById('hero-inner');
    heroInner.style.opacity = fade;
    heroInner.style.transform = `translateY(${(1 - fade) * -40}px)`;
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('in-view'); });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  // sound toggle (no actual audio file — just a UI toggle, honest no-op)
  let soundOn = false;
  document.getElementById('sound-toggle').addEventListener('click', function() {
    soundOn = !soundOn;
    this.textContent = soundOn ? '\u266a SOUND ON' : '\u266a SOUND OFF';
  });

  // tabbed capabilities, real content
  const TAB_DATA = [
    {
      title: 'Fraud Scoring',
      whyNow: 'core detection layer',
      body: "Calibrated XGBoost, tested against logistic regression on 284,807 real transactions before being trusted for production. Two-tier threshold (0.25 / 0.45) reserves full manual review for genuinely high-confidence fraud only.",
      stat: 'F2 0.856', statLabel: 'vs logistic regression 0.707, real held-out data',
    },
    {
      title: 'Ring Detection',
      whyNow: 'coordinated abuse',
      body: "A union-find graph algorithm groups transactions sharing pincode, tight time windows, and fresh-agent status — catching coordinated fraud rings a per-transaction score alone would miss entirely.",
      stat: '100%', statLabel: '15 of 15 injected rings fully recovered, 92.3% precision',
    },
    {
      title: 'Spike Detection',
      whyNow: 'aggregate-rate anomalies',
      body: "A genuinely different problem shape: does the fraud RATE over a time window look statistically abnormal, even if no single transaction looks alarming alone? Median + MAD, not mean/std — robust to outliers by design.",
      stat: '167', statLabel: 'time buckets scanned, 11 flagged as anomalous',
    },
    {
      title: 'Fairness Audit',
      whyNow: 'geographic equity',
      body: "Empirical-Bayes shrinkage on pincode-level rates, plus bootstrap confidence intervals on every disparity — reported honestly as statistical noise or a confirmed bias, never assumed.",
      stat: '2.15x', statLabel: 'worst-case disparity, not distinguishable from noise',
    },
  ];

  function renderTab(idx) {
    const d = TAB_DATA[idx];
    document.getElementById('tab-panel').innerHTML = `
      <div class="why-now">${d.whyNow}</div>
      <h3>${d.title}</h3>
      <p>${d.body}</p>
      <div class="stat-line">${d.stat}</div>
      <div style="font-size:11px;color:var(--dim);margin-bottom:10px;">${d.statLabel}</div>
      <a class="tab-cta" href="checkout.html">Apply this track &#9656;</a>
    `;
  }
  document.querySelectorAll('.tab-item').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTab(parseInt(btn.dataset.tab));
    });
  });
  renderTab(0);
</script>
</body>
</html>
'''

with open(path, "w") as f:
    f.write(new_content)

print("second landing page built successfully")
