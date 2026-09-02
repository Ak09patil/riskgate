import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '      <div class="sim-result" id="sim-result"></div>'
new1 = '''      <div class="sim-result" id="sim-result"></div>
      <div class="decision-trace" id="decision-trace"></div>'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "  .card:hover { border-color: var(--line-bright); }"
new2 = '''  .card:hover { border-color: var(--line-bright); }
  .decision-trace {
    margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--line);
    opacity: 0; transition: opacity 0.4s ease;
  }
  .decision-trace.show { opacity: 1; }
  .decision-trace .trace-title {
    font-family: var(--mono); font-size: 10.5px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--dim); margin-bottom: 12px;
  }
  .trace-step {
    display: flex; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line);
    animation: rowIn 0.3s ease backwards;
  }
  .trace-step:last-child { border-bottom: none; }
  .trace-step .trace-icon {
    flex-shrink: 0; width: 18px; height: 18px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; margin-top: 1px;
  }
  .trace-step.pass .trace-icon { background: var(--go-dim); color: var(--go); }
  .trace-step.trigger .trace-icon { background: var(--stop-dim); color: var(--stop); }
  .trace-step.trigger.final-approve .trace-icon { background: var(--go-dim); color: var(--go); }
  .trace-step.trigger.final-verify .trace-icon { background: var(--verify-dim); color: var(--verify); }
  .trace-step.trigger.final-confirm .trace-icon { background: var(--amber-dim); color: var(--amber); }
  .trace-step.trigger.final-mismatch .trace-icon { background: var(--rose-dim); color: var(--rose); }
  .trace-step-body { flex: 1; }
  .trace-step-name { font-size: 12.5px; font-weight: 600; color: var(--ink); }
  .trace-step-detail { font-family: var(--mono); font-size: 11px; color: var(--muted); margin-top: 2px; }
  .trace-step-note { font-size: 11.5px; color: var(--dim); margin-top: 4px; line-height: 1.5; }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''  const b = badgeInfo(d.decision);
  simResult.innerHTML = `<span class="badge ${b.cls}">${b.label}</span>${d.reason}`;
  simResult.classList.add('show');
}
simBtn.addEventListener('click', runSimulation);'''
new3 = '''  const b = badgeInfo(d.decision);
  simResult.innerHTML = `<span class="badge ${b.cls}">${b.label}</span>${d.reason}`;
  simResult.classList.add('show');

  renderDecisionTrace(d);
}
simBtn.addEventListener('click', runSimulation);

// DECISION TRACE — walks the SAME gating order as score_transaction()
// in pipeline.py, step by step, using the SAME threshold constants
// (exported live from pipeline.py via agg_stats.json, not a separate
// hardcoded copy here).
function traceStepHtml(step, isLast, finalClass) {
  const cls = step.triggered ? 'trigger' : 'pass';
  const finalCls = (isLast && step.triggered) ? ` final-${finalClass}` : '';
  const icon = step.triggered ? (isLast ? '\\u25cf' : '\\u26a0') : '\\u2713';
  return `
    <div class="trace-step ${cls}${finalCls}">
      <div class="trace-icon">${icon}</div>
      <div class="trace-step-body">
        <div class="trace-step-name">${step.name}</div>
        <div class="trace-step-detail">${step.detail}</div>
        <div class="trace-step-note">${step.note}</div>
      </div>
    </div>`;
}

function renderDecisionTrace(d) {
  const cb = aggStats.circuit_breaker_max_order_value;
  const fth = aggStats.fraud_threshold_high;
  const ft = aggStats.fraud_threshold;
  const band = aggStats.fraud_borderline_band;
  const historyThresh = aggStats.trust_override_history_threshold;
  const prefThresh = aggStats.pref_fit_threshold;
  const intentThresh = aggStats.intent_threshold;

  const price = d.order_price;
  const fraud = d.fraud_risk_score;
  const history = d.user_past_over_budget_kept_rate;
  const cleanSignal = d.device_ip_consistency;
  const intent = d.intent_match_confidence;
  const pref = d.preference_fit_score;

  const steps = [];
  let finalClass = 'mismatch';

  const cbTriggered = price > cb;
  steps.push({
    name: '1. Circuit breaker',
    detail: `order value \\u20b9${price.toLocaleString('en-IN')} vs cap \\u20b9${cb.toLocaleString('en-IN')}`,
    triggered: cbTriggered,
    note: cbTriggered
      ? 'Order value far outside anything the model was trained on \\u2014 held for manual review regardless of model score.'
      : 'Within the range the model was trained on \\u2014 continue.',
  });

  if (!cbTriggered) {
    const highTriggered = fraud >= fth;
    steps.push({
      name: '2. High-confidence fraud check',
      detail: `fraud_risk_score ${fraud} vs threshold ${fth}`,
      triggered: highTriggered,
      note: highTriggered
        ? 'Confidently high fraud score \\u2014 full manual review, the trust override never even applies here by design.'
        : 'Below the high-confidence threshold \\u2014 continue.',
    });

    if (!highTriggered) {
      const floorTriggered = fraud >= ft;
      steps.push({
        name: '3. Ambiguous-band fraud check',
        detail: `fraud_risk_score ${fraud} vs threshold ${ft}`,
        triggered: floorTriggered,
        note: floorTriggered
          ? 'Above the floor \\u2014 checking the bounded trust override next.'
          : 'Below the floor \\u2014 continue to intent-match.',
      });

      if (floorTriggered) {
        const isBorderline = fraud < (ft + band);
        const hasHistory = (history !== undefined && history !== null) && history >= historyThresh;
        const hasClean = cleanSignal === 1;
        const overrideApplies = isBorderline && hasHistory && hasClean;
        steps.push({
          name: '4. Bounded trust override',
          detail: `needs: borderline (< ${(ft + band).toFixed(2)}) AND history \\u2265 ${historyThresh} AND clean device/IP \\u2014 got: ${isBorderline ? 'borderline' : 'not borderline'}, history ${history !== undefined ? history : 'n/a'}, device/IP ${cleanSignal === 1 ? 'clean' : 'mismatched'}`,
          triggered: overrideApplies,
          note: overrideApplies
            ? 'All three conditions met \\u2014 downgraded to a quick human confirmation instead of a hold. Two-factor by design: history alone is never enough, to resist trust-farming.'
            : 'Not all conditions met \\u2014 routed to a quick re-verification step instead of full review.',
        });
        finalClass = overrideApplies ? 'confirm' : 'verify';
      } else {
        const intentTriggered = intent >= intentThresh;
        steps.push({
          name: '4. Intent-match check',
          detail: `intent_match_confidence ${intent} vs threshold ${intentThresh}`,
          triggered: intentTriggered,
          note: intentTriggered
            ? 'Low fraud risk and high intent match \\u2014 auto-approved.'
            : 'Deviates from the original stated intent \\u2014 continue to preference-fit.',
        });
        finalClass = 'approve';

        if (!intentTriggered) {
          const prefTriggered = pref >= prefThresh;
          steps.push({
            name: '5. Preference-fit check',
            detail: `preference_fit_score ${pref} vs threshold ${prefThresh}`,
            triggered: prefTriggered,
            note: prefTriggered
              ? 'History suggests this customer may welcome the deviation \\u2014 routed to a human confirmation instead of an auto-block.'
              : 'Doesn\\'t align with this customer\\'s history either \\u2014 likely a mistaken purchase, held to prevent a probable return.',
          });
          finalClass = prefTriggered ? 'confirm' : 'mismatch';
        }
      }
    } else {
      finalClass = 'fraud';
    }
  } else {
    finalClass = 'fraud';
  }

  const traceEl = document.getElementById('decision-trace');
  const html = steps.map((s, i) => traceStepHtml(s, i === steps.length - 1, finalClass)).join('');
  traceEl.innerHTML = `<div class="trace-title">// Decision Trace \\u2014 same gating order as pipeline.py, live</div>${html}`;
  traceEl.classList.add('show');
}'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
