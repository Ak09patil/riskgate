import sys

path = "landing3.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''  .cta {
    font-family: var(--mono); font-size: 12px; font-weight: 700; letter-spacing: 0.02em;
    color: var(--bg); background: var(--go); border: none; padding: 15px 28px; border-radius: 4px;
    text-decoration: none; display: inline-block; box-shadow: 0 0 26px var(--go-glow);
  }'''
new1 = '''  .stat-cycle { min-height: 44px; margin-bottom: 30px; position: relative; }
  .stat-slide {
    position: absolute; top: 0; left: 0; font-family: var(--mono); font-size: 13px; color: var(--muted);
    opacity: 0; transform: translateY(8px); transition: opacity 0.5s ease, transform 0.5s ease;
    max-width: 480px; line-height: 1.6;
  }
  .stat-slide.active { opacity: 1; transform: none; }
  .stat-slide .stat-hl { color: var(--go); font-weight: 700; }
  .cta {
    font-family: var(--mono); font-size: 12px; font-weight: 700; letter-spacing: 0.02em;
    color: var(--bg); background: var(--go); border: none; padding: 15px 28px; border-radius: 4px;
    text-decoration: none; display: inline-block; box-shadow: 0 0 26px var(--go-glow);
  }'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''    <p class="sub">An AI agent buys on someone's behalf \u2014 fully authorized, still capable of getting it wrong. RiskGate scores fraud-risk, intent-match, and preference-fit on every transaction, live.</p>
    <a class="cta" href="checkout.html">Start the demo &#9656;</a>'''
new2 = '''    <p class="sub">An AI agent buys on someone's behalf \u2014 fully authorized, still capable of getting it wrong. RiskGate scores fraud-risk, intent-match, and preference-fit on every transaction, live.</p>
    <div class="stat-cycle" id="stat-cycle">
      <div class="stat-slide active"><span class="stat-hl">F2 0.856</span> vs 0.707 logistic regression \u2014 validated on 284,807 real transactions, not just synthetic data.</div>
      <div class="stat-slide"><span class="stat-hl">100%</span> of injected coordinated-abuse rings recovered, 92.3% precision \u2014 a real detection algorithm, not a heuristic.</div>
      <div class="stat-slide"><span class="stat-hl">2.15x</span> worst-case pincode disparity \u2014 bootstrap-confirmed as statistical noise, not a hidden bias.</div>
      <div class="stat-slide"><span class="stat-hl">39/39</span> tests passing, including 3 that caught real production bugs during migration.</div>
    </div>
    <a class="cta" href="checkout.html">Start the demo &#9656;</a>'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = "window.addEventListener('load', () => setTimeout(runFlow, 400));"
new3 = '''window.addEventListener('load', () => setTimeout(runFlow, 400));

  const statSlides = document.querySelectorAll('.stat-slide');
  let statIdx = 0;
  setInterval(() => {
    statSlides[statIdx].classList.remove('active');
    statIdx = (statIdx + 1) % statSlides.length;
    statSlides[statIdx].classList.add('active');
  }, 2500);'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
