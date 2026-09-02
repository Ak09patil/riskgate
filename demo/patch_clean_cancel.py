import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old1 = '      <button class="btn primary" id="confirm-btn">Confirm purchase</button>'
new1 = '''      <button class="btn primary" id="confirm-btn">Confirm purchase</button>
      <button class="btn ghost" id="clean-cancel-btn">Cancel this order</button>'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''document.getElementById('confirm-btn').addEventListener('click', async () => {
  await sleep(500); // brief pause so the flow doesn't feel instant/fake
  routeByDecision();
});'''
new2 = '''document.getElementById('confirm-btn').addEventListener('click', async () => {
  await sleep(500); // brief pause so the flow doesn't feel instant/fake
  routeByDecision();
});
document.getElementById('clean-cancel-btn').addEventListener('click', () => {
  // Cancel option for a clean/AUTO_APPROVE transaction too - a customer
  // should always be able to back out, not just when the system flags
  // something. Previously only HOLD_* decisions offered this.
  setRiskGateLinks();
  showStage('stage-cancelled');
});'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
