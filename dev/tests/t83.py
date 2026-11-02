# 휴대폰: 학습 나눔 교사 화면이 짧아졌는지(설정 접기·필터 한 줄·알림 줄 접기·카드 높이)
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
    for name,w,h in (('휴대폰',390,844),('PC',1280,900)):
      ctx=await b.new_context(viewport={'width':w,'height':h}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
      await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
      names='\n'.join(f'1{i//10:02d}{i%10+1:02d} 학생{i}' for i in range(18))
      await T.evaluate('act("roster-open",{dataset:{}})'); await T.wait_for_timeout(250); await T.fill('#roster-add',names); await T.click('[data-a=roster-add]'); await T.wait_for_timeout(400); await T.keyboard.press('Escape'); await T.wait_for_timeout(250)
      await T.evaluate('act("create",{dataset:{}})'); await T.wait_for_timeout(300); await T.click('[data-a=goal][data-v=notes]'); await T.wait_for_timeout(300)
      await T.fill('#c-memoq','광복했는데도 왜 하나의 정부를 바로 만들지 못했을까?') if await T.locator('#c-memoq').count() else None
      await T.click('[data-a=create-save]'); await T.wait_for_timeout(800)
      rid=await T.evaluate('S.roomId')
      await T.evaluate('''(rid)=>{ const now=Date.now(); S.roster && 0; S.posts=S.posts.filter(p=>p.roomId!==rid); for(let i=0;i<4;i++) S.posts.push({id:"np"+i,roomId:rid,author:`10${i}0${i+1} 학생${i}`,status:"submitted",notes:{images:[],files:[{d:"data:text/plain;base64,aGk=",n:"a.pdf",s:1000}],memo:"메모",submittedAt:now,version:1}}); S.ttab="students"; render() }''', rid)
      await T.evaluate('act("ttab",{dataset:{v:"students"}})'); await T.wait_for_timeout(700)
      first=await T.evaluate('(()=>{const c=document.querySelector(".ncards .ncard"); return c?Math.round(c.getBoundingClientRect().top+scrollY):-1})()')
      ok(f'{name} 학생 카드 시작 위치', first>0, str(first)+'px')
      await T.screenshot(path=f'/tmp/claude-0/smoke/t83_{name}.png', full_page=False)
      if w<=700:
        ok('휴대폰: 카드가 첫 화면 안(1000px 이내)에서 시작', first<1000, str(first))
        ok('휴대폰: 활동 설정은 접힘', await T.evaluate('!document.querySelector(".nset").open'))
        ok('휴대폰: 요약에 현재 상태', '파일 끔' in await T.inner_text('.nset > summary'), await T.inner_text('.nset > summary'))
        ok('휴대폰: 숫자 카드 한 줄', await T.evaluate('(()=>{const k=[...document.querySelectorAll(".kpis.nk .kpi")].map(e=>Math.round(e.getBoundingClientRect().top));return new Set(k).size===1})()'))
        ok('휴대폰: 필터 칩 한 줄(가로 스크롤)', await T.evaluate('(()=>{const k=[...document.querySelectorAll(".nbar .mfilters button")].map(e=>Math.round(e.getBoundingClientRect().top));return new Set(k).size===1})()'))
        ok('휴대폰: 학교·반/검색이 한 줄', await T.evaluate('(()=>{const a=document.querySelector("#n-q"),c=document.querySelector("#n-cls");return !c||Math.abs(a.getBoundingClientRect().top-c.getBoundingClientRect().top)<6})()'))
        ok('휴대폰: 알림 줄은 한 버튼만', await T.evaluate('(()=>{const n=document.querySelector("#nudge-bar");return !n||[...n.children].filter(e=>getComputedStyle(e).display!=="none").length===1})()'))
        ok('휴대폰: 페이지 가로 넘침 없음', await T.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        await T.click('.nset > summary'); await T.wait_for_timeout(250); ok('설정 펼치면 토글이 보임', await T.locator('[data-a=note-files]:visible').count()==2)
        await T.click('[data-a=note-files][data-v=on]'); await T.wait_for_timeout(500); ok('토글 동작 + 요약 갱신', '파일 켬' in await T.inner_text('.nset > summary') and await T.evaluate('document.querySelector(".nset").open'))
        await T.click('.nset > summary'); await T.wait_for_timeout(200)
        if await T.locator('.nudge-go').count():
          await T.click('.nudge-go'); await T.wait_for_timeout(500)
          ok('알림 버튼 → 미제출 필터로 이동', await T.locator('.mfilters button[data-v=none][aria-pressed=true]').count()==1)
          ok('필터 후 알림 줄 전체가 보임', await T.locator('[data-a=nudge-all]:visible').count()==1)
          await T.click('[data-a=nudge-all]'); await T.wait_for_timeout(400)
          ok('학생을 고르면 알림 줄이 화면 아래에 따라다님(sticky)', await T.evaluate('getComputedStyle(document.querySelector("#nudge-bar")).position')=='sticky')
        else: ok('알림 줄(이 환경에서는 알림 기능 꺼짐)', True, 'skip')
      else:
        ok('PC: 활동 설정은 펼쳐 있음', await T.evaluate('document.querySelector(".nset").open'))
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
