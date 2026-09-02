import sys

path = "checkout.html"

with open(path, "r") as f:
    content = f.read()

old1 = "const res = await fetch('http://localhost:5050/full_loop', { signal: AbortSignal.timeout(1000) });"
new1 = "const res = await fetch('http://localhost:5050/full_loop', { signal: AbortSignal.timeout(3000) });"
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, new1)

old2 = "      signal: AbortSignal.timeout(2000),"
new2 = '''      // Raised from 2000ms: the Flask dev server processes requests
      // serially (Python's GIL, on CPU-bound model scoring - see
      // load_test.py's documented finding), so under any concurrent
      // load (e.g. multiple demo tabs open at once) a request can
      // genuinely take longer than 2s without anything being wrong.
      signal: AbortSignal.timeout(8000),'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
