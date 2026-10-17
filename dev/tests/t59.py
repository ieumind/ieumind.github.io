# 아이콘 통일 점검: 여러 화면을 돌며 ① 없는 아이콘 경고·오류 ② 화면에 남은 이모지 ③ 아이콘 크기(16·20·24)·선 굵기(1.8) ④ 휴대폰 넘침
import asyncio, re, json, sys
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'; D='file:///tmp/claude-0/smoke/pdemo.html?demo=1'
EMO = r"[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{2190}-\u{21FF}\u{2300}-\u{23FF}\u{25A0}-\u{25FF}\u{FE0F}\u{22EF}\u{28FF}\u{FF0B}]"
SCAN = '''(ALLOW) => { const re = new RegExp("%s", "u"), out = [];
  const skip = el => el.closest("textarea,input,.post .v,.wcard p,.pad-body,.bub p,.pquote p,.qline,.preview,.ncard,.tc-body,.replies,.prompt,.mbody,.bm-body,.initem p,.notice-item p,.dn,.chcard p,.sctbl,.scprev,.tnotice-body,.sk-links,.cbtxt");
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while(w.nextNode()){ const n = w.currentNode, t = n.nodeValue; if(!re.test(t)) continue; const el = n.parentElement; if(!el || skip(el) || el.closest("[hidden]")) continue;
    const st = getComputedStyle(el); if(st.display === "none" || st.visibility === "hidden") continue;
    const clean = t.replace(new RegExp("[→↔]", "gu"), ""); if(!re.test(clean)) continue;   // 문장 속 흐름 화살표(A → B)는 글자
    out.push((el.className || el.tagName) + ": " + t.trim().slice(0, 60)) }
  const sizes = {}, bad = [];
  document.querySelectorAll("svg.ti").forEach(s => { const r = s.getBoundingClientRect(); if(!r.width) return; const k = Math.round(r.width) + "x" + Math.round(r.height); sizes[k] = (sizes[k] || 0) + 1;
    if(s.getAttribute("stroke-width") !== "1.8") bad.push("stroke " + s.getAttribute("stroke-width")); if(![16,20,24].includes(Math.round(r.width)) || Math.round(r.width) !== Math.round(r.height)) bad.push(k + " in " + (s.parentElement.className || s.parentElement.tagName)) });
  return {emoji: [...new Set(out)], sizes, bad: [...new Set(bad)].slice(0, 10), n: document.querySelectorAll("svg.ti").length, w: document.documentElement.scrollWidth} }''' % EMO.replace("\\", "\\\\")
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; warns=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms); allemo={}
    async def chk(pg, name):
      r = await pg.evaluate(SCAN, None)
      for e in r['emoji']: allemo.setdefault(e, name)
      print(f"{name:26s} icons {r['n']:3d} sizes {r['sizes']} bad {r['bad']} width {r['w']}")
    def hook(pg, tag):
      pg.on('pageerror', lambda e: errs.append(tag + ':' + str(e)))
      pg.on('console', lambda m: (warns.append(tag + ':' + m.text) if m.type in ('warning','error') and ('icon' in m.text or 'Error' in m.text) else None))
    for vw in (1280, 390):
      c=await b.new_context(viewport={'width':vw,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
      P=await c.new_page(); hook(P, f'D{vw}')
      await P.goto(D); await W(P,800); await P.evaluate('S.tour=null; render()'); await W(P)
      await chk(P, f'{vw} 교사 홈')
      await P.evaluate('act("mcourse",{dataset:{v:"c-demo"}})'); await W(P); await P.evaluate('document.querySelector("details.tnotice").open=true; document.querySelector(".cport > summary")?.click()'); await W(P,500); await chk(P, f'{vw} 과목')
      for rid in ['park-1965','demo-draw','demo-notes','comfort-relay','joseon-minbon','demo-chat']:
        await P.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(P)
        for t in ['overview','progress','students','change','feedback','settings']:
          await P.evaluate(f'act("ttab",{{dataset:{{v:"{t}"}}}})'); await W(P,150)
          await chk(P, f'{vw} {rid[:10]}/{t}')
        if rid != 'demo-notes':
          await P.evaluate(f'act("present",{{dataset:{{id:"{rid}"}}}})'); await W(P); await chk(P, f'{vw} {rid[:10]} 함께보기'); await P.evaluate('act("present-exit",{dataset:{}})'); await W(P)
      await P.evaluate('act("ttab",{dataset:{v:"students"}})'); await W(P)
      await P.evaluate('act("home",{dataset:{}}); act("create",{dataset:{}})'); await W(P,400)
      await P.evaluate('document.querySelectorAll("details.adv").forEach(d=>d.open=true)'); await W(P); await chk(P, f'{vw} 새 활동')
      for g in ['question','sketch','chat','notes']:
        await P.evaluate(f'act("goal",{{dataset:{{v:"{g}"}}}})'); await W(P,200); await chk(P, f'{vw} 새 활동/{g}')
      for m in ['msg-open','tname-open']:
        try:
          await P.evaluate('act("home",{dataset:{}})'); await W(P); await P.evaluate(f'act("{m}",{{dataset:{{}}}})'); await W(P,400); await chk(P, f'{vw} 창 {m}'); await P.keyboard.press('Escape'); await W(P)
        except Exception as e: print('skip', m, e)
      await P.evaluate('act("home",{dataset:{}})'); await W(P); await P.evaluate('act("msg-open",{dataset:{}})'); await W(P); await P.evaluate('act("msg-tab",{dataset:{v:"sent"}})'); await W(P); await P.evaluate('document.querySelector(".mitem > summary")?.click()'); await W(P); await chk(P, f'{vw} 보낸 안내'); await P.keyboard.press('Escape'); await W(P)
      await P.evaluate('act("install-help",{dataset:{}})'); await W(P); await chk(P, f'{vw} 설치 안내'); await P.keyboard.press('Escape')
      await P.evaluate('act("tour-start",{dataset:{}})'); await W(P,500); await chk(P, f'{vw} 둘러보기'); await P.evaluate('tourEnd()'); await W(P)
      # 학생 화면 미리보기
      await P.evaluate('act("preview-home",{dataset:{}})'); await W(P,500); await chk(P, f'{vw} 학생 홈')
      await P.click('.dcard'); await W(P,400); await chk(P, f'{vw} 학생 과목')
      for rid in ['park-1965','demo-draw','demo-notes','comfort-relay','joseon-minbon','demo-chat']:
        await P.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(P,300); await chk(P, f'{vw} 학생 {rid[:10]}')
        await P.evaluate('act("rmode",{dataset:{v:"work"}})'); await W(P,300); await chk(P, f'{vw} 학생 {rid[:10]} 쓰기')
      await P.evaluate('act("preview-exit",{dataset:{}})'); await W(P)
      # 소개·학생 첫 화면
      W2=await c.new_page(); hook(W2, f'W{vw}'); await W2.goto(U+'?who=teacher#teacher'); await W(W2,700)
      await W2.goto('file:///tmp/claude-0/smoke/pdemo.html'); await W(W2,700); await chk(W2, f'{vw} 첫 화면')
      await c.close()
    print('\nleft emoji in UI:'); [print('  ', k, '@', v) for k, v in allemo.items()]
    print('warns', warns[:10]); print('errors', errs); await b.close()
asyncio.run(main())
