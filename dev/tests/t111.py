# 단계 질문 카드: 논술은 필수·글쓰기 전 질문 정리, 감상·성찰은 선택·접힘·느낌 틀 둘·질문 3개까지, 토론은 기존 그대로
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    ctx=await b.new_context(viewport={'width':375,'height':800}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
    await T.set_viewport_size({'width':1280,'height':900}); await T.evaluate('document.querySelector("[data-a=create]").click()'); await T.wait_for_timeout(500); await T.set_viewport_size({'width':375,'height':800})
    async def goal(k,t=None):
      await T.evaluate(f'document.querySelector("[data-a=goal][data-v={k}]").click()'); await T.wait_for_timeout(400)
      if t: await T.evaluate(f'document.querySelector("[data-a=tpl][data-v={t}]")?.click()'); await T.wait_for_timeout(300)
    # 논술
    await goal('write'); h=await T.evaluate('document.querySelector(".stepq-card h3")?.innerText||""')
    ok('논술: 글을 쓰기 전 질문 제목·필수 표시', '글을 쓰기 전에' in h and await T.evaluate('!!document.querySelector(".stepq-card .req")'), h)
    # 감상·성찰
    await goal('look'); card=T.locator('.stepq-card')
    h=await T.evaluate('document.querySelector(".stepq-card h3")?.innerText||""')
    ok('감상·성찰: 느낌 질문 제목, 필수 표시 없음', '어떤 느낌을 물어볼까요' in h and await T.evaluate('!document.querySelector(".stepq-card .req")'), h)
    ok('감상·성찰: 기본은 접혀 있음', await T.evaluate('document.querySelector(".stepq-card details").open')==False)
    await T.evaluate('document.querySelector(".stepq-card details").open=true'); await T.wait_for_timeout(200)
    chips=await T.evaluate('[...document.querySelectorAll(".stepq-card .toolchip")].map(x=>x.querySelector("b").innerText)'); print(chips)
    ok('감상·성찰: 틀은 느낌과 이유·자유롭게(+직접 만들기)', chips[:2]==['느낌과 이유','자유롭게'] and len(chips)==3, chips)
    n0=await T.locator('.stepq-card .qstep').count(); ok('감상·성찰: 기본 질문 2개', n0==2, n0)
    await T.click('.stepq-card [data-a=q-add]'); await T.wait_for_timeout(250)
    ok('감상·성찰: 3개까지 늘릴 수 있음', await T.locator('.stepq-card .qstep').count()==3)
    ok('감상·성찰: 3개면 추가 버튼 없고 안내', await T.locator('.stepq-card [data-a=q-add]').count()==0 and '3개까지' in await T.locator('.stepq-card').inner_text())
    await T.evaluate('act("q-add",{dataset:{}})'); await T.wait_for_timeout(200)
    ok('감상·성찰: 강제로 눌러도 4개는 안 됨', await T.evaluate('qsOf(F("create")).length')==3)
    # 토론은 그대로
    await goal('compare'); h=await T.evaluate('document.querySelector(".stepq-card h3")?.innerText||""')
    ok('토론: 기존 제목·필수', '어떤 질문을 따라 생각할까요' in h and await T.evaluate('!!document.querySelector(".stepq-card .req")'), h)
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
