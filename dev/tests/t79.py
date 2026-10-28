# 도구 버튼을 좌측 메뉴(학생 관리)로 · 홈에는 새 활동 만들기만 · 최근 활동 4개까지
import asyncio, re
from playwright.async_api import async_playwright
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for name,w,h in (('PC',1280,800),('휴대폰',390,800)):
      c=await b.new_context(viewport={'width':w,'height':h}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
      await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await P.evaluate('localStorage.setItem("nonjae.tourdone","1")'); await P.reload(); await P.wait_for_timeout(900)
      if w<700:
        await P.click('#side-tog'); await P.wait_for_timeout(250)
      ok(f'{name} 메뉴에 ‘학생 관리’ 묶음과 개별 안내·출석부', await P.evaluate('!!document.querySelector("#side .nav-grp") && !!document.querySelector("#side [data-a=msg-open]") && !!document.querySelector("#side [data-a=att-open]")') and await P.is_visible('#side [data-a=att-open]'))
      ok(f'{name} 메뉴에 새 과목', await P.is_visible('#side [data-a=course-new]'))
      await P.screenshot(path=f'/tmp/claude-0/smoke/t79_{name}.png')
      await P.click('#side [data-a=att-open]'); await P.wait_for_timeout(400)
      ok(f'{name} 메뉴에서 출석부가 열림', await P.evaluate('S.modal?.type')=='attend')
      if w<700: ok(f'{name} 메뉴가 닫힘', not await P.evaluate('document.body.classList.contains("side-open")'))
      await P.evaluate('S.modal=null; render()')
      if w>700:
        ok(f'{name} 홈 카드는 새 활동 만들기 하나', await P.evaluate('document.querySelectorAll(".qgrid .qa").length')==1 and await P.is_visible('.qgrid [data-a=create]'))
        ok(f'{name} 메뉴 위치 안내 글', '왼쪽 메뉴' in await P.inner_text('.qhint'))
      else:
        ok(f'{name} 휴대폰 안내 글(☰)', '☰' in await P.inner_text('.qhint'))
      # 최근 활동 최대 4개
      n=await P.evaluate('document.querySelectorAll(".recent li").length'); ok(f'{name} 최근 활동 4개 이하', 0<n<=4, str(n))
      await P.screenshot(path=f'/tmp/claude-0/smoke/t79_home_{name}.png')
      await c.close()
    # 지난달 안내 전 표시
    c=await b.new_context(viewport={'width':1280,'height':800}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page()
    await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await P.evaluate('localStorage.setItem("nonjae.tourdone","1")'); await P.reload(); await P.wait_for_timeout(800)
    await P.evaluate('S.attend=[{id:"all_2026-09",ym:"2026-09",per:3,dates:["2026-09-07"],marks:{a:{"2026-09-07":"○○○"}},notes:{}}]; render()'); await P.wait_for_timeout(200)
    ok('지난달 안내 전: 메뉴 점 + 홈 알림', await P.evaluate('!!document.querySelector("#side .nav-dot")') and '9월 출석 안내를 아직 안 보냈어요' in await P.inner_text('.qhint'))
    await P.click('.qhint-b'); await P.wait_for_timeout(300); ok('알림을 누르면 출석부', await P.evaluate('S.modal?.type')=='attend')
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
