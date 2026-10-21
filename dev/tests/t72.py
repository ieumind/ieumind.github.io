# 휴대폰 학생 코드 입력 화면: ‘시작하기’ 막대가 맨 아래 고정, 그 아래는 같은 색으로 덮임
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
    c=await b.new_context(viewport={'width':390,'height':700}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto(U); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(1000)
    f=lambda: P.evaluate('(()=>{const e=document.querySelector(".foot.fixb"),r=e.getBoundingClientRect(),a=getComputedStyle(e,"::after");return [getComputedStyle(e).position,Math.round(r.bottom),innerHeight,a.position,parseFloat(a.height),a.backgroundColor,getComputedStyle(e).backgroundColor]})()')
    r=await f(); ok('시작하기 막대가 맨 아래에 고정', r[0]=='fixed' and r[1]==r[2], str(r))
    ok('막대 아래를 같은 색으로 덮음', r[3]=='absolute' and r[4]>=300 and r[5]==r[6] and r[5]!='rgba(0, 0, 0, 0)', str(r))
    await P.evaluate('scrollTo(0,document.body.scrollHeight)'); await P.wait_for_timeout(200)
    ok('맨 끝까지 내려도 입력칸·안내가 막대에 안 가림', await P.evaluate('(()=>{const h=document.querySelector(".card:has(> .foot.fixb) .hint").getBoundingClientRect();return h.bottom<=document.querySelector(".foot.fixb").getBoundingClientRect().top+1})()'))
    await P.screenshot(path='/tmp/claude-0/smoke/t72_m.png')
    await P.set_viewport_size({'width':1280,'height':800}); await P.wait_for_timeout(300)
    ok('PC: 예전처럼 카드 안 막대', await P.evaluate('getComputedStyle(document.querySelector(".foot.fixb")).position')!='fixed')
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
