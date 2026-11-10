# 실시간 토론 화면 개편(2026-11-10l~): ① 대기실 — 역할 카드 안에 명단, 내 자리 표시, 겹치던 아래 명단 없음
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda pg,ms=300: pg.wait_for_timeout(ms)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=tpl][data-v=live]'); await W(T,300)
    await T.fill('#c-prompt','반민특위는 정말 필요했을까?'); await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(nm+':'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1500); return K
    A=await stu('김가온'); B=await stu('나다은'); C=await stu('박서준')
    await A.click('.lvrole.pro'); await W(A,700); await B.click('.lvrole.con'); await W(B,700)
    await W(C,3500)
    # ① 대기실
    ok('역할 카드 3개(카드 안에 명단)', await C.locator('.lvslot').count()==3 and await C.locator('.lvslot .lr-l').count()==3)
    pro=await C.locator('.lvslot.pro .lr-l').inner_text(); con=await C.locator('.lvslot.con .lr-l').inner_text()
    ok('찬성 카드에 찬성01, 반대 카드에 반대01', '찬성01' in pro and '반대01' in con, f'{pro!r} {con!r}')
    ok('아래에 겹치던 명단 칸 없음', await C.locator('.lvroster').count()==0 and await C.locator('.lvcol').count()==0)
    mine=await A.locator('#lv-mine').inner_text()
    ok('내 자리 크게(찬성팀·닉네임)', '찬성팀' in mine and '찬성01' in mine, mine)
    ok('내 카드 표시', await A.locator('.lvslot.pro.me').count()==1 and '지금 내 자리' in await A.locator('.lvslot.pro').inner_text())
    ok('다른 카드는 옮기기 안내', '이 자리로 옮기기' in await C.locator('.lvslot.pro').inner_text())
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails); raise SystemExit(1 if fails else 0)
asyncio.run(main())
