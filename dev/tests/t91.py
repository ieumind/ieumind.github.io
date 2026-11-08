# 💬 실시간 토론: 휴대폰 화면(입력창 하단 고정·넘침 없음) · 체험 모드 · 학생 화면 미리보기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda pg,ms=250: pg.wait_for_timeout(ms)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    ctx=await b.new_context(viewport={'width':1200,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=tpl][data-v=live]'); await W(T)
    await T.select_option('#c-team','teacher'); await T.fill('#c-prompt','임시 정부는 큰 성과를 거두었다.'); await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,400)
    m=await b.new_context(viewport={'width':390,'height':760}, has_touch=True, is_mobile=True); await m.route(re.compile(r'https://.*'), lambda r: r.abort())
    # 같은 localStorage를 쓰려면 같은 컨텍스트여야 함 → 휴대폰 크기 페이지를 같은 컨텍스트에서 연다
    K=await ctx.new_page(); await K.set_viewport_size({'width':390,'height':760}); K.on('pageerror',lambda e:errs.append('K:'+str(e)))
    await K.goto(U+'?who=anon#'+rid); await W(K,500); await K.fill('#g-nick','김가온'); await K.click('[data-a=guest-join]'); await W(K,1600)
    ok('교사 지정 방식: 팀 배정 대기', '팀 배정 대기' in await K.inner_text('.lvme') and await K.locator('#lv-in').count()==0)
    await W(T,900)
    ok('교사: 대기 1명 · 자동으로 나누기 버튼', await T.locator('[data-a=lv-auto]').count()==1)
    k=await T.evaluate(f'[...lv(S.rooms.find(r=>r.id==="{rid}")).members.keys()][0]')
    await T.click(f'[data-a=lv-team][data-k="{k}"][data-v=con]'); await W(T,400); await W(K,1000)
    ok('팀을 정하면 학생 입력창 열림', await K.locator('#lv-in').count()==1 and '반대' in await K.inner_text('.lvme'))
    for i in range(14):
      await K.evaluate(f'(()=>{{const L=lv(S.rooms.find(r=>r.id==="{rid}"));for(let j=0;j<1;j++){{const id=1000+{i};L.msgs.set(id,{{id,mkey:"x",nick:"논객"+{i},team:{i}%2?"pro":"con",body:"긴 메시지 ".repeat(8),deleted:false,created_at:new Date().toISOString()}})}}}})()')
    await K.evaluate(f'liveRefresh(S.rooms.find(r=>r.id==="{rid}"),"msg")'); await W(K,300)
    await K.evaluate('scrollTo(0, 0)'); await W(K,200)
    box=await K.evaluate('(()=>{const c=document.querySelector(".lvcomp").getBoundingClientRect();return {top:c.top,bottom:c.bottom,vh:innerHeight}})()')
    ok('휴대폰: 입력창이 화면 아래에 붙어 보임', box['bottom']<=box['vh']+1 and box['bottom']>box['vh']-90, str(box))
    ok('휴대폰: 가로 넘침 없음', await K.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    ok('입력 글자 크기 16px(아이폰 확대 방지)', await K.evaluate('getComputedStyle(document.getElementById("lv-in")).fontSize')=='16px')
    await K.screenshot(path='/tmp/claude-0/lv_m_student.png')
    # 교사 휴대폰
    await T.set_viewport_size({'width':390,'height':844}); await W(T,400)
    ok('교사 휴대폰: 가로 넘침 없음', await T.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    await T.screenshot(path='/tmp/claude-0/lv_m_teacher.png', full_page=True)
    # 미리보기
    await T.set_viewport_size({'width':1200,'height':900}); await T.click('[data-a=preview][data-id="%s"]'%rid); await W(T,700)
    ok('학생 화면 미리보기: 채팅은 보이지만 보낼 수 없음', await T.locator('#lv-msgs').count()==1 and '미리보기' in await T.inner_text('.lvcomp'))
    await ctx.close()
    # 체험 모드
    d=await b.new_context(viewport={'width':1200,'height':900}); D=await d.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,800); await D.evaluate('S.tour=null; act("open",{dataset:{id:"demo-live"}})'); await W(D,700)
    ok('체험: 예시 학생 6명·메시지 6개', '6' in await D.inner_text('#lv-kpis') and await D.locator('#lv-msgs .lvm').count()==6)
    await D.click('#lv-msgs [data-a=lv-del] >> nth=0'); await W(D,300); ok('체험: 메시지 지우기', await D.locator('#lv-msgs .lvm.del').count()==1)
    await D.click('[data-a=lv-state][data-v=ended]'); await W(D,300); await D.click('[data-a=lv-state][data-v=vote]'); await W(D,300)
    ok('체험: 종료 → 투표 시작', '투표 중' in await D.inner_text('.lvctl'))
    await D.click('[data-a=lv-state][data-v=result]'); await W(D,300); ok('체험: 결과 공개', '결과' in await D.inner_text('.lvctl'))
    await D.screenshot(path='/tmp/claude-0/lv_demo.png', full_page=True)
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
