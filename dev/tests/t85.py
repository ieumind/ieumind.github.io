import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html?who=teacher'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for w in (360,390,430,640):
      ctx=await b.new_context(viewport={'width':w,'height':844}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      P=await ctx.new_page(); await P.goto(U); await P.wait_for_timeout(900)
      r=await P.evaluate('''()=>{const e=document.querySelector(".wbanner");if(!e)return null;const c=getComputedStyle(e),t=e.querySelector("p").getBoundingClientRect(),b=e.getBoundingClientRect();return {pb:parseFloat(c.paddingBottom),gap:b.bottom-t.bottom,h:b.height,art:getComputedStyle(e.querySelector(".wb-art")).display}}''')
      ok(f'{w}px 배너 있음', r is not None)
      if r:
        ok(f'{w}px 글 아래 여백 ≥14px', r['gap']>=14, str(r)); ok(f'{w}px 그림 숨김', r['art']=='none'); ok(f'{w}px 높이 220 이하', r['h']<220, str(r['h']))
      if w==390: await P.screenshot(path='/tmp/claude-0/banner390.png')
      await ctx.close()
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
