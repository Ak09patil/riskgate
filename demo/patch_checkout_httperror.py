import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old = '''    if (res.ok) {
      const json = await res.json();
      if (json.status === 'SCORED') return json;
    }
  } catch (e) {
    console.error('[RiskGate demo] fetchLive failed:', e.name, e.message, e);
  }
  return null;
}'''

new = '''    if (res.ok) {
      const json = await res.json();
      if (json.status === 'SCORED') return json;
      console.warn('[RiskGate demo] fetchLive got 200 but status was not SCORED:', json);
    } else {
      // fetch() does NOT throw on HTTP error status codes (400/500) -
      // only on network-level failures. This is the actual gap that
      // let real backend errors silently return null with no log at
      // all, even with try/catch in place.
      const bodyText = await res.text().catch(() => '(could not read body)');
      console.error('[RiskGate demo] fetchLive got a non-ok HTTP status:', res.status, res.statusText, bodyText);
    }
  } catch (e) {
    console.error('[RiskGate demo] fetchLive failed (network-level):', e.name, e.message, e);
  }
  return null;
}'''

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
