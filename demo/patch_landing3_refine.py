import sys

path = "landing3.html"

with open(path, "r") as f:
    content = f.read()

old1 = '<div class="nav-right"><a href="checkout.html">Start demo</a></div>'
if old1 not in content:
    print("PATTERN 1 NOT FOUND")
    sys.exit(1)
content = content.replace(old1, '')

old2 = '''  .hero h1 {
    font-size: 58px; line-height: 1.08; font-weight: 600; letter-spacing: -0.02em;
    margin-bottom: 24px; max-width: 640px;
  }'''
new2 = '''  .hero h1 {
    font-size: 84px; line-height: 0.98; font-weight: 700; letter-spacing: -0.03em;
    margin-bottom: 28px; max-width: 700px;
  }'''
if old2 not in content:
    print("PATTERN 2 NOT FOUND")
    sys.exit(1)
content = content.replace(old2, new2)

old2b = "    .hero h1 { font-size: 36px; }"
new2b = "    .hero h1 { font-size: 40px; line-height: 1.05; }"
if old2b not in content:
    print("PATTERN 2B NOT FOUND")
    sys.exit(1)
content = content.replace(old2b, new2b)

old3 = "body { background: var(--bg); color: var(--ink); font-family: var(--display); overflow-x: hidden; }"
new3 = '''body { background: var(--bg); color: var(--ink); font-family: var(--display); overflow-x: hidden; position: relative; }
  .glow-field { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
  .glow-orb { position: absolute; border-radius: 50%; filter: blur(90px); }
  .glow-orb.o1 { width: 480px; height: 480px; background: var(--go); top: -120px; left: -100px; opacity: 0.12; }
  .glow-orb.o2 { width: 380px; height: 380px; background: var(--go); top: 30%; right: -140px; opacity: 0.10; }
  .glow-orb.o3 { width: 340px; height: 340px; background: #2fb8ff; bottom: -80px; left: 30%; opacity: 0.07; }
  nav, .hero, .section, .final { position: relative; z-index: 1; }'''
if old3 not in content:
    print("PATTERN 3 NOT FOUND")
    sys.exit(1)
content = content.replace(old3, new3)

old4 = "<body>\n\n<nav>"
new4 = '''<body>
<div class="glow-field">
  <div class="glow-orb o1"></div>
  <div class="glow-orb o2"></div>
  <div class="glow-orb o3"></div>
</div>

<nav>'''
if old4 not in content:
    print("PATTERN 4 NOT FOUND")
    sys.exit(1)
content = content.replace(old4, new4)

with open(path, "w") as f:
    f.write(content)

print("all patches applied successfully")
