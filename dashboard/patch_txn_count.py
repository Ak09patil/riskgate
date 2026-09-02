import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '    <div class="live-pill"><span class="blip"></span>4,000 txns scored</div>'
new1 = '    <div class="live-pill"><span class="blip"></span><span id="txn-count-badge">... txns scored</span></div>'
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''let liveTxn = null;
try {
  const _params = new URLSearchParams(window.location.search);
  const _carried = _params.get('result');
  if (_carried) {
    liveTxn = JSON.parse(decodeURIComponent(_carried));
    liveTxn._isLive = true;
    demoData.unshift(liveTxn);
  }
} catch (e) { /* malformed/missing param — proceed with replay data only */ }'''
new2 = '''let liveTxn = null;
try {
  const _params = new URLSearchParams(window.location.search);
  const _carried = _params.get('result');
  if (_carried) {
    liveTxn = JSON.parse(decodeURIComponent(_carried));
    liveTxn._isLive = true;
    demoData.unshift(liveTxn);
  }
} catch (e) { /* malformed/missing param — proceed with replay data only */ }

// Real total, not hardcoded - was showing a stale "4,000" regardless of
// the actual dataset size, which drifted the moment the dataset was
// regenerated (currently 4,072 rows after the ring-rate feature work).
document.getElementById('txn-count-badge').textContent =
  `${aggStats.total_transactions.toLocaleString()} txns scored`;'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
