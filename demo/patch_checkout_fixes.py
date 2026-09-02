import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old1 = '<input type="number" id="input-budget" value="4000" min="500" step="100">'
new1 = '<input type="number" id="input-budget" value="4000" min="500" max="100000" step="100">'
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old1b = "const maxPrice = parseFloat(document.getElementById('input-budget').value) || 4000;"
new1b = '''const rawBudget = parseFloat(document.getElementById('input-budget').value) || 4000;
  // Clamp defensively even if the input's max attribute gets bypassed
  // (e.g. pasting a value directly) - the circuit breaker checks the
  // AGENT'S PROPOSED order value, not this stated budget, so an absurd
  // budget here wouldn't trigger it anyway; this cap is purely so the
  // demo doesn't display a nonsensical number.
  const maxPrice = Math.min(rawBudget, 100000);'''
if old1b not in content:
    print("PATTERN 1B NOT FOUND")
    sys.exit(1)
content = content.replace(old1b, new1b)

old2 = "<script>"
new2 = '''<script>
// Detect bfcache restoration (Safari/Chrome can serve an already-executed
// page instead of truly reloading it on back/forward navigation, keeping
// old JS variables like liveResult alive) and force a real reload so
// every demo run starts from a genuinely clean state.
window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    window.location.reload();
  }
});
'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2, 1)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
