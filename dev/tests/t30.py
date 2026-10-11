import asyncio, re
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; P=await ctx.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await P.wait_for_timeout(800)
    print('demo teacher chips:', await P.eval_on_selector_all('.cchips button','e=>e.map(x=>x.textContent.trim())'))
    print('notify chk in demo:', bool(await P.query_selector('[data-k=notify]')))
    await P.click('#topr [data-a=preview-home]'); await P.wait_for_timeout(500)
    print('preview dcards:', await P.eval_on_selector_all('.dcard .dt','e=>e.map(x=>x.textContent.trim())'), '| pushbar:', bool(await P.query_selector('.pushbar')))
    await P.click('.dcard'); await P.wait_for_timeout(300); print('dash:', await P.text_content('.dhead h1'), len(await P.query_selector_all('.scard')))
    await P.screenshot(path='mob/demo_dash.png', full_page=True)
    await P.click('[data-a=feedback-open]'); await P.wait_for_timeout(200); await P.fill('#fb-body','테스트입니다'); await P.click('[data-a=fb-send]'); await P.wait_for_timeout(200)
    print('demo fb toast:', await P.text_content('#toast'))
    print('errors', errs); await b.close()
asyncio.run(main())
