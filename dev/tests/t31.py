import asyncio, re, sys
from playwright.async_api import async_playwright
W_=int(sys.argv[1]) if len(sys.argv)>1 else 1280
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':W_,'height':860})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; P=await ctx.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await P.wait_for_timeout(900)
    for i in range(12):
      card=await P.query_selector('#tour .tour-card')
      if not card: print('tour closed at', i); break
      t=await P.text_content('#tour h3'); hole=await P.evaluate('(()=>{const h=document.querySelector("#tour .tour-hole");return h?h.style.cssText:"(center)"})()')
      print(i, t, '|', hole[:80])
      await P.screenshot(path=f'mob/tour{W_}_{i}.png')
      nx=await P.query_selector('[data-a=tour-next]')
      if not nx: break
      await nx.click(); await P.wait_for_timeout(300)
    await P.click('[data-a=tour-end]'); await P.wait_for_timeout(200)
    print('after end tour:', await P.evaluate('[S.tour, localStorage.getItem("nonjae.tourdone")]'))
    await P.screenshot(path=f'mob/tdash{W_}.png', full_page=True)
    await P.reload(); await P.wait_for_timeout(600); print('no auto tour after done:', not await P.query_selector('#tour .tour-card'))
    print('errors', errs); await b.close()
asyncio.run(main())
