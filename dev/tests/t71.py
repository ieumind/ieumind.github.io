# 둘러보기 10~13번(새 활동 / 학생 화면 미리보기 / 학생 관리 메뉴 / 오류·건의하기): PC·휴대폰 모두 화면의 실제 버튼을 비춘다
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/pdemo.html?demo=1'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for name,w,h in [('PC',1280,900),('휴대폰',390,780)]:
      c=await b.new_context(viewport={'width':w,'height':h}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
      await P.goto(U); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(800)
      for i,key in [(9,'새 활동'),(10,'학생 화면 미리보기'),(11,'개별 안내'),(12,'오류·건의하기')]:
        await P.evaluate(f'tourGo({i})'); await P.wait_for_timeout(500)
        r=await P.evaluate('''(()=>{const h=document.querySelector(".tour-hole");if(!h)return null;const a=h.getBoundingClientRect(),c=document.querySelector(".tour-card").getBoundingClientRect();
          const mid=[a.left+a.width/2,a.top+a.height/2];const t=document.elementsFromPoint(mid[0],mid[1]).find(e=>!e.closest("#tour"));
          return {top:a.top,bottom:a.bottom,inview:a.top>=0&&a.bottom<=innerHeight,text:(t?.closest("button,a,[data-a]")?.textContent||"").replace(/\\s+/g," ").trim().slice(0,30),overlap:!(c.bottom<=a.top||c.top>=a.bottom)}})()''')
        ok(f'{name} {i+1}번({key}): 강조 상자가 화면 안', bool(r) and r['inview'], str(r))
        ok(f'{name} {i+1}번: 가리키는 버튼 글자', bool(r) and key in r['text'], str(r and r['text']))
        ok(f'{name} {i+1}번: 설명 카드가 강조 상자를 안 가림', bool(r) and not r['overlap'])
      await c.close()
    # 휴대폰 9번: 미참여(김가온)가 아니라 결과물이 있는 이하린 카드를 비춘다
    c=await b.new_context(viewport={'width':390,'height':780}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page()
    await P.goto(U); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(800)
    await P.evaluate('tourGo(8)'); await P.wait_for_timeout(500)
    t=await P.evaluate('''(()=>{const h=document.querySelector(".tour-hole").getBoundingClientRect();const e=document.elementsFromPoint(h.left+h.width/2,h.top+60).find(x=>!x.closest("#tour"));return (e?.closest(".post")?.textContent||"").replace(/\\s+/g," ").slice(0,30)})()''')
    ok('휴대폰 9번: 이하린 카드를 비춤', '이하린' in t, t)
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
