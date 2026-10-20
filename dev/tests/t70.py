# 휴대폰: 새 과목·학생 코드·개별 안내는 한 화면으로 열림 / 만들기 화면 아래 고정 막대
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    ctx=await b.new_context(viewport={'width':390,'height':780}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    for a,name in [('course-new','새 과목'),('roster-open','학생 코드'),('msg-open','개별 안내')]:
      await T.click(f'#qbar [data-a={a}]'); await W(T,500)
      r=await T.evaluate('(()=>{const m=document.querySelector(".modal").getBoundingClientRect(),g=getComputedStyle(document.querySelector(".modal-bg"));return [Math.round(m.left),Math.round(m.width),Math.round(document.querySelector(".modal-bg").getBoundingClientRect().height),innerHeight,document.documentElement.scrollWidth]})()')
      ok(f'{name}: 화면 전체로 열림', r[0]==0 and r[1]==390 and r[2]==780 and r[4]<=390, str(r))
      ok(f'{name}: 돌아가기', await T.is_visible('.sheet-back'))
      await T.screenshot(path=f'/tmp/claude-0/smoke/t70_{a}.png')
      await T.click('.sheet-back'); await W(T,300); ok(f'{name}: 돌아가면 닫힘', not await T.query_selector('.modal'))
    # PC에서는 그대로 팝업
    await T.set_viewport_size({'width':1280,'height':900}); await W(T,300)
    await T.click('[data-a=course-new]'); await W(T,400)
    ok('PC: 팝업 그대로, 돌아가기 줄 없음', not await T.is_visible('.sheet-back') and await T.evaluate('document.querySelector(".modal").getBoundingClientRect().width<=520'))
    await T.keyboard.press('Escape'); await W(T,200)
    await T.evaluate('S.modal=null;renderModal()'); await T.set_viewport_size({'width':390,'height':780}); await W(T,300)
    await T.click('#qbar [data-a=create]'); await W(T,500)
    r=await T.evaluate('(()=>{const f=document.querySelector(".cform > .foot");return f? [getComputedStyle(f).boxShadow.includes("160px"), Math.round(f.getBoundingClientRect().bottom), innerHeight]:null})()')
    ok('만들기 화면 아래 고정 막대에 덮개 그림자', bool(r) and r[0], str(r))
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
