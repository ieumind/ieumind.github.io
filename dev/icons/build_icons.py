#!/usr/bin/env python3
"""index.html이 쓰는 Tabler 아이콘만 골라 TI_PATHS(…/*TI:BEGIN*/ … /*TI:END*/)에 넣는다.
사용: python3 dev/icons/build_icons.py [tabler-icons 저장소 경로]
  - 아이콘 이름은 ic("이름") 호출과, 아이콘 이름을 담는 자료(icon:/modeIcon:/ic:/mark: 값, TI_LIST 배열)에서 모은다
  - 저장소에 없는 이름이 있으면 멈춘다 (실제 Tabler 아이콘만 쓴다)
Tabler Icons — MIT License, https://github.com/tabler/tabler-icons"""
import re, sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/tabler/tabler-icons"
OUT = os.path.join(REPO, "icons", "outline")
p = os.path.join(ROOT, "index.html"); s = open(p, encoding="utf-8").read()
a, b = s.index("/*TI:BEGIN*/"), s.index("/*TI:END*/")
body = s[:a] + s[b:]
names = set(re.findall(r'\b(?:ic|sec|tile|node)\(\s*"([a-z0-9-]+)"', body))            # ic("이름") · 아이콘 이름을 첫 값으로 받는 도우미
names |= set(re.findall(r'\b(?:icon|modeIcon|ic|mark|i|ti)\s*:\s*"([a-z0-9-]+)"', body))   # 자료의 아이콘 칸
names |= set(re.findall(r'data-ti="([a-z0-9-]+)"', body))                              # 처음부터 화면에 있는 버튼
names |= set(re.findall(r'\bic\(\s*[^()"]*\?\s*"([a-z0-9-]+)"\s*:\s*"([a-z0-9-]+)"', body) and sum(re.findall(r'\bic\(\s*[^()"]*\?\s*"([a-z0-9-]+)"\s*:\s*"([a-z0-9-]+)"', body), ()) or ())
for a3 in re.findall(r'\bic\(\s*\[([^\]]*)\]', body): names |= set(re.findall(r'"([a-z0-9-]+)"', a3))   # ic(["a","b"][i])
listed = set()
for arr in re.findall(r'/\*TI:LIST\*/(.*?);[ \t]*(?://[^\n]*)?$', body, re.S | re.M):           # /*TI:LIST*/ 뒤 목록(문장 끝 ; 까지)의 아이콘 이름
    listed |= {n for n in re.findall(r'"([a-z0-9-]+)"', arr) if os.path.exists(os.path.join(OUT, n + ".svg"))}
names |= listed
missing = sorted(n for n in names if not os.path.exists(os.path.join(OUT, n + ".svg")))
if missing: sys.exit("Tabler에 없는 아이콘: " + ", ".join(missing))
ver = json.load(open(os.path.join(REPO, "package.json")))["version"]
items = []
for n in sorted(names):
    svg = open(os.path.join(OUT, n + ".svg"), encoding="utf-8").read()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    inner = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", inner)
    inner = re.sub(r"\s*\n\s*", "", inner).replace(" />", "/>").strip()
    items.append(f'"{n}":\'{inner}\'')
# CSS에서 쓰는 아이콘: var(--ti-이름) → :root에 마스크용 data URI (/*TIC:BEGIN*/ … /*TIC:END*/)
from urllib.parse import quote
css_names = sorted(set(re.findall(r'var\(--ti-([a-z0-9-]+)\)', body)))
miss2 = [n for n in css_names if not os.path.exists(os.path.join(OUT, n + ".svg"))]
if miss2: sys.exit("Tabler에 없는 CSS 아이콘: " + ", ".join(miss2))
def uri(n):
    svg = open(os.path.join(OUT, n + ".svg"), encoding="utf-8").read()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    svg = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", svg)
    svg = re.sub(r"\s+", " ", svg).replace("> <", "><").strip().replace('stroke-width="2"', 'stroke-width="1.8"').replace('stroke="currentColor"', 'stroke="black"')
    return 'url("data:image/svg+xml,' + quote(svg, safe=" =:/;,") + '")'
if "/*TIC:BEGIN*/" in s:
    c1, c2 = s.index("/*TIC:BEGIN*/"), s.index("/*TIC:END*/")
    s = s[:c1] + "/*TIC:BEGIN*/:root{" + ";".join(f"--ti-{n}:{uri(n)}" for n in css_names) + "}/*TIC:END*/" + s[c2 + len("/*TIC:END*/"):]
    a, b = s.index("/*TI:BEGIN*/"), s.index("/*TI:END*/")
block = "/*TI:BEGIN*/" + f"/* Tabler Icons v{ver} outline · {len(items)}개 */" + ",".join(items) + "/*TI:END*/"
s = s[:a] + block + s[b + len("/*TI:END*/"):]
open(p, "w", encoding="utf-8").write(s)
print(f"Tabler Icons v{ver}: {len(items)}개 아이콘, {len(block)//1024}KB")
