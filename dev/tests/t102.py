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
    # ② 토론 시작 → 머리 카드(진행·내 역할·참여) + 채팅 위 ‘◀ 찬성 · 반대 ▶’ 띠, 찬성 왼쪽·반대 오른쪽
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,900)
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,1500); await W(A,1200)
    await A.fill('#lv-in','반민특위는 꼭 필요했어요.'); await A.click('[data-a=lv-send]'); await W(A,700)
    await W(B,900); await B.fill('#lv-in','국가 안정이 먼저였어요.'); await B.click('[data-a=lv-send]'); await W(B,1200); await W(C,1200)
    ok('머리 카드 3칸', await C.locator('.lvhead2 .lvh-cell').count()==3)
    hc=await A.locator('.lvhead2').inner_text()
    ok('머리 카드에 논제·LIVE·내 역할·참여', '반민특위는 정말 필요했을까?' in hc and 'LIVE' in hc and '찬성01' in hc and '찬성 1/4' in hc, hc.replace('\n',' | '))
    ok('채팅 위 좌우 띠', await A.locator('.lvsides .pro').count()==1 and await A.locator('.lvsides .con').count()==1)
    al=await C.evaluate('[...document.querySelectorAll("#lv-msgs .lvm")].map(x=>[x.classList.contains("con")?"con":"pro", getComputedStyle(x).alignSelf])')
    ok('찬성 왼쪽·반대 오른쪽', al==[['pro','flex-start'],['con','flex-end']], al)
    # ③ 현황 패널: 팀별 발언 수 · 말하지 않은 토론자 수 / 휴대폰에서는 ‘현황’ 탭
    st=await C.locator('#lv-stat').inner_text()
    ok('현황: 찬성 1개·반대 1개 발언', '찬성 발언 1개' in st.replace('\n',' ') and '반대 발언 1개' in st.replace('\n',' '), st.replace('\n',' | '))
    ok('현황: 말하지 않은 토론자 0명', '찬성 0명 · 반대 0명' in st, st)
    ok('넓은 화면: 채팅 옆에 의견과 현황이 함께', await C.locator('.lvside .lvnotes').is_visible() and await C.locator('.lvside .lvstat').is_visible())
    await C.set_viewport_size({'width':390,'height':844}); await W(C,300)
    ok('휴대폰: 탭 3개', await C.locator('.lvtab').count()==3)
    await C.click('.lvtab[data-v=stat]'); await W(C,400)
    ok('휴대폰: 현황 탭을 누르면 현황만', await C.locator('#lv-stat').is_visible() and not await C.locator('.lvchat').is_visible() and not await C.locator('.lvnotes').is_visible())
    await C.click('.lvtab[data-v=chat]'); await W(C,300); await C.set_viewport_size({'width':1280,'height':900})
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails); raise SystemExit(1 if fails else 0)
asyncio.run(main())
