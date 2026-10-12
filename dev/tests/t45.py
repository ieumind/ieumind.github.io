# 깊이 카드 안에 ‘학생은 이렇게 활동해요’ · 깊이별 시간 = 아래 예상 시간 · 차시·연도
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('.thead [data-a=create]'); await W(T)
    for tpl in ['debate2','inquiry','essay','draw']:
      await T.evaluate(f'(()=>{{applyTemplate("{tpl}"); render()}})()'); await W(T,200)
      print(tpl, 'preview inside card:', bool(await T.query_selector('.depth-card .preview-steps')))
      for d in await T.eval_on_selector_all('.depth','e=>e.map(x=>x.dataset.v)'):
        await T.click(f'.depth[data-v="{d}"]'); await W(T,200)
        use=await T.inner_text(f'.depth[data-v="{d}"] .use'); est=await T.inner_text('.estline')
        others=await T.eval_on_selector_all('.depth .use','e=>e.map(x=>x.textContent)')
        print('  ', d, use, '|', est, '| all:', others, '| match:', use.split('약 ')[1] in est)
    await T.evaluate('(()=>{applyTemplate("debate2"); render()})()'); await W(T)
    await T.evaluate('document.querySelector(".depth-card").scrollIntoView()'); await W(T)
    await T.screenshot(path='/tmp/claude-0/smoke/mob/depth_card.png')
    await T.evaluate('document.querySelector("details[data-keep=info]").open=true'); await W(T)
    print('year label:', await T.inner_text('label[for=c-year]'))
    M=await ctx.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,600); await M.click('.thead [data-a=create]'); await W(M)
    await M.evaluate('document.querySelector(".depth-card").scrollIntoView()'); await W(M); await M.screenshot(path='/tmp/claude-0/smoke/mob/depth_card_m.png')
    print('m overflow:', await M.evaluate('document.documentElement.scrollWidth'))
    print('errors', errs); await b.close()
asyncio.run(main())
