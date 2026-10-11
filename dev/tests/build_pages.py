"""테스트용 페이지 만들기: index.html의 viewport meta 바로 뒤에 가짜 Supabase(mock.js)를 끼워 넣는다.
테스트 파일들은 /tmp/claude-0/smoke/pNN.html 경로를 쓴다.
사용: python3 dev/tests/build_pages.py   (저장소 루트에서)"""
import os, shutil
OUT = "/tmp/claude-0/smoke"
os.makedirs(OUT + "/mob", exist_ok=True)
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
h = open(os.path.join(root, "index.html"), encoding="utf-8").read()
m = open(os.path.join(root, "dev/tests/mock.js"), encoding="utf-8").read()
i = h.index('<meta name="viewport"'); j = h.index(">", i) + 1
page = h[:j] + "\n<script>" + m + "</script>" + h[j:]
for n in ["p17", "p20", "p21", "p22", "p23", "p24", "p25", "p26"]:
    open(f"{OUT}/{n}.html", "w", encoding="utf-8").write(page)
open(f"{OUT}/pdemo.html", "w", encoding="utf-8").write(h)          # 체험 모드(?demo=1)용: 가짜 서버 없이
shutil.copy(os.path.join(root, "sw.js"), OUT)
print("built", OUT)
