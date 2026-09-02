import sys

path = "index.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''    default: return {cls:'mismatch', label: decision || 'Unknown'};
  }
}'''
new1 = '''    default: return {cls:'mismatch', label: decision || 'Unknown'};
  }
}

// Formats an ISO timestamp as a short, readable time — used on Consumer
// cards and Merchant rows so a judge can see WHEN a transaction happened
// without parsing a raw ISO string.
function formatTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch (e) { return ''; }
}'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''        <div class="item-line">${d.order_category[0].toUpperCase()+d.order_category.slice(1)} order</div>
        <div class="price">₹${d.order_price.toLocaleString('en-IN')} · intent budget ₹${d.intent_max_price.toLocaleString('en-IN')}</div>
      </div>
      <span class="badge ${b.cls}">${b.label}</span>
    </div>
    <div class="reason">${d.reason}</div>
  `;'''
new2 = '''        <div class="item-line">${d.order_category[0].toUpperCase()+d.order_category.slice(1)} order</div>
        <div class="price">₹${d.order_price.toLocaleString('en-IN')} · intent budget ₹${d.intent_max_price.toLocaleString('en-IN')}</div>
        <div class="context-line">${formatTime(d.timestamp)}${d.payment_mode ? ' · ' + d.payment_mode : ''}${d.pincode ? ' · pincode ' + d.pincode : ''}${(d.agent_age_days !== undefined) ? ' · agent ' + d.agent_age_days + 'd old' : ''}</div>
      </div>
      <span class="badge ${b.cls}">${b.label}</span>
    </div>
    <div class="reason">${d.reason}</div>
  `;'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old3 = '''      <td class="mono">${d._isLive ? '\\u25cf LIVE ' : ''}${d.order_id}</td>
      <td>${d.order_category}</td>'''
new3 = '''      <td class="mono">${d._isLive ? '\\u25cf LIVE ' : ''}${d.order_id}<div class="context-sub">${formatTime(d.timestamp)}</div></td>
      <td>${d.order_category}<div class="context-sub">${d.payment_mode || ''}${d.pincode ? ' \\u00b7 ' + d.pincode : ''}${(d.agent_age_days !== undefined) ? ' \\u00b7 agent ' + d.agent_age_days + 'd' : ''}</div></td>'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = "  .card:hover { border-color: var(--line-bright); }"
new4 = '''  .card:hover { border-color: var(--line-bright); }
  .context-line { font-family: var(--mono); font-size: 10.5px; color: var(--dim); margin-top: 4px; }
  .context-sub { font-family: var(--mono); font-size: 10px; color: var(--dim); margin-top: 2px; }'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
