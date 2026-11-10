# 실시간 토론(2026-11-10w): 교사 참여 학생 목록(한 줄·거르기·찾기) + 연결 상태(presence)
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
    await A.click('.lvrole.pro'); await W(A,700); await B.click('.lvrole.con'); await W(B,700); await W(C,2500)
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,3000)
    sm=await T.locator('#lv-presn').inner_text()
    ok('제목 줄: 접속 3 / 3명', '접속 3 / 3명' in sm, sm)
    ok('세 학생 모두 초록 점', await T.locator('.lvmem .lvmdot.on').count()==3)
    h=(await T.locator('.lvmem li').first.bounding_box())['height']
    ok('한 줄 높이 48px 이하', h<=48, h)
    ok('역할 버튼은 그대로(data-v 3개씩)', await T.locator('[data-a=lv-team][data-v=jury]').count()==3)
    mf=await T.locator('.lvmf').inner_text()
    ok('거르기 칩: 전체·찬성·반대·판정단', all(k in mf for k in ['전체','찬성','반대','판정단']), mf)
    await T.click('[data-a=lv-memf][data-v=pro]'); await W(T,200)
    ok('찬성만 보기', await T.locator('.lvmem li').count()==1 and '김가온' in await T.locator('.lvmem').inner_text())
    await T.click('[data-a=lv-memf][data-v=all]'); await W(T,200)
    await T.fill('#lv-memq','박서'); await W(T,200)
    ok('이름 찾기', await T.locator('.lvmem li').count()==1 and '박서준' in await T.locator('.lvmem').inner_text())
    ok('찾는 중에도 입력칸 포커스 유지', await T.evaluate('document.activeElement && document.activeElement.id')=='lv-memq')
    await T.fill('#lv-memq',''); await W(T,200)
    await T.screenshot(path='/tmp/claude-0/scr/mem_on.png')
    # 나다은이 다른 앱으로: 10초 유예 뒤 ‘다른 화면’
    ok('학생 안내: 선생님이 볼 수 있어요', '누가 지금 토론 화면을 보고 있는지' in await B.locator('.lvh-note').inner_text())
    HIDE="Object.defineProperty(document,'visibilityState',{get:()=>'hidden',configurable:true}); document.dispatchEvent(new Event('visibilitychange'))"
    SHOW="Object.defineProperty(document,'visibilityState',{get:()=>'visible',configurable:true}); document.dispatchEvent(new Event('visibilitychange'))"
    await B.evaluate(HIDE); await W(T,4000)
    ok('잠깐(4초)은 아직 보는 중', await T.locator('.lvmem .lvmdot.away').count()==0)
    await W(T,9000)
    li=await T.locator('.lvmem li', has_text='나다은').inner_text()
    ok('10초 넘으면 다른 화면(노란 점)', await T.locator('.lvmem .lvmdot.away').count()==1 and '다른 화면' in li, li)
    ok('제목 줄: 접속 3 · 다른 화면 1', '다른 화면 1' in await T.locator('#lv-presn').inner_text() and '접속 3 / 3명' in await T.locator('#lv-presn').inner_text())
    # 넘침 검사: 판정단 + 직접 닉네임(되돌리기 버튼) + 다른 화면, 좁은 칸
    await T.evaluate("(()=>{const r=room(); r.liveCfg={...(r.liveCfg||{}),nickMode:'custom'}; const L=lv(r); for(const m of L.members.values()){ m.nick_set=true; if(m.real_name==='나다은') m.nick='아주긴닉네임김찬성' } liveMemRepaint(r)})()")
    for vw in [1280, 1024, 1440]:
        await T.set_viewport_size({'width':vw,'height':900}); await W(T,300); await T.evaluate('liveMemRepaint(room())'); await W(T,100)
        bad=await T.evaluate("""[...document.querySelectorAll('.lvmem li')].filter(li=>{const R=li.getBoundingClientRect(); return [...li.querySelectorAll('button,.lvseg-s')].some(b=>b.getBoundingClientRect().right>R.right+1)}).map(li=>li.innerText.replace(/\n/g,' '))""")
        ok(f'목록 줄 넘침 없음({vw}px)', not bad, bad)
    st=await T.locator('.lvmem li', has_text='나다은').locator('.lvmem-n .small').inner_text()
    ok('상태 글자가 닉네임보다 앞', st.startswith('다른 화면'), st)
    await T.set_viewport_size({'width':1280,'height':900}); await W(T,300)
    await T.locator('.lvmemd').screenshot(path='/tmp/claude-0/scr/mem_fit.png')
    await T.click('[data-a=lv-memf][data-v=away]'); await W(T,200)
    ok('다른 화면만 보기', await T.locator('.lvmem li').count()==1 and '나다은' in await T.locator('.lvmem').inner_text())
    await T.locator('.lvmemd').screenshot(path='/tmp/claude-0/scr/mem_away.png')
    await T.click('[data-a=lv-memf][data-v=all]'); await W(T,200)
    await B.evaluate(SHOW); await W(T,2500)
    ok('돌아오면 바로 보는 중', await T.locator('.lvmem .lvmdot.away').count()==0 and await T.locator('.lvmem .lvmdot.on').count()==3)
    # 박서준 창을 닫으면: 20초 유예 뒤 끊김
    await C.close(); await W(T,8000)
    ok('잠깐은 아직 초록(유예)', await T.locator('.lvmem .lvmdot.on').count()==3)
    await W(T,20000)
    sm=await T.locator('#lv-presn').inner_text()
    ok('20초 뒤: 접속 2 / 3명', '접속 2 / 3명' in sm, sm)
    ok('박서준 끊김 표시', '끊김' in await T.locator('.lvmem li', has_text='박서준').inner_text())
    await T.click('[data-a=lv-memf][data-v=off]'); await W(T,200)
    ok('끊김만 보기', await T.locator('.lvmem li').count()==1 and '박서준' in await T.locator('.lvmem').inner_text())
    await T.click('[data-a=lv-memf][data-v=all]'); await W(T,200); await T.locator('.lvmemd').screenshot(path='/tmp/claude-0/scr/mem_off.png')
    ok('학생 화면에는 목록 없음', await A.locator('#lv-memwrap').count()==0)
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS', fails)
asyncio.run(main())