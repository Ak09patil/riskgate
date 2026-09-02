import sys

path = "landing3.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''  .stat-cycle { min-height: 44px; margin-bottom: 30px; position: relative; }
  .stat-slide {
    position: absolute; top: 0; left: 0; font-family: var(--mono); font-size: 13px; color: var(--muted);
    opacity: 0; transform: translateY(8px); transition: opacity 0.5s ease, transform 0.5s ease;
    max-width: 480px; line-height: 1.6;
  }
  .stat-slide.active { opacity: 1; transform: none; }
  .stat-slide .stat-hl { color: var(--go); font-weight: 700; }'''

new1 = '''  .stat-cycle {
    min-height: 76px; margin-bottom: 30px; position: relative; max-width: 500px;
    background: var(--panel); border: 1px solid var(--line-bright); border-radius: 8px;
    padding: 16px 18px 16px 16px; box-shadow: 0 0 24px rgba(94,255,157,0.06);
  }
  .stat-cycle-inner { position: relative; min-height: 44px; padding-left: 26px; }
  .stat-cycle-inner::before {
    content: '\\25c9'; position: absolute; left: 0; top: 1px; color: var(--go); font-size: 14px;
    text-shadow: 0 0 8px var(--go-glow);
  }
  .stat-slide {
    position: absolute; top: 0; left: 26px; right: 0; font-family: var(--mono); font-size: 13px; color: var(--ink);
    opacity: 0; transform: translateY(8px); transition: opacity 0.5s ease, transform 0.5s ease;
    line-height: 1.6;
  }
  .stat-slide.active { opacity: 1; transform: none; }
  .stat-slide .stat-hl { color: var(--go); font-weight: 700; }
  .stat-dots { display: flex; gap: 6px; margin-top: 12px; padding-left: 26px; }
  .stat-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--line-bright); opacity: 0.4; transition: all 0.3s ease; }
  .stat-dot.active { background: var(--go); opacity: 1; box-shadow: 0 0 6px var(--go-glow); width: 16px; border-radius: 3px; }'''

if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''    <div class="stat-cycle" id="stat-cycle">
      <div class="stat-slide active"><span class="stat-hl">F2 0.856</span> vs 0.707 logistic regression \u2014 validated on 284,807 real transactions, not just synthetic data.</div>
      <div class="stat-slide"><span class="stat-hl">100%</span> of injected coordinated-abuse rings recovered, 92.3% precision \u2014 a real detection algorithm, not a heuristic.</div>
      <div class="stat-slide"><span class="stat-hl">2.15x</span> worst-case pincode disparity \u2014 bootstrap-confirmed as statistical noise, not a hidden bias.</div>
      <div class="stat-slide"><span class="stat-hl">39/39</span> tests passing, including 3 that caught real production bugs during migration.</div>
    </div>'''

new2 = '''    <div class="stat-cycle" id="stat-cycle">
      <div class="stat-cycle-inner">
        <div class="stat-slide active"><span class="stat-hl">F2 0.856</span> vs 0.707 logistic regression \u2014 validated on 284,807 real transactions, not just synthetic data.</div>
        <div class="stat-slide"><span class="stat-hl">100%</span> of injected coordinated-abuse rings recovered, 92.3% precision \u2014 a real detection algorithm, not a heuristic.</div>
        <div class="stat-slide"><span class="stat-hl">2.15x</span> worst-case pincode disparity \u2014 bootstrap-confirmed as statistical noise, not a hidden bias.</div>
        <div class="stat-slide"><span class="stat-hl">39/39</span> tests passing, including 3 that caught real production bugs during migration.</div>
      </div>
      <div class="stat-dots">
        <div class="stat-dot active"></div><div class="stat-dot"></div><div class="stat-dot"></div><div class="stat-dot"></div>
      </div>
    </div>'''

if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''  const statSlides = document.querySelectorAll('.stat-slide');
  let statIdx = 0;
  setInterval(() => {
    statSlides[statIdx].classList.remove('active');
    statIdx = (statIdx + 1) % statSlides.length;
    statSlides[statIdx].classList.add('active');
  }, 2500);'''

new3 = '''  const statSlides = document.querySelectorAll('.stat-slide');
  const statDots = document.querySelectorAll('.stat-dot');
  let statIdx = 0;
  setInterval(() => {
    statSlides[statIdx].classList.remove('active');
    statDots[statIdx].classList.remove('active');
    statIdx = (statIdx + 1) % statSlides.length;
    statSlides[statIdx].classList.add('active');
    statDots[statIdx].classList.add('active');
  }, 2500);'''

if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
