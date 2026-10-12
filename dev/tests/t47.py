# 👀 조회 기록(학생이 열기만 해도) · 참여 현황 조회 수 · 마키 속도
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n10303 박서준'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']
    await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title','1학년 한국사'); await T.click('[data-a=mem-all]'); await T.click('[data-a=course-save]'); await W(T,600)
    await T.click('[data-a=create]'); await W(T); await T.fill('#c-prompt','개항은 기회였을까?'); await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    async def login(s):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon'); await W(K,500)
      await K.fill('#f-num',s['number']); await K.fill('#f-name',s['name']); await K.fill('#f-code',s['code']); await K.press('#f-code','Enter'); await W(K,1200); return K
    A=await login(studs[0]); await A.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(A,500)
    await A.evaluate(f'act("home",{{dataset:{{}}}})'); await W(A,200); await A.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(A,400)
    print('view calls (once per session):', [x for x in await A.evaluate('__sbLog') if x=='room_view'])
    B=await login(studs[1]); await B.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(B,400)
    await B.evaluate(f'(async()=>{{const r=S.rooms.find(x=>x.id==="{rid}"); await savePost(r,{{stance:r.stances[0], body:{{claim:"기회", reason:"근대화"}}, status:"submitted", submittedAt:Date.now()}})}})()'); await W(B,600)
    await T.evaluate(f'S.views={{}}; act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,800)
    print('kpis:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    await T.evaluate('act("ttab",{dataset:{v:"progress"}})'); await W(T,400)
    print('vsum:', await T.inner_text('.vsum'))
    print('rows:', await T.eval_on_selector_all('.ptable tbody tr','e=>e.map(x=>x.innerText.replace(/\\s+/g," "))'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/views_progress.png')
    # demo
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e))); await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,600)
    await D.evaluate('S.tour=null; act("open",{dataset:{id:"park-1965"}}); act("ttab",{dataset:{v:"progress"}})'); await W(D,400)
    print('demo vsum:', await D.inner_text('.vsum'), '| kpi0:', await D.inner_text('.kpi'))
    await D.evaluate('S.courses[0].title="2026학년도 2학기 고급 생명과학 온라인 공동교육과정 (화목 7교시)"; act("home",{dataset:{}})'); await W(D,500)
    print('mq duration:', await D.evaluate('getComputedStyle(document.querySelector(".mq.run .mq-in")).animationDuration'))
    print('errors', errs); await b.close()
asyncio.run(main())
