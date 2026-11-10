# 💬 실시간 토론: 휴대폰 화면(대기실·입력창 하단 고정·탭·넘침 없음) · 체험 모드 · 학생 화면 미리보기
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
    await T.select_option('#c-selfmove','off'); await T.fill('#c-prompt','임시 정부는 큰 성과를 거두었다.'); await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    ME=f'lv(S.rooms.find(r=>r.id==="{rid}")).me'
    async def stu(nm, w=390):
      K=await ctx.new_page(); await K.set_viewport_size({'width':w,'height':760}); K.on('pageerror',lambda e:errs.append(nm+':'+str(e)))
      await K.goto(U+'?who=anon#'+rid); await W(K,500); await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1600); return K
    K=await stu('김가온'); A=await stu('나다은'); C=await stu('박서준')
    ok('휴대폰 대기실: 가로 넘침 없음', await K.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    ok('휴대폰 대기실: 역할 버튼 터치 크기(44px 이상)', await K.evaluate('[...document.querySelectorAll(".lvrole")].every(b=>b.getBoundingClientRect().height>=44)'))
    ok('교사만 정하는 방식: 학생 역할 버튼 비활성', await K.evaluate('[...document.querySelectorAll(".lvrole")].every(b=>b.disabled)') and '선생님이 역할을 정해' in await K.inner_text('.lvlobby'))
    r=await K.evaluate(f'SB.rpc("debate_move",{{p_room:"{rid}",p_team:"pro"}})'); ok('서버도 학생 이동 거절(selfoff)', r['data']['reason']=='selfoff', str(r))
    await W(T,900)
    ks=await T.evaluate(f'[...lv(S.rooms.find(r=>r.id==="{rid}")).members.values()].map(m=>[m.mkey,m.real_name])')
    mk={n:k for k,n in ks}
    await T.click(f'[data-a=lv-team][data-k="{mk["나다은"]}"][data-v=pro]'); await W(T,500)
    await T.click(f'[data-a=lv-team][data-k="{mk["김가온"]}"][data-v=con]'); await W(T,500); await W(K,1100)
    nk=await K.evaluate(ME); ok('교사가 지정하면 학생에게 반영·닉네임 새로 부여', nk['team']=='con' and nk['nick']=='반대01', str(nk))
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,500); await W(K,1100); await W(C,300)
    ok('휴대폰 토론방: 탭 3개 표시(채팅·청중 의견·현황)', await K.locator('.lvtabs').is_visible() and await K.locator('.lvtab').count()==3)
    ok('휴대폰: 채팅 탭이 기본, 청중 의견은 숨김', await K.locator('.lvchat').is_visible() and not await K.locator('.lvnotes').is_visible())
    for i in range(14):
      await K.evaluate(f'(()=>{{const L=lv(S.rooms.find(r=>r.id==="{rid}"));const id=1000+{i};L.msgs.set(id,{{id,mkey:"x",nick:"찬성"+{i},team:{i}%2?"pro":"con",body:"긴 메시지 ".repeat(8),deleted:false,created_at:new Date().toISOString()}})}})()')
    await K.evaluate(f'liveRefresh(S.rooms.find(r=>r.id==="{rid}"),"msg")'); await W(K,300)
    await K.evaluate('scrollTo(0, 0)'); await W(K,200)
    box=await K.evaluate('(()=>{const c=document.querySelector(".lvchat .lvcomp").getBoundingClientRect();return {top:c.top,bottom:c.bottom,vh:innerHeight}})()')
    ok('휴대폰: 입력창이 화면 아래에 붙어 보임', box['bottom']<=box['vh']+1 and box['bottom']>box['vh']-90, str(box))
    ok('휴대폰: 가로 넘침 없음', await K.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    ok('입력 글자 크기 16px(아이폰 확대 방지)', await K.evaluate('getComputedStyle(document.getElementById("lv-in")).fontSize')=='16px')
    # 판정단 휴대폰: 의견 탭으로 전환해 쓰기
    ok('판정단 휴대폰: 채팅 입력창 없음', await C.locator('#lv-in').count()==0)
    await C.click('[data-a=lv-tab][data-v=notes]'); await W(C,400)
    ok('휴대폰: 청중 의견 탭 → 의견 목록·쓰기 칸 표시', await C.locator('.lvnotes').is_visible() and await C.locator('#lv-note').is_visible() and not await C.locator('.lvchat').is_visible())
    ok('휴대폰: 의견 글자 크기 16px', await C.evaluate('getComputedStyle(document.getElementById("lv-note")).fontSize')=='16px' and await C.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    await C.fill('#lv-note','질문이 있어요.'); await C.click('[data-a=lv-note-send]'); await W(C,700)
    await W(K,1000)
    ok('새 의견이 오면 다른 탭에 알림 점', await K.locator('#lv-tabn').is_visible() and (await K.inner_text('#lv-tabn'))=='1')
    await K.click('[data-a=lv-tab][data-v=notes]'); await W(K,300); ok('탭을 열면 알림 점이 사라지고 의견이 보임', not await K.locator('#lv-tabn').is_visible() and '질문이 있어요' in await K.inner_text('#lv-notelist'))
    await K.screenshot(path='/tmp/claude-0/lv_m_student.png')
    await C.screenshot(path='/tmp/claude-0/lv_m_jury.png')
    # 넓은 화면은 나란히
    W2=await stu('최서아', 1200); ok('넓은 화면: 탭 숨김·채팅과 의견 나란히', not await W2.locator('.lvtabs').is_visible() and await W2.locator('.lvchat').is_visible() and await W2.locator('.lvnotes').is_visible())
    await T.set_viewport_size({'width':390,'height':844}); await W(T,400)
    ok('교사 휴대폰: 가로 넘침 없음', await T.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    await T.screenshot(path='/tmp/claude-0/lv_m_teacher.png', full_page=True)
    await T.set_viewport_size({'width':1200,'height':900}); await T.click('[data-a=preview][data-id="%s"]'%rid); await W(T,700)
    ok('학생 화면 미리보기: 채팅은 보이지만 보낼 수 없음', await T.locator('#lv-msgs').count()==1 and '미리보기' in await T.inner_text('.lvchat .lvcomp'))
    await ctx.close()
    # 체험 모드
    d=await b.new_context(viewport={'width':1200,'height':900}); D=await d.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,800); await D.evaluate('S.tour=null; act("open",{dataset:{id:"demo-live"}})'); await W(D,700)
    ok('체험: 예시 학생 8명(판정단 2)·메시지 6개·의견 2개', '8' in await D.inner_text('#lv-kpis') and await D.locator('#lv-msgs .lvm').count()==6 and await D.locator('#lv-notelist .lvn').count()==2 and '찬성01' in await D.inner_text('.lvmem'))
    await D.click('#lv-msgs [data-a=lv-del] >> nth=0'); await W(D,300); ok('체험: 메시지 지우기', await D.locator('#lv-msgs .lvm.del').count()==1)
    await D.click('#lv-notelist [data-a=lv-note-del] >> nth=0'); await W(D,300); ok('체험: 의견 지우기', await D.locator('#lv-notelist .lvn.del').count()==1)
    await D.click('[data-a=lv-state][data-v=ended]'); await W(D,300); await D.click('[data-a=lv-state][data-v=vote]'); await W(D,300)
    ok('체험: 종료 → 투표 시작', '투표 중' in await D.inner_text('.lvctl'))
    await D.click('[data-a=lv-state][data-v=result]'); await W(D,300); ok('체험: 결과 공개', '결과' in await D.inner_text('.lvctl'))
    await D.screenshot(path='/tmp/claude-0/lv_demo.png', full_page=True)
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
