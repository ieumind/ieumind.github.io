# 휴대폰 위쪽 새로고침 버튼 · 단계별 질문 상자(여러 줄)
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
    ctx=await b.new_context(viewport={'width':390,'height':780}); await ctx.route(re.compile(r'https://.*'),lambda r:r.abort()); T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(900)
    ok('휴대폰: 새로고침 버튼이 위쪽 막대에 보임', await T.is_visible('#side-refresh'))
    r=await T.evaluate('(()=>{const g=s=>document.querySelector(s).getBoundingClientRect();const l=g(".brand-logo"),f=g("#side-refresh"),a=g("#topbar-m [data-a=tb-bell]"),m=g("#side-tog");return [Math.round(l.right),Math.round(f.left),Math.round(f.right),Math.round(a.left),Math.round(m.right),Math.round(g("#side").height),innerWidth]})()')
    ok('순서: 로고 … 새로고침, 알림, 계정, ☰ / 막대 낮음 / 가로 안 넘침', r[0]<r[1]<r[2]<=r[3] and r[4]<=r[6] and r[5]<=64, str(r))
    await T.evaluate('window.__rl=0; const o=location.reload.bind(location)'); 
    async with T.expect_navigation(timeout=5000):
      await T.click('#side-refresh')
    ok('누르면 새로고침됨', True)
    await T.wait_for_timeout(800)
    await T.set_viewport_size({'width':1280,'height':900}); await T.wait_for_timeout(300)
    ok('PC: 새로고침 버튼은 안 보임', not await T.is_visible('#side-refresh'))
    # 단계별 질문
    await T.click('[data-a=create]'); await T.wait_for_timeout(500)
    await T.click('[data-a=goal][data-v=look]'); await T.wait_for_timeout(300)
    if not await T.query_selector('.qstep textarea'):
      await T.click('[data-a=q-custom]'); await T.wait_for_timeout(300)
    ta=await T.query_selector_all('.qstep textarea:not(.qhint)')
    ok('질문 칸이 여러 줄 상자(textarea)', len(ta)>=1)
    h0=await T.evaluate('document.querySelector(".qstep textarea:not(.qhint)").getBoundingClientRect().height')
    ok('한 줄짜리보다 높음', h0>=50, str(h0))
    long='일제강점기에 놓인 철도는 누구를 위해 어디와 어디를 이었으며, 그 결과 조선 사람들의 삶과 경제는 어떻게 달라졌다고 볼 수 있을까요? 근거를 들어 설명해 보세요.'[:160]
    await T.click('.qstep textarea:not(.qhint)'); await T.keyboard.type(long[:60]); await T.keyboard.press('Enter'); await T.keyboard.type(long[60:])
    v=await T.evaluate('document.querySelector(".qstep textarea:not(.qhint)").value')
    h1=await T.evaluate('document.querySelector(".qstep textarea:not(.qhint)").getBoundingClientRect().height')
    ok('엔터로 줄이 나뉘지 않음', '\n' not in v, repr(v[:70]))
    ok('긴 질문이면 상자가 커짐', h1>h0, f'{h0}->{h1}')
    await T.set_viewport_size({'width':390,'height':780}); await T.wait_for_timeout(400)
    hm=await T.evaluate('document.querySelector(".qstep textarea:not(.qhint)").getBoundingClientRect().height')
    ok('휴대폰에서는 여러 줄로 보임(글이 잘리지 않음)', hm>=80 and await T.evaluate('(()=>{const e=document.querySelector(".qstep textarea:not(.qhint)");return e.scrollHeight<=e.clientHeight+3})()'), str(hm))
    await T.screenshot(path='/tmp/claude-0/smoke/t75_m.png')
    await T.set_viewport_size({'width':1280,'height':900})
    saved=await T.evaluate('(()=>{const f=S.form.create;return (f.qs||[])[0]?.q||""})()')
    ok('고친 질문이 저장됨', saved==v and len(v)>60, saved[:30])
    await T.screenshot(path='/tmp/claude-0/smoke/t75_q.png')
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
