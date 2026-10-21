# 첫 환영: 처음 가입한 선생님(이름 정한 뒤) · 처음 코드로 들어온 학생
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
    for vw in (1280,390):
      c=await b.new_context(viewport={'width':vw,'height':800}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); T=await c.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
      await T.goto(U+'?who=teacher2&newteacher=1'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(900)
      first=await T.evaluate('S.modal&&S.modal.type+":"+S.modal.first')
      ok(f'{vw} 처음 온 선생님: 이름 정하기가 먼저', first=='tname:true', str(first))
      await T.fill('#t-name','새샘'); await T.click('[data-a=tname-save]'); await T.wait_for_timeout(700)
      ok(f'{vw} 이름을 정하면 환영 창', await T.evaluate('S.modal?.type')=='welcome' and '새샘 선생님, 생각이음에 오신 것을 환영해요' in await T.inner_text('.hello'))
      ok(f'{vw} 빵빠레(색종이)가 나옴', await T.evaluate('!!document.getElementById("confetti")'))
      await T.screenshot(path=f'/tmp/claude-0/smoke/t73_t{vw}.png')
      await T.click('.hello [data-a=modal-close]'); await T.wait_for_timeout(300)
      ok(f'{vw} 닫으면 사라짐, 새로고침해도 다시 안 뜸', not await T.query_selector('.hello'))
      await T.reload(); await T.wait_for_timeout(900); ok(f'{vw} 다시 안 뜸', await T.evaluate('S.modal?.type')!='welcome')
      await c.close()
    # 학생
    c=await b.new_context(viewport={'width':390,'height':800}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); S=await c.new_page(); S.on('pageerror',lambda e:errs.append(str(e)))
    await S.goto(U); await S.evaluate('localStorage.clear()'); await S.evaluate('localStorage.setItem("nonjae.name","김가온"); localStorage.setItem("nonjae.welcome","student")'); await S.reload(); await S.wait_for_timeout(1000)
    ok('학생: 환영 창', await S.evaluate('S.modal?.type')=='welcome' and '김가온님, 환영해요' in await S.inner_text('.hello'), str(await S.evaluate('[S.mode,S.name,S.modal&&S.modal.type]')))
    await S.screenshot(path='/tmp/claude-0/smoke/t73_s.png')
    await S.click('.hello [data-a=modal-close]'); await S.wait_for_timeout(300); await S.reload(); await S.wait_for_timeout(900)
    ok('학생: 두 번째부터는 안 뜸', await S.evaluate('S.modal?.type')!='welcome')
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
