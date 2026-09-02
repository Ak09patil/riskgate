import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''document.getElementById('gate-cancel-btn-early').addEventListener('click', () => {
  showStage('stage-cancelled');
});'''
new1 = '''document.getElementById('gate-cancel-btn-early').addEventListener('click', () => {
  setRiskGateLinks();
  showStage('stage-cancelled');
});'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''document.getElementById('gate-cancel-btn').addEventListener('click', () => {
  showStage('stage-cancelled');
});'''
new2 = '''document.getElementById('gate-cancel-btn').addEventListener('click', () => {
  setRiskGateLinks();
  showStage('stage-cancelled');
});'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = "<script>"
new3 = '''<script>
// FRAUD_THRESHOLD mirrors pipeline.py's real value - used here only to
// distinguish WHICH path led to HOLD_CONFIRM_WITH_HUMAN (trust override
// vs pref-fit), not to make any gating decision itself.
const FRAUD_THRESHOLD_FOR_MESSAGING = 0.25;

function getHoldConfirmReason(liveResult) {
  if (liveResult.fraud_risk_score >= FRAUD_THRESHOLD_FOR_MESSAGING) {
    return "This order had a borderline risk score, but your account history and a clean device check let us skip straight to a quick confirmation instead of a full review.";
  }
  if (liveResult.matched_rule === 'over_budget_closest_available') {
    return "This went a bit outside your usual budget for this category \\u2014 but it matches things you\\'ve bought before.";
  }
  if (liveResult.matched_rule === 'category_in_budget_attribute_mismatch') {
    return "This wasn\\'t quite the exact variant you asked for \\u2014 but it matches things you\\'ve bought before.";
  }
  return "This deviated a bit from what you originally asked for \\u2014 but it matches things you\\'ve bought before.";
}

function getMismatchReason(liveResult) {
  if (liveResult.matched_rule === 'over_budget_closest_available') {
    return "Heads up \\u2014 this went further outside your budget than we\\'d normally let through without checking, and it doesn\\'t match your usual pattern either. We\\'d recommend double-checking before this goes through.";
  }
  if (liveResult.matched_rule === 'category_in_budget_attribute_mismatch') {
    return "Heads up \\u2014 this isn\\'t the variant you asked for, and it doesn\\'t match your usual pattern either. We\\'d recommend double-checking before this goes through.";
  }
  return "Heads up \\u2014 this doesn\\'t quite match what you originally asked for. We\\'d recommend double-checking before this goes through.";
}

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
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3, 1)

old4 = '''      preNote.innerHTML = decision === 'HOLD_CONFIRM_WITH_HUMAN'
        ? '<span class="why-title">Before you confirm</span>This went a bit outside your usual budget for this category — but it matches things you\\'ve bought before.'
        : '<span class="why-title">Before you confirm</span>This doesn\\'t quite match what you originally asked for (budget, size, or category).';'''
new4 = '''      preNote.innerHTML = decision === 'HOLD_CONFIRM_WITH_HUMAN'
        ? '<span class="why-title">Before you confirm</span>' + getHoldConfirmReason(liveResult)
        : '<span class="why-title">Before you confirm</span>' + getMismatchReason(liveResult);'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

old5 = '''  } else if (decision === 'HOLD_CONFIRM_WITH_HUMAN') {
    gateMessage.innerHTML = "This order went a bit outside your usual budget for this category — but it matches things you've bought before. Want to go ahead anyway?";
    showStage('stage-gate');
  } else if (decision === 'HOLD_LIKELY_MISMATCH') {
    gateMessage.innerHTML = "Heads up — this doesn't quite match what you originally asked for (budget, size, or category). We'd recommend double-checking before this goes through.";
    showStage('stage-gate');'''
new5 = '''  } else if (decision === 'HOLD_CONFIRM_WITH_HUMAN') {
    gateMessage.innerHTML = getHoldConfirmReason(liveResult) + " Want to go ahead anyway?";
    showStage('stage-gate');
  } else if (decision === 'HOLD_LIKELY_MISMATCH') {
    gateMessage.innerHTML = getMismatchReason(liveResult);
    showStage('stage-gate');'''
if old5 not in content:
    print("PATTERN 5 NOT FOUND")
    sys.exit(1)
content = content.replace(old5, new5)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
