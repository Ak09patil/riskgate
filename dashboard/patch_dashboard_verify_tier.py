import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = "    --amber-glow: rgba(255,180,84,0.16);"
new1 = '''    --amber-glow: rgba(255,180,84,0.16);
    --verify: #5ec8ff;
    --verify-dim: #1c2f3d;
    --verify-glow: rgba(94,200,255,0.16);'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "  .badge.confirm, .badge.mismatch { background: var(--amber-dim); color: var(--amber); border-color: rgba(255,180,84,0.25); }"
new2 = '''  .badge.confirm, .badge.mismatch { background: var(--amber-dim); color: var(--amber); border-color: rgba(255,180,84,0.25); }
  .badge.verify { background: var(--verify-dim); color: var(--verify); border-color: rgba(94,200,255,0.25); }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''  .stat.confirm, .stat.mismatch { --stat-color: var(--amber); }
  .stat.confirm .num, .stat.mismatch .num { color: var(--amber); }'''
new3 = '''  .stat.confirm, .stat.mismatch { --stat-color: var(--amber); }
  .stat.confirm .num, .stat.mismatch .num { color: var(--amber); }
  .stat.verify { --stat-color: var(--verify); }
  .stat.verify .num { color: var(--verify); }'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = "  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }"
new4 = '''  .bar-fill.confirm { background: var(--amber); box-shadow: 0 0 10px var(--amber-glow) inset; }
  .bar-fill.verify { background: var(--verify); box-shadow: 0 0 10px var(--verify-glow) inset; }'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

old5 = '''function badgeInfo(decision) {
  switch(decision) {
    case 'AUTO_APPROVE': return {cls:'approve', label:'Approved'};
    case 'HOLD_FRAUD_REVIEW': return {cls:'fraud', label:'Fraud review'};
    case 'HOLD_CONFIRM_WITH_HUMAN': return {cls:'confirm', label:'Confirm with you'};
    case 'HOLD_LIKELY_MISMATCH': return {cls:'mismatch', label:'Likely mismatch'};
  }
}'''
new5 = '''function badgeInfo(decision) {
  switch(decision) {
    case 'AUTO_APPROVE': return {cls:'approve', label:'Approved'};
    case 'HOLD_QUICK_VERIFY': return {cls:'verify', label:'Quick verify'};
    case 'HOLD_FRAUD_REVIEW': return {cls:'fraud', label:'Fraud review'};
    case 'HOLD_CONFIRM_WITH_HUMAN': return {cls:'confirm', label:'Confirm with you'};
    case 'HOLD_LIKELY_MISMATCH': return {cls:'mismatch', label:'Likely mismatch'};
    default: return {cls:'mismatch', label: decision || 'Unknown'};
  }
}'''
if old5 not in content:
    print("PATTERN 5 NOT FOUND")
    sys.exit(1)
content = content.replace(old5, new5)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
