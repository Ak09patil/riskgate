import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''        <div class="uth-num">39/39</div>
        <div class="uth-label">tests passing</div>'''
new1 = '''        <div class="uth-num">39/39</div>
        <div class="uth-label">tests passing <span class="uth-src">synthetic + real</span></div>'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''        <div class="uth-num">92.3% / 100%</div>
        <div class="uth-label">ring detector: precision / recall</div>'''
new2 = '''        <div class="uth-num">92.3% / 100%</div>
        <div class="uth-label">ring detector: precision / recall <span class="uth-src">synthetic, injected ground truth</span></div>'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''        <div class="uth-num">54.5% / 54.5%</div>
        <div class="uth-label">spike detector: precision / recall</div>'''
new3 = '''        <div class="uth-num">54.5% / 54.5%</div>
        <div class="uth-label">spike detector: precision / recall <span class="uth-src">synthetic, injected ground truth</span></div>'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = '''        <div class="uth-num">0.229 \\u2192 0.194</div>
        <div class="uth-label">calibration (Brier score)</div>'''
new4 = '''        <div class="uth-num">0.229 \\u2192 0.194</div>
        <div class="uth-label">calibration (Brier score) <span class="uth-src">synthetic (production training data)</span></div>'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

old5 = '''        <div class="uth-num">2.15x</div>
        <div class="uth-label">worst-case pincode disparity</div>'''
new5 = '''        <div class="uth-num">2.15x</div>
        <div class="uth-label">worst-case pincode disparity <span class="uth-src">synthetic (production training data)</span></div>'''
if old5 not in content:
    print("PATTERN 5 NOT FOUND")
    sys.exit(1)
content = content.replace(old5, new5)

old6 = '''        <div class="uth-num">~168 req/s</div>
        <div class="uth-label">measured throughput</div>'''
new6 = '''        <div class="uth-num">~168 req/s</div>
        <div class="uth-label">measured throughput <span class="uth-src">architecture test, data-source independent</span></div>'''
if old6 not in content:
    print("PATTERN 6 NOT FOUND")
    sys.exit(1)
content = content.replace(old6, new6)

old7 = '''      <div class="uth-compare-title">// why this model, not the alternatives</div>
      <div class="uth-compare-row">
        <div class="uth-compare-label">vs. a hand-written rule</div>'''
new7 = '''      <div class="uth-compare-title">// why this model, not the alternatives</div>
      <div class="uth-compare-note">Deliberately mixed evidence: synthetic data for pipeline/architecture testing and detectors where labeled real fraud rings don't exist publicly; real external data specifically to validate the core model-choice decision (the one claim synthetic data can mislead on).</div>
      <div class="uth-compare-row">
        <div class="uth-compare-label">vs. a hand-written rule <span class="uth-src">synthetic</span></div>'''
if old7 not in content:
    print("PATTERN 7 NOT FOUND")
    sys.exit(1)
content = content.replace(old7, new7)

old8 = '<div class="uth-compare-label">vs. logistic regression, real data</div>'
new8 = '<div class="uth-compare-label">vs. logistic regression, real data <span class="uth-src">real (Kaggle, 284,807 rows)</span></div>'
if old8 not in content:
    print("PATTERN 8 NOT FOUND")
    sys.exit(1)
content = content.replace(old8, new8)

old9 = '<div class="uth-compare-label">vs. logistic regression, our synthetic data</div>'
new9 = '<div class="uth-compare-label">vs. logistic regression, our synthetic data <span class="uth-src">synthetic</span></div>'
if old9 not in content:
    print("PATTERN 9 NOT FOUND")
    sys.exit(1)
content = content.replace(old9, new9)

old10 = "  .uth-detail { font-size: 11.5px; color: var(--muted); line-height: 1.55; }"
new10 = '''  .uth-detail { font-size: 11.5px; color: var(--muted); line-height: 1.55; }
  .uth-src {
    display: inline-block; font-size: 9px; font-weight: 600; color: var(--dim);
    background: var(--panel-2); border: 1px solid var(--line); padding: 2px 6px;
    border-radius: 4px; margin-left: 6px; text-transform: none; letter-spacing: 0;
    vertical-align: middle;
  }
  .uth-compare-note { font-size: 11px; color: var(--dim); line-height: 1.5; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px dashed var(--line); }'''
if old10 not in content:
    print("PATTERN 10 NOT FOUND")
    sys.exit(1)
content = content.replace(old10, new10)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
