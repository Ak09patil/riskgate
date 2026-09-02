import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = "    --verify-glow: rgba(94,200,255,0.16);"
new1 = '''    --verify-glow: rgba(94,200,255,0.16);
    --rose: #ff8a7a;
    --rose-dim: #3d241c;
    --rose-glow: rgba(255,138,122,0.16);'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "  .badge.confirm, .badge.mismatch { background: var(--amber-dim); color: var(--amber); border-color: rgba(255,180,84,0.25); }"
new2 = '''  .badge.confirm { background: var(--amber-dim); color: var(--amber); border-color: rgba(255,180,84,0.25); }
  .badge.mismatch { background: var(--rose-dim); color: var(--rose); border-color: rgba(255,138,122,0.25); }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''  .stat.confirm, .stat.mismatch { --stat-color: var(--amber); }
  .stat.confirm .num, .stat.mismatch .num { color: var(--amber); }
  .stat.verify { --stat-color: var(--verify); }
  .stat.verify .num { color: var(--verify); }'''
new3 = '''  .stat.confirm { --stat-color: var(--amber); }
  .stat.confirm .num { color: var(--amber); }
  .stat.mismatch { --stat-color: var(--rose); }
  .stat.mismatch .num { color: var(--rose); }
  .stat.verify { --stat-color: var(--verify); }
  .stat.verify .num { color: var(--verify); }'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = '''  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }
  .bar-fill.verify { background: var(--verify); box-shadow: 0 0 10px var(--verify-glow) inset; }
  .bar-fill.mismatch { background: #d99a3f; }'''
new4 = '''  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }
  .bar-fill.verify { background: var(--verify); box-shadow: 0 0 10px var(--verify-glow) inset; }
  .bar-fill.mismatch { background: var(--rose); box-shadow: 0 0 10px var(--rose-glow) inset; }'''
if old4 in content:
    content = content.replace(old4, new4)
else:
    old4b = '''  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }
  .bar-fill.mismatch { background: #d99a3f; }'''
    new4b = '''  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }
  .bar-fill.mismatch { background: var(--rose); box-shadow: 0 0 10px var(--rose-glow) inset; }'''
    if old4b not in content:
        print("PATTERN 4 NOT FOUND (both variants)")
        sys.exit(1)
    content = content.replace(old4b, new4b)

old5 = "    case 'HOLD_LIKELY_MISMATCH': return {cls:'mismatch', label:'Likely mismatch'};"
new5 = "    case 'HOLD_LIKELY_MISMATCH': return {cls:'mismatch', label:'Held: mismatch'};"
if old5 not in content:
    print("PATTERN 5 NOT FOUND")
    sys.exit(1)
content = content.replace(old5, new5)

old6 = '''const statDefs = [
  {key:'AUTO_APPROVE', label:'auto-approved', cls:'approve'},
  {key:'HOLD_FRAUD_REVIEW', label:'fraud review', cls:'fraud'},
  {key:'HOLD_CONFIRM_WITH_HUMAN', label:'confirm w/ human', cls:'confirm'},
  {key:'HOLD_LIKELY_MISMATCH', label:'likely mismatch', cls:'mismatch'},
];'''
new6 = '''const statDefs = [
  {key:'AUTO_APPROVE', label:'auto-approved', cls:'approve'},
  {key:'HOLD_QUICK_VERIFY', label:'quick verify', cls:'verify'},
  {key:'HOLD_FRAUD_REVIEW', label:'fraud review', cls:'fraud'},
  {key:'HOLD_CONFIRM_WITH_HUMAN', label:'confirm w/ human', cls:'confirm'},
  {key:'HOLD_LIKELY_MISMATCH', label:'held: mismatch', cls:'mismatch'},
];'''
if old6 not in content:
    print("PATTERN 6 NOT FOUND")
    sys.exit(1)
content = content.replace(old6, new6)

old7 = '''      <button data-filter="AUTO_APPROVE">Approved</button>
      <button data-filter="HOLD_FRAUD_REVIEW">Fraud review</button>'''
new7 = '''      <button data-filter="AUTO_APPROVE">Approved</button>
      <button data-filter="HOLD_QUICK_VERIFY">Quick verify</button>
      <button data-filter="HOLD_FRAUD_REVIEW">Fraud review</button>'''
if old7 not in content:
    print("PATTERN 7 NOT FOUND")
    sys.exit(1)
content = content.replace(old7, new7)

old8 = '<button data-filter="HOLD_LIKELY_MISMATCH">Mismatch</button>'
new8 = '<button data-filter="HOLD_LIKELY_MISMATCH">Held: mismatch</button>'
if old8 not in content:
    print("PATTERN 8 NOT FOUND")
    sys.exit(1)
content = content.replace(old8, new8)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
