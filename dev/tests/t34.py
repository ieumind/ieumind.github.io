import asyncio, re
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    P=await ctx.new_page(); errs=[]; P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await P.wait_for_timeout(700)
    await P.click('[data-a=tour-end]'); await P.click('.thead [data-a=create]'); await P.wait_for_timeout(300)
    await P.fill('#c-kw','콜럼버스'); await P.click('[data-a=ai-suggest]'); await P.wait_for_timeout(800)
    print(await P.eval_on_selector_all('.aisug-item b','e=>e.map(x=>x.textContent)'), await P.text_content('.aisug .hint'))
    await P.click('[data-a=ai-setup] >> nth=0'); await P.wait_for_timeout(300); print('demo modal:', await P.text_content('#modal .notice'))
    print(errs); await b.close()
asyncio.run(main())
