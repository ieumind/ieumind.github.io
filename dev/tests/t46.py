# 휴대폰 넘침 · 링크·QR 합치기 · 유형별 예시 · 과목 고르기 크기 · 긴 과목 이름 흐르기 · 과목 포트폴리오
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
WIDE='''()=>{const W=document.documentElement.clientWidth; const out=[]; document.querySelectorAll("body *").forEach(e=>{const b=e.getBoundingClientRect(); if(b.right>W+1 && b.width>0 && getComputedStyle(e).position!=="fixed" && !e.closest(".cport-wrap,.mq")) out.push((e.className||e.tagName)+":"+Math.round(b.right))}); return [document.documentElement.scrollWidth, out.slice(0,8)]}'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    # 휴대폰 체험
    mc=await b.new_context(viewport={'width':390,'height':844}); await mc.route(re.compile(r'https://.*'), lambda r: r.abort())
    M=await mc.new_page(); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(M,700); await M.evaluate('S.tour=null; render()')
    await M.evaluate('S.courses[0].title="2026학년도 2학기 고급 생명과학 온라인 공동교육과정 (화목 7교시)"; render()'); await W(M,600)
    print('home', await M.evaluate(WIDE), '| marquee run:', await M.evaluate('[...document.querySelectorAll(".mq.run")].length'))
    await M.evaluate('act("mcourse",{dataset:{v:"c-demo"}})'); await W(M,500)
    print('course', await M.evaluate(WIDE))
    print('m chead btns:', await M.eval_on_selector_all('.chead-acts .btn','e=>e.filter(x=>getComputedStyle(x).display!=="none").map(x=>x.textContent.trim())'))
    print('chead h2 one line:', await M.evaluate('document.querySelector(".chead h2").getBoundingClientRect().height < 40'), '| run:', await M.evaluate('document.querySelector(".chead .mq").classList.contains("run")'))
    await M.screenshot(path='/tmp/claude-0/smoke/mob/m_course.png')
    await M.evaluate('document.querySelector("details.tnotice").open=true'); await W(M,300); print('notice open', await M.evaluate(WIDE))
    await M.evaluate('act("open",{dataset:{id:"park-1965"}})'); await W(M,400)
    print('room', await M.evaluate(WIDE), '| abar visible:', await M.eval_on_selector_all('.abar .btn','e=>e.filter(x=>x.offsetParent).map(x=>x.textContent.trim())'))
    await M.screenshot(path='/tmp/claude-0/smoke/mob/m_room.png')
    for t in ['progress','students','change','feedback','settings']:
      await M.evaluate(f'act("ttab",{{dataset:{{v:"{t}"}}}})'); await W(M,250); r=await M.evaluate(WIDE)
      if r[0]>390 or r[1]: print('tab', t, r)
    await M.evaluate('act("create",{dataset:{}})'); await W(M,400); print('create', await M.evaluate(WIDE))
    await M.evaluate('act("preview-home",{dataset:{}})'); await W(M,500); print('stu home', await M.evaluate(WIDE))
    await M.click('.dcard'); await W(M,400); print('stu dash', await M.evaluate(WIDE)); await M.screenshot(path='/tmp/claude-0/smoke/mob/m_sdash.png')
    # PC 체험: 예시·과목 고르기·포트폴리오
    pc=await b.new_context(viewport={'width':1280,'height':900}); await pc.route(re.compile(r'https://.*'), lambda r: r.abort())
    D=await pc.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700); await D.evaluate('S.tour=null; act("create",{dataset:{}})'); await W(D,400)
    for tpl in ['debate2','debateN','inquiry','relay','essay','sketch','draw','chat','notes']:
      await D.evaluate(f'(()=>{{applyTemplate("{tpl}"); render()}})()'); await W(D,120)
      print(' ', tpl, '|', await D.inner_text('label[for=c-prompt]'), '|', await D.get_attribute('#c-prompt','placeholder'))
    print('course chip h:', await D.evaluate('document.querySelector("[data-a=c-course]").getBoundingClientRect().height'), 'due h:', await D.evaluate('document.querySelector("#c-due").getBoundingClientRect().height'))
    await D.evaluate('act("home",{dataset:{}})'); await W(D,300); await D.evaluate('act("mcourse",{dataset:{v:"c-demo"}})'); await W(D,400)
    print('pc chead btns:', await D.eval_on_selector_all('.chead-acts .btn','e=>e.filter(x=>getComputedStyle(x).display!=="none").map(x=>x.textContent.trim())'))
    print('cport closed body:', bool(await D.query_selector('.cport-body')))
    await D.click('.cport > summary'); await W(D,400)
    print('cport rows:', len(await D.query_selector_all('.cport-t tbody tr')), '| cols:', await D.eval_on_selector_all('.cport-t thead th .ctt','e=>e.map(x=>x.textContent)'))
    print('row1:', await D.eval_on_selector('.cport-t tbody tr','e=>e.innerText.replace(/\\s+/g," ")'))
    print('col done:', await D.eval_on_selector_all('.cport-t .cdone','e=>e.map(x=>x.textContent)'))
    await D.screenshot(path='/tmp/claude-0/smoke/mob/cport.png', full_page=False)
    await D.click('.cport-t tbody tr:nth-child(4) [data-a=port-student]'); await W(D,300)
    print('student modal:', (await D.inner_text('#modal')).replace('\n',' | ')[:260])
    await D.screenshot(path='/tmp/claude-0/smoke/mob/cport_student.png')
    await D.click('#modal [data-a=port-open]'); await W(D,400)
    print('opened:', await D.evaluate('[S.view,S.roomId,S.ttab,!!S.openPost]'))
    await D.evaluate('act("home",{dataset:{}})'); await W(D,300); await D.evaluate('act("mcourse",{dataset:{v:"c-demo"}})'); await W(D,300)
    print('cport stays open:', bool(await D.query_selector('.cport-body')))
    # 휴대폰 포트폴리오
    await M.evaluate('act("preview-exit",{dataset:{}})'); await W(M,300); await M.evaluate('act("home",{dataset:{}}); act("mcourse",{dataset:{v:"c-demo"}})'); await W(M,300)
    await M.click('.cport > summary'); await W(M,400); print('m cport', await M.evaluate(WIDE)); await M.screenshot(path='/tmp/claude-0/smoke/mob/m_cport.png')
    print('errors', errs); await b.close()
asyncio.run(main())
