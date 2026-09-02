import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old = '''document.getElementById('confirm-btn').addEventListener('click', async () => {
  showStage('stage-processing');
  await sleep(1600);
  showStage('stage-done');
});'''

new = '''document.getElementById('confirm-btn').addEventListener('click', async () => {
  showStage('stage-processing');
  await sleep(1600);
  showStage('stage-done');

  // Persist THIS transaction's real result so the dashboard can show the
  // exact same decision across Consumer/Merchant/Razorpay/Fraud queue,
  // instead of each tab showing an unrelated random sample. Only stored
  // when we actually have a live API result — if the API wasn't running,
  // liveResult is null and the dashboard falls back to its own replay data.
  if (liveResult) {
    try {
      localStorage.setItem('riskgate_live_txn', JSON.stringify(liveResult));
    } catch (e) { /* localStorage unavailable — dashboard falls back to replay */ }
  }
});'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
