# 새 활동 만들기: 활동 이름·소개가 맨 위(활동 종류보다 앞)에 접힘 없이 보인다
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
    for vw,vh in ((1280,900),(375,800)):
      ctx=await b.new_context(viewport={'width':vw,'height':vh}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
      await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
      await T.evaluate('act("create",{dataset:{}})'); await T.wait_for_timeout(700)
      order=await T.evaluate('[...document.querySelectorAll(".cform > [data-cs], #app [data-cs]")].map(x=>x.dataset.cs)'); print(vw,order)
      ok(f'{vw}px 이름·소개가 활동 종류보다 앞', order.index('title')<order.index('goal') and order[0]=='title')
      ok(f'{vw}px 이름 칸이 접힘 없이 보임', await T.is_visible('#c-title') and await T.is_visible('#c-intro'))
      ok(f'{vw}px 더 설정하기 안에는 이름 칸이 없음', await T.evaluate('!document.querySelector(".cmore #c-title")'))
      await T.fill('#c-title','순서 테스트'); await T.fill('#c-intro','소개 테스트'); await T.wait_for_timeout(300)
      ok(f'{vw}px 입력이 폼에 반영', await T.evaluate('createForm().title==="순서 테스트"&&createForm().intro==="소개 테스트"'))
      await T.screenshot(path=f'/tmp/claude-0/scr/create_title_{vw}.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
