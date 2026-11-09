# 🔔 알림 켠 학생 표시: 학생 명단·출석부에 표시, 켜지 않은 학생은 표시 없음
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
    await T.evaluate('''(()=>{const k="__sbmock"; const D=JSON.parse(localStorage.getItem(k)||"{}"); D.students=[{id:"s1",tid:"T",school:"",number:"1",name:"가나",code:"AAA111"},{id:"s2",tid:"T",school:"",number:"2",name:"다라",code:"BBB222"}]; localStorage.setItem(k,JSON.stringify(D)); window.__k=k})()''')
    await T.evaluate('window.__pushWho=["s1"]')
    await T.evaluate('S.roster=undefined; act("roster-open")'); await T.wait_for_timeout(900)
    html=await T.inner_html('.ptable tbody')
    ok('명단: 알림 켠 학생에 🔔', html.count('pushmk')==1 and html.index('가나')<html.index('pushmk')<html.index('다라'), html.count('pushmk'))
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
