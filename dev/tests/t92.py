# ⚖️ 청중 판정단: 설정 → 자동 배정(판정단) → 읽기 전용 → 투표 단계에서 3기준 판정 → 중복/공개 전 차단 → 결과(익명 이유·가리기) → 성찰·기록
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
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T)
    await T.click('[data-a=tpl][data-v=live]'); await W(T,300)
    ok('판정단 설정 칸·기본은 사용 안 함', await T.locator('#c-jury').count()==1 and await T.input_value('#c-jury')=='0')
    await T.select_option('#c-jury','20'); await W(T)
    await T.fill('#c-prompt','대한민국 임시 정부는 독립운동에 큰 성과를 거두었다.')
    await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    rm=await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}")')
    ok('저장: liveCfg.jury=20', rm['liveCfg']['jury']==20 and rm['liveCfg']['teamMode']=='auto', str(rm['liveCfg']))
    ok('교사 화면: 판정단 칸', '청중 판정단' in await T.inner_text('#lv-kpis'))
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(nm+':'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1600); return K
    ME=lambda: f'lv(S.rooms.find(r=>r.id==="{rid}")).me'
    A=await stu('김가온'); B=await stu('나다은'); C=await stu('박서준'); D=await stu('이하린')
    roles={n:(await P.evaluate(ME()))['team'] for n,P in [('A',A),('B',B),('C',C),('D',D)]}
    ok('세 번째 입장자가 판정단, 나머지는 찬반 균형', roles['C']=='jury' and sorted([roles['A'],roles['B'],roles['D']]).count('jury')==0 and abs(list(roles.values()).count('pro')-list(roles.values()).count('con'))<=1, str(roles))
    ok('판정단 화면: 역할 표시 + 회색 계열 클래스', '청중 판정단' in await C.inner_text('.lvme') and await C.locator('.lvme.jury').count()==1)
    ok('찬반 학생은 기존 표시(팀 이름)', '청중' not in await A.inner_text('.lvme'))
    me=lambda n:{'A':A,'B':B,'C':C,'D':D}[n]
    await W(T,800)
    ok('교사: 역할 3종 버튼 + 판정단 1명', await T.locator(f'[data-a=lv-team][data-k][data-v=jury]').count()==4 and '판정단' in await T.inner_text('.lvmem'))
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,400); await W(C,900)
    ok('판정단은 입력창 없음', await C.locator('#lv-in').count()==0 and await C.locator('.lvcomp').count()==1 and '읽기만' in await C.inner_text('.lvcomp'))
    ok('찬반 학생은 입력창 있음', await A.locator('#lv-in').count()==1)
    await A.fill('#lv-in','임시 헌장 제1조가 민주 공화제를 선언했어요.'); await A.keyboard.press('Enter'); await W(A,600); await W(C,900)
    ok('판정단도 찬반 메시지를 실시간으로 봄', '민주 공화제' in await C.inner_text('#lv-msgs'))
    rs=await C.evaluate(f'SB.rpc("debate_send",{{p_room:"{rid}",p_body:"끼어들기"}})'); ok('판정단 글쓰기 서버 거절', rs['data']['reason']=='jury', str(rs))
    # 종료 → 투표·판정
    await T.click('[data-a=lv-state][data-v=ended]'); await W(T,400)
    ok('교사 버튼: 최종 투표 · 판정 시작', '판정' in await T.inner_text('[data-a=lv-state][data-v=vote]'))
    await T.click('[data-a=lv-state][data-v=vote]'); await W(T,400); await W(A,900); await W(C,300)
    ok('판정단: 판정 폼(3기준)·투표 버튼 없음', await C.locator('.lvcrit').count()==3 and await C.locator('[data-a=lv-vote]').count()==0)
    ok('기준 설명 문구', '역사적 근거의 타당성' in await C.inner_text('.lvjudge') and '반박의 적절성' in await C.inner_text('.lvjudge') and '근거가 주장과 밀접하게' in await C.inner_text('.lvjudge'))
    ok('찬반 학생: 투표 버튼·판정 폼 없음', await A.locator('[data-a=lv-vote]').count()==2 and await A.locator('.lvjudge').count()==0)
    rv=await C.evaluate(f'SB.rpc("debate_vote",{{p_room:"{rid}",p_choice:"pro"}})'); ok('판정단 최종 투표 서버 거절', rv['data']['reason']=='jury', str(rv))
    rj0=await A.evaluate(f'SB.rpc("debate_judge",{{p_room:"{rid}",p_c1:"pro",p_c2:"pro",p_c3:"pro",p_reason:"찬반 학생은 못 해요"}})'); ok('찬반 학생 판정 서버 거절', rj0['data']['reason']=='denied', str(rj0))
    # 판정 제출 검증
    await C.click('[data-a=lv-judge]'); await W(C,300); ok('기준 안 고르면 안내', '고르' in await C.inner_text('body') or '골라' in await C.inner_text('body'))
    for k,v in [('c1','pro'),('c2','con'),('c3','con')]: await C.check(f'input[name="lvj:{rid}-{k}"][value={v}]')
    await C.fill(f'[id="lvj:{rid}-reason"]','너무'); await C.click('[data-a=lv-judge]'); await W(C,300)
    ok('이유가 너무 짧으면 막힘', await C.locator('.lvjudge [data-a=lv-judge]').count()==1 and '이상' in await C.inner_text('body'))
    await C.fill(f'[id="lvj:{rid}-reason"]','반대팀이 연통제의 한계를 근거로 들며 찬성팀 주장에 직접 반박했어요.'); await C.click('[data-a=lv-judge]'); await W(C,800)
    ok('판정 제출 완료 표시', '제출 완료' in await C.inner_text('.lvjudge') and await C.locator('.lvjudge [data-a=lv-judge]').count()==0)
    rd=await C.evaluate(f'SB.rpc("debate_judge",{{p_room:"{rid}",p_c1:"con",p_c2:"con",p_c3:"con",p_reason:"한 번 더 해 볼게요 응"}})'); ok('중복 판정 서버 거절', rd['data']['reason']=='dup', str(rd))
    rr=await C.evaluate(f'SB.rpc("debate_result",{{p_room:"{rid}"}})'); ok('공개 전 학생은 판정 결과 못 봄', rr['data'] is None, str(rr))
    await W(T,900)
    ok('교사: 판정 제출 1/1 + 판정 현황', '1' in await T.inner_text('#lv-kpis') and '판정 제출' in await T.inner_text('#lv-kpis') and '청중 판정 현황' in await T.inner_text('.lvside'))
    await A.click('[data-a=lv-vote][data-v=pro]'); await W(A,600)
    # 결과 공개
    ok('교사 버튼: 투표 · 판정 마감 · 결과 공개', '판정' in await T.inner_text('[data-a=lv-state][data-v=result]'))
    await T.click('[data-a=lv-state][data-v=result]'); await W(T,500); await W(C,1300); await W(A,300)
    jt=await C.inner_text('.lvjury')
    ok('판정단 결과: 기준별 선택 수·전체·참여 인원', '역사적 근거의 타당성' in jt and '판정 1명' in jt and '더 많은 판정' in jt and '반대팀이 연통제' in jt, jt[:200])
    ok('정답 아님 안내', '정답이나 절대적인 승패' in jt)
    ok('최종 투표 결과와 판정 결과가 따로 표시', await C.locator('.lvcard:has(h3:has-text("최종 투표 결과"))').count()==1 and await C.locator('.lvcard:has(h3:has-text("청중 판정 결과"))').count()==1)
    ok('판정 이유는 익명(닉네임·실명 없음)', '박서준' not in jt and (await C.evaluate(ME()))['nick'] not in jt)
    await A.evaluate(f'liveResult(S.rooms.find(r=>r.id==="{rid}")).then(()=>liveRefresh(S.rooms.find(r=>r.id==="{rid}")))'); await W(A,500)
    ok('찬반 학생도 판정 결과를 봄', '반대팀이 연통제' in await A.inner_text('.lvjury'))
    ok('교사: 이유 가리기 버튼', await T.locator('[data-a=lv-jhide]').count()==1)
    await T.click('[data-a=lv-jhide]'); await W(T,500)
    await A.evaluate(f'liveResult(S.rooms.find(r=>r.id==="{rid}")).then(()=>liveRefresh(S.rooms.find(r=>r.id==="{rid}")))'); await W(A,500)
    ok('가린 의견은 학생 결과에서 사라짐(교사에겐 남음)', '반대팀이 연통제' not in await A.inner_text('.lvjury') and '반대팀이 연통제' in await T.inner_text('.lvside'))
    # 판정단 성찰·기록
    q=await C.inner_text('[id="lvref:%s-persuasive"]'%rid if False else '.lvcard:has([data-a=lv-ref-save])')
    ok('판정단 성찰 질문은 판정단용', '두 팀의 주장 중 가장 설득력' in q)
    await C.fill('[id="lvref:%s-before"]'%rid,'임시 정부의 성과가 크다고 생각했다.'); await C.fill('[id="lvref:%s-persuasive"]'%rid,'연통제의 한계에 대한 반박'); await C.fill('[id="lvref:%s-after"]'%rid,'성과와 한계를 함께 보게 됐다.')
    await C.check('input[name="lvref:%s-degree"][value=some]'%rid); await C.click('[data-a=lv-ref-save]'); await W(C,900)
    post=await C.evaluate(f'myPost(S.rooms.find(r=>r.id==="{rid}"))')
    ok('기록에 역할·판정·이유 저장', post['live']['team']=='jury' and post['live']['jury']['c2']=='con' and '연통제' in post['live']['jury']['reason'], str(post.get('live')))
    await W(T,900); rl=await T.inner_text('.lvrefs')
    ok('교사 성찰 목록에 판정단 표시·판정 내용', '청중 판정단' in rl and '반박의 적절성' in rl and '연통제의 한계' in rl)
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await T.screenshot(path='/tmp/claude-0/jury_teacher.png', full_page=True); await C.screenshot(path='/tmp/claude-0/jury_student.png', full_page=True)
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
