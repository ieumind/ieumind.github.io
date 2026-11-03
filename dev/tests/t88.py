# 활동 카드: 삭제는 ⋯ 메뉴 · 도구 줄 한 줄 · 긴 제목 두 줄까지
import asyncio, re
from playwright.async_api import async_playwright
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda P,t: P.wait_for_timeout(t)
LONG='드라마 <100일의 거짓말> 요약본 시청 및 생각 나누기 그리고 이어서 모둠별로 토의한 뒤 개인 정리까지 하는 아주 긴 이름의 활동'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for name,w,h in (('PC',1100,900),('PC넓게',1400,900),('휴대폰',390,844)):
      ctx=await b.new_context(viewport={'width':w,'height':h}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      P=await ctx.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
      await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(P,800)
      await P.evaluate('S.tour=null; S.mcourse=""; S.mview="card"; S.mf="all"; const r=S.rooms.find(x=>statusOf(x)==="closed")||S.rooms[0]; S.rooms.push({...r,id:"longroom",title:%r,status:"closed"}); render()' % LONG); await W(P,500)
      cards=await P.locator('.mcard').count(); ok(f'{name} 카드 있음', cards>=2, str(cards))
      r=await P.evaluate('''()=>{const out=[];document.querySelectorAll(".mcard").forEach(c=>{const t=c.querySelector(".mctools");if(!t)return;const tops=[...t.querySelectorAll(":scope > button, :scope > .mmore")].map(e=>Math.round(e.getBoundingClientRect().top));const h2=c.querySelector("h2"),lh=parseFloat(getComputedStyle(h2).lineHeight);out.push({one:new Set(tops).size===1,lines:Math.round(h2.getBoundingClientRect().height/lh),over:c.scrollWidth>c.clientWidth+1})});return out}''')
      ok(f'{name} 도구 줄이 모든 카드에서 한 줄', all(x['one'] for x in r), str(r[:6]))
      ok(f'{name} 제목은 최대 두 줄', all(x['lines']<=2 for x in r), str([x['lines'] for x in r]))
      ok(f'{name} 가로 넘침 없음', not any(x['over'] for x in r) and await P.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
      ok(f'{name} 긴 제목 전체가 마우스 올리면 보임(title)', await P.evaluate('[...document.querySelectorAll(".mcard h2 button")].some(b=>b.title.includes("아주 긴 이름"))'))
      if w>700:
        # 같은 줄 카드의 버튼 줄 위치가 맞는지(제목 최소 높이)
        ok(f'{name} 같은 줄 카드의 ‘결과 보기’ 줄이 맞음', await P.evaluate('''()=>{const rows={};document.querySelectorAll(".mcard").forEach(c=>{const y=Math.round(c.getBoundingClientRect().top),b=c.getBoundingClientRect().bottom-c.querySelector(".macts").getBoundingClientRect().top;(rows[y]=rows[y]||[]).push(Math.round(b))});return Object.values(rows).every(a=>Math.max(...a)-Math.min(...a)<=2)}'''))
      # ⋯ 메뉴
      await P.evaluate('document.querySelector(".mcard .mmore summary").scrollIntoView({block:"center"})'); await W(P,200)
      ok(f'{name} 삭제는 처음엔 숨겨짐', not await P.locator('.mcard .mmore-pop >> visible=true').count())
      await P.locator('.mcard .mmore summary').first.click(); await W(P,200)
      ok(f'{name} ⋯ 누르면 삭제 메뉴', await P.locator('.mcard .mmore[open] .mmore-pop button.del').first.is_visible())
      await P.screenshot(path=f'/tmp/claude-0/cards_{name}.png')
      await P.mouse.click(5,5); await W(P,200)
      ok(f'{name} 바깥을 누르면 닫힘', not await P.locator('.mmore[open]').count())
      await P.locator('.mcard .mmore summary').first.click(); await W(P,150); await P.keyboard.press('Escape'); await W(P,150)
      ok(f'{name} Esc로 닫힘', not await P.locator('.mmore[open]').count())
      await P.locator('.mcard .mmore summary').first.click(); await W(P,150); await P.locator('.mmore[open] button.del').click(); await W(P,300)
      ok(f'{name} 삭제 누르면 확인 창', await P.evaluate('S.modal?.type')=='del')
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
