# 필기 안내 빈칸 · 질문 활동 설명 · 세부 설정 간격 · 공지 두 줄 요약 · 주소 자동 링크
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('.thead [data-a=create]'); await W(T)
    await T.click('[data-a=goal][data-v=notes]'); await W(T)
    print('notes prompt value:', repr(await T.input_value('#c-prompt')), '| ph:', await T.get_attribute('#c-prompt','placeholder'))
    await T.click('[data-a=create-save]'); await W(T,600); rid=await T.evaluate('S.roomId')
    print('saved notes prompt:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}")?.prompt'))
    await T.click('.thead [data-a=create]') if await T.query_selector('.thead [data-a=create]') else await T.click('#topr [data-a=create]'); await W(T)
    await T.click('[data-a=goal][data-v=question]'); await W(T)
    print('question modes:', await T.eval_on_selector_all('[data-a=tpl]','e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    await T.click('details[data-keep=adv] > summary'); await W(T)
    await T.screenshot(path='/tmp/claude-0/smoke/mob/adv_tight.png', full_page=True)
    await T.fill('#c-prompt','자료를 보세요 https://example.com/a?b=1&c=2. 그리고 생각해요'); await T.fill('#c-context','참고: https://ko.wikipedia.org/wiki/콜럼버스')
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    await T.click('[data-a=preview]'); await W(T,500)
    print('links:', await T.eval_on_selector_all('a.autolink','e=>e.map(x=>x.getAttribute("href")+" ["+x.textContent+"]")'))
    await T.click('[data-a=preview-exit]'); await W(T,400)
    # course + 2 notices
    await T.click('[data-a=home]'); await W(T); await T.click('.dadd'); await W(T); await T.fill('#course-title','시험 과목'); await T.click('[data-a=course-save]'); await W(T,600)
    for t in ['내일은 컴퓨터실에서 수업해요. 이어폰 챙기기','수행평가 자료는 https://example.org/doc 에서 보세요']:
      await T.evaluate('document.querySelectorAll(".tnotice").forEach(d=>d.open=true)'); await T.fill('#notice-text',t); await T.click('[data-a=notice-add]'); await W(T,500)
    await T.evaluate('document.querySelectorAll(".tnotice").forEach(d=>d.open=false)'); await W(T)
    print('collapsed:', await T.eval_on_selector_all('.tnotice .nprev','e=>e.map(x=>x.textContent)'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/notice2.png')
    await T.evaluate('document.querySelectorAll(".tnotice").forEach(d=>d.open=true)'); print('notice links:', await T.eval_on_selector_all('.tnotice a.autolink','e=>e.map(x=>x.href)'))
    print('errors', errs); await b.close()
asyncio.run(main())
