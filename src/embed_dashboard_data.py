"""
Re-embeds dashboard/demo_data.json and dashboard/agg_stats.json directly
into dashboard/index.html, so the dashboard works as a single, portable
HTML file (openable without a local server) in addition to its live mode.

Run this AFTER build_dashboard_data.py, whenever the underlying data has
changed and you want the standalone file to reflect it.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import re

dashboard_dir = f"{BASE_DIR}/dashboard"

with open(f"{dashboard_dir}/index.html") as f:
    html = f.read()
with open(f"{dashboard_dir}/demo_data.json") as f:
    demo_data = f.read()
with open(f"{dashboard_dir}/agg_stats.json") as f:
    agg_stats = f.read()

html = re.sub(
    r'(<script id="demo-data" type="application/json">).*?(</script>)',
    lambda m: m.group(1) + demo_data + m.group(2),
    html, flags=re.DOTALL,
)
html = re.sub(
    r'(<script id="agg-stats" type="application/json">).*?(</script>)',
    lambda m: m.group(1) + agg_stats + m.group(2),
    html, flags=re.DOTALL,
)

with open(f"{dashboard_dir}/index.html", "w") as f:
    f.write(html)

print("Re-embedded demo_data.json and agg_stats.json into dashboard/index.html")
