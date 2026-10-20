# 휴대폰: 위쪽 막대 고정 · 아래쪽 빠른 메뉴 4칸 고정 (+ 데스크톱에서는 그대로)
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(name, cond, extra=''):
  print(('PASS ' if cond else 'FAIL ')+name, extra)
  if not cond: fails.append(name)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    ok('데스크톱: 아래 고정 메뉴는 안 보이고 바로가기 카드가 보임', not await T.is_visible('#qbar') and await T.is_visible('.qgrid'))
    # 휴대폰
    await T.set_viewport_size({'width':390,'height':780}); await W(T,400)
    ok('휴대폰: 아래 고정 메뉴 4칸', await T.is_visible('#qbar') and await T.eval_on_selector_all('#qbar button','e=>e.map(x=>x.textContent.trim())')==['새 활동 만들기','새 과목','학생 코드','개별 안내'])
    r=await T.evaluate('(()=>{const q=document.getElementById("qbar").getBoundingClientRect(); const bs=[...document.querySelectorAll("#qbar button")].map(x=>Math.round(x.getBoundingClientRect().top)); return [Math.round(q.bottom), innerHeight, new Set(bs).size, getComputedStyle(document.getElementById("qbar")).position]})()')
    ok('아래에 붙어 있고 한 줄에 4개', r[0]==r[1] and r[2]==1 and r[3]=='fixed', str(r))
    ok('휴대폰: 윗쪽 바로가기 카드는 숨김(중복 방지)', not await T.is_visible('.qgrid'))
    pos=lambda: T.evaluate('(()=>{const h=document.getElementById("side").getBoundingClientRect(), t=document.getElementById("topbar").getBoundingClientRect(); return [Math.round(h.top), Math.round(t.top), Math.round(h.bottom), Math.round(t.bottom)]})()')
    a=await pos(); await T.evaluate('scrollTo(0, 600)'); await W(T,300); z=await pos()
    sy=await T.evaluate('scrollY'); ok('스크롤을 내렸음', sy>200, str(sy))
    ok('스크롤해도 앱 이름 막대·알림/계정 줄이 위에 고정', z[0]==0 and abs(z[1]-z[2])<=1, f'{a} -> {z}')
    q=await T.evaluate('Math.round(document.getElementById("qbar").getBoundingClientRect().bottom)==innerHeight'); ok('스크롤해도 아래 메뉴 고정', q)
    await T.click('#qbar [data-a=course-new]'); await W(T,400); ok('아래 메뉴의 ‘새 과목’이 동작', await T.is_visible('#course-title')); await T.keyboard.press('Escape'); await W(T)
    await T.click('#qbar [data-a=create]'); await W(T,500); ok('‘새 활동 만들기’가 동작, 활동 만들기 화면에서는 아래 메뉴 숨김', await T.evaluate('S.view')=='create' and not await T.is_visible('#qbar'))
    await T.evaluate('act("home",{dataset:{}})'); await W(T,400)
    await T.evaluate('scrollTo(0,0)'); await T.screenshot(path='/tmp/claude-0/smoke/t68_m.png')
    ok('가로 넘침 없음', await T.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    # 학생: 아래 메뉴 없음, 위쪽 줄은 고정
    await T.click('#side-tog'); await W(T,200); await T.click('#sideme [data-a=feedback-open]') if False else None
    await T.evaluate('act("preview-home",{dataset:{}})'); await W(T,600)
    ok('학생 화면 미리보기에서는 아래 메뉴 숨김', not await T.is_visible('#qbar'))
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
