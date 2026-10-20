# 로고 헤더 · 휴대폰 위쪽 오른쪽 3버튼 · 설치 안내 PC 탭
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
    ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    ok('PC: 로고 이미지', await T.is_visible('.brand-logo') and await T.evaluate('document.querySelector(".brand-logo").naturalWidth>0'))
    ok('PC: 말풍선·"생각이음" 글자 없음, 문구만', not await T.query_selector('.brand-mark') and (await T.inner_text('.brand')).strip()=='생각을 잇다, 생각이 자라다')
    ok('PC: 위쪽 막대 알림·계정은 본문 위, 헤더 안 것은 숨김', await T.is_visible('#topbar [data-a=tb-bell]') and not await T.is_visible('#topbar-m'))
    await T.click('.brand-logo'); await W(T); ok('로고 누르면 처음 화면', await T.evaluate('S.view')!='create')
    await T.screenshot(path='/tmp/claude-0/smoke/t69_pc.png')
    await T.set_viewport_size({'width':390,'height':780}); await W(T,400)
    ok('휴대폰: 헤더에 알림·계정·메뉴 3버튼', await T.is_visible('#topbar-m [data-a=tb-bell]') and await T.is_visible('#topbar-m [data-a=tb-acct]') and await T.is_visible('#side-tog') and not await T.is_visible('#topbar'))
    r=await T.evaluate('(()=>{const g=s=>document.querySelector(s).getBoundingClientRect(); const l=g(".brand-logo"),a=g("#topbar-m [data-a=tb-bell]"),c=g("#topbar-m [data-a=tb-acct]"),m=g("#side-tog"),h=g("#side"); return [Math.round(h.height),Math.round(l.right),Math.round(a.left),Math.round(c.left),Math.round(m.left),Math.round(m.right),innerWidth]})()')
    ok('순서: 로고 … 알림, 계정, ☰ / 헤더 낮음', r[1]<r[2]<r[3]<r[4] and r[5]<=r[6] and r[0]<=64, str(r))
    ok('휴대폰: 로고 외 글자 없음', not await T.is_visible('.brand-tag'))
    await T.screenshot(path='/tmp/claude-0/smoke/t69_m.png')
    await T.click('#topbar-m [data-a=tb-acct]'); await W(T,300)
    ok('휴대폰: 계정 메뉴가 열림(화면 안)', await T.is_visible('#topbar-m .tb-pop') and await T.evaluate('(()=>{const r=document.querySelector("#topbar-m .tb-pop").getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()'))
    await T.screenshot(path='/tmp/claude-0/smoke/t69_m_pop.png')
    await T.mouse.click(200,500); await W(T,200); ok('바깥 누르면 닫힘', not await T.is_visible('#topbar-m .tb-pop'))
    await T.click('#topbar-m [data-a=tb-bell]'); await W(T,300); ok('휴대폰: 알림 메뉴 열림', await T.is_visible('#topbar-m .tb-pop')); await T.mouse.click(200,500); await W(T,200)
    await T.click('.brand-logo'); await W(T,300); ok('휴대폰: 로고 누르면 메인', await T.evaluate('S.view')!='create')
    # 설치 안내
    await T.evaluate('act("install-help",{dataset:{}})'); await W(T,300)
    ok('설치: 탭 3개(아이폰/안드로이드/PC)', await T.eval_on_selector_all('.seg [data-a=install-os]','e=>e.map(x=>x.textContent)')==['아이폰·아이패드','갤럭시·안드로이드','컴퓨터(PC)'])
    ok('설치: 이 환경(PC UA)에서 기본이 PC 탭', await T.evaluate('S.modal.os')=='pc')
    await T.click('[data-v=pc]'); await W(T,200); t=await T.inner_text('#modal, .modal')
    ok('PC 탭: 제어판/설치된 앱·버튼 안 보일 때 안내', '설치된 앱' in t and '안 보이면' in t and 'chrome://apps' in t)
    ok('설치 가능 이벤트 없으면 즉시 설치 버튼 없음', not await T.query_selector('[data-a=install-now]'))
    await T.evaluate('INSTALL_EVT={prompt(){},userChoice:Promise.resolve({})}; renderModal()'); await W(T,200)
    ok('이벤트 있으면 PC 탭에 즉시 설치 버튼', await T.is_visible('[data-a=install-now]'))
    await T.click('[data-v=ios]'); await W(T,200); ok('아이폰 탭엔 즉시 설치 버튼 없음', not await T.query_selector('[data-a=install-now]'))
    await T.click('[data-v=android]'); await W(T,200); ok('안드로이드 탭엔 즉시 설치 버튼', await T.is_visible('[data-a=install-now]'))
    await T.screenshot(path='/tmp/claude-0/smoke/t69_inst.png')
    # 학생
    await T.keyboard.press('Escape')
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
