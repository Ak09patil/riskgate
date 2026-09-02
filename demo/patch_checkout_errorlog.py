import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old1 = '''async function checkApi() {
  try {
    const res = await fetch('http://localhost:5050/full_loop', { signal: AbortSignal.timeout(3000) });
    apiIsUp = res.ok;
  } catch (e) { apiIsUp = false; }
}'''
new1 = '''async function checkApi() {
  try {
    const res = await fetch('http://localhost:5050/full_loop', { signal: AbortSignal.timeout(3000) });
    apiIsUp = res.ok;
  } catch (e) {
    apiIsUp = false;
    console.warn('[RiskGate demo] checkApi failed:', e.name, e.message);
  }
}'''
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = '''    if (json.status === 'SCORED') return json;
    }
  } catch (e) {}
  return null;
}'''
new2 = '''    if (json.status === 'SCORED') return json;
    }
  } catch (e) {
    console.error('[RiskGate demo] fetchLive failed:', e.name, e.message, e);
  }
  return null;
}'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
