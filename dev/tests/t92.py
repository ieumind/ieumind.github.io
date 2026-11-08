# ⚖️ 대기실·역할 이동(팀당 N명)·직접 닉네임·교사 지정·판정단 의견 최소 개수·판정=최종 투표·가리기·성찰 기록 / 판정단 없는 토론은 토론자가 투표
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
    async def mk(opts):
      await T.evaluate('act("home")'); await W(T,300)
      await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=tpl][data-v=live]'); await W(T,300)
      for k,v in opts.items(): await T.select_option(k,v)
      await T.fill('#c-prompt','대한민국 임시 정부는 독립운동에 큰 성과를 거두었다.'); await T.click('[data-a=create-save]'); await W(T,900); return await T.evaluate('S.roomId')
    rid=await mk({'#c-nick':'custom','#c-teamn':'2','#c-notemin':'2'})
    rm=await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}")')
    ok('설정 저장: 직접 닉네임·팀당 2명·의견 2개', rm['liveCfg']['nickMode']=='custom' and rm['liveCfg']['teamN']==2 and rm['liveCfg']['noteMin']==2, str(rm['liveCfg']))
    ME=f'lv(S.rooms.find(r=>r.id==="{rid}")).me'
    async def stu(nm, r=None):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(nm+':'+str(e))); await K.goto(U+'?who=anon#'+(r or rid)); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1600); return K
    A=await stu('김가온'); B=await stu('나다은'); C=await stu('박서준'); D=await stu('이하린'); E=await stu('최서아')
    # 직접 닉네임
    ok('직접 닉네임 방식: 대기실에 닉네임 입력칸', await A.locator('#lv-nick').count()==1)
    await A.fill('#lv-nick','역사탐험가'); await A.click('[data-a=lv-nick-save]'); await W(A,700)
    ok('닉네임 저장', (await A.evaluate(ME))['nick']=='역사탐험가' and '역사탐험가' in await A.inner_text('.lvme'))
    q=lambda P,n: P.evaluate(f'SB.rpc("debate_nick",{{p_room:"{rid}",p_nick:{n!r}}})')
    ok('중복 닉네임 거절', (await q(B,'역사탐험가'))['data']['reason']=='dup')
    ok('역할 이름 흉내(찬성01) 거절', (await q(B,'찬성01'))['data']['reason']=='reserved')
    ok('실제 이름 거절', (await q(B,'김가온'))['data']['reason']=='real')
    ok('너무 짧은 닉네임 거절', (await q(B,'가'))['data']['reason']=='bad' and (await q(B,'가나다라마바사아자'))['data']['reason']=='bad')
    await B.fill('#lv-nick','역사탐험가'); await B.click('[data-a=lv-nick-save]'); await W(B,500); ok('화면에서도 중복 안내', '이미 다른 친구' in await B.inner_text('body'))
    # 팀당 N명
    await A.click('.lvrole.pro'); await W(A,700); await B.click('.lvrole.pro'); await W(B,700)
    ok('직접 정한 닉네임은 역할을 옮겨도 유지', (await A.evaluate(ME))['nick']=='역사탐험가' and (await B.evaluate(ME))['nick']=='찬성01', f"{await A.evaluate(ME)} {await B.evaluate(ME)}")
    await W(C,3600)
    ok('찬성이 가득 차면(2/2) 버튼 비활성', await C.locator('.lvrole.pro').is_disabled() and '2 / 2' in await C.inner_text('.lvrole.pro'))
    rf=await C.evaluate(f'SB.rpc("debate_move",{{p_room:"{rid}",p_team:"pro"}})'); ok('서버도 인원 초과 거절(full)', rf['data']['reason']=='full', str(rf))
    # 교사 지정 + 닉네임 되돌리기
    await W(T,900)
    ks=await T.evaluate(f'[...lv(S.rooms.find(r=>r.id==="{rid}")).members.values()].map(m=>[m.mkey,m.real_name])'); mk_={n:k for k,n in ks}
    await T.click(f'[data-a=lv-team][data-k="{mk_["이하린"]}"][data-v=con]'); await W(T,500); await W(D,1000)
    nd=await D.evaluate(ME); ok('교사가 직접 지정 → 반대01로 닉네임 새로 부여', nd['team']=='con' and nd['nick']=='반대01', str(nd))
    ok('직접 닉네임 학생에게만 되돌리기 버튼', await T.locator(f'[data-a=lv-nick-reset][data-k="{mk_["김가온"]}"]').count()==1 and await T.locator('[data-a=lv-nick-reset]').count()==1)
    await T.click(f'[data-a=lv-nick-reset][data-k="{mk_["김가온"]}"]'); await W(T,500); await W(A,1000)
    ok('교사가 되돌리면 자동 닉네임(찬성02)', (await A.evaluate(ME))['nick']=='찬성02', str(await A.evaluate(ME)))
    # 시작
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,500); await W(A,1000); await W(C,800)
    rm_=await A.evaluate(f'SB.rpc("debate_move",{{p_room:"{rid}",p_team:"jury"}})'); ok('시작 뒤 학생 이동 서버 거절(locked)', rm_['data']['reason']=='locked', str(rm_))
    ok('시작 뒤 닉네임 변경 거절(locked)', (await q(C,'새이름'))['data']['reason']=='locked')
    # 청중 의견 최소 2개
    nj=await C.evaluate(ME); ok('나머지 학생은 판정단(박서준·최서아)', nj['team']=='jury' and (await E.evaluate(ME))['team']=='jury')
    await C.fill('#lv-note','첫 번째 의견'); await C.click('[data-a=lv-note-send]'); await W(C,700)
    await T.click('[data-a=lv-state][data-v=ended]'); await W(T,400); await T.click('[data-a=lv-state][data-v=vote]'); await W(T,400); await W(C,1000); await W(E,500)
    ok('의견 최소 개수 안내(1/2)', '의견 1개' in await C.inner_text('.lvjudge') and '2개 이상' in await C.inner_text('.lvjudge'))
    jr=lambda P: P.evaluate(f'SB.rpc("debate_judge",{{p_room:"{rid}",p_c1:"pro",p_c2:"con",p_c3:"con",p_c4:"con",p_reason:"반대팀이 한계를 근거로 반박했어요."}})')
    ok('의견 부족하면 서버가 판정 거절(notes)', (await jr(C))['data']['reason']=='notes' and (await jr(E))['data']['reason']=='notes')
    for k,v in [('c1','pro'),('c2','con'),('c3','con'),('c4','con')]: await C.check(f'input[name="lvj:{rid}-{k}"][value={v}]')
    await C.fill(f'[id="lvj:{rid}-reason"]','반대팀이 한계를 근거로 직접 반박했어요.'); await C.click('[data-a=lv-judge]'); await W(C,500)
    ok('화면에서도 막힘·의견 쓰러 가기', '먼저 남겨' in await C.inner_text('body') and await C.locator('#lv-note').count()==1)
    await C.wait_for_timeout(2600); await C.fill('#lv-note','두 번째 의견이에요.'); await C.click('[data-a=lv-note-send]'); await W(C,800)
    for k,v in [('c1','pro'),('c2','con'),('c3','con'),('c4','con')]: await C.check(f'input[name="lvj:{rid}-{k}"][value={v}]')
    await C.fill(f'[id="lvj:{rid}-reason"]','반대팀이 한계를 근거로 직접 반박했어요.'); await C.click('[data-a=lv-judge]'); await W(C,900)
    ok('의견 2개를 쓰면 판정 제출됨', '제출 완료' in await C.inner_text('.lvjudge'))
    ok('종합(최종 투표) 선택도 함께 표시', '종합' in await C.inner_text('.lvjudge'))
    ok('중복 판정 서버 거절', (await jr(C))['data']['reason']=='dup')
    await W(T,900)
    ok('교사: 판정 제출 1/2(판정단 2명)', '판정 제출' in await T.inner_text('#lv-kpis') and '1' in await T.inner_text('#lv-kpis'))
    await T.click('[data-a=lv-state][data-v=result]'); await W(T,500); await W(C,1300); await W(A,300)
    jt=await C.inner_text('.lvjury'); ok('판정 결과(기준별·전체·익명 이유)', '역사적 근거의 타당성' in jt and '판정 1명' in jt and '반대팀이 한계를' in jt and '박서준' not in jt)
    ok('최종 투표 결과 = 판정단 종합(반대 100%)', '100%' in await C.inner_text('.lvres'))
    await A.evaluate(f'liveResult(S.rooms.find(r=>r.id==="{rid}")).then(()=>liveRefresh(S.rooms.find(r=>r.id==="{rid}")))'); await W(A,500)
    await T.click('[data-a=lv-jhide]'); await W(T,500)
    await A.evaluate(f'liveResult(S.rooms.find(r=>r.id==="{rid}")).then(()=>liveRefresh(S.rooms.find(r=>r.id==="{rid}")))'); await W(A,500)
    ok('가린 의견은 학생 결과에서 사라짐(교사에겐 남음)', '반대팀이 한계를' not in await A.inner_text('.lvjury') and '반대팀이 한계를' in await T.inner_text('.lvside'))
    # 판정단 성찰·기록
    q3=await C.inner_text('.lvcard:has([data-a=lv-ref-save])'); ok('판정단 성찰 질문은 판정단용', '두 팀의 주장 중 가장 설득력' in q3)
    await C.fill('[id="lvref:%s-before"]'%rid,'임시 정부의 성과가 크다고 생각했다.'); await C.fill('[id="lvref:%s-persuasive"]'%rid,'연통제의 한계에 대한 반박'); await C.fill('[id="lvref:%s-after"]'%rid,'성과와 한계를 함께 보게 됐다.')
    await C.check('input[name="lvref:%s-degree"][value=some]'%rid); await C.click('[data-a=lv-ref-save]'); await W(C,900)
    post=await C.evaluate(f'myPost(S.rooms.find(r=>r.id==="{rid}"))')
    ok('기록에 역할·판정(종합 포함)·이유 저장', post['live']['team']=='jury' and post['live']['jury']['c4']=='con' and post['live']['vote']=='con' and '한계' in post['live']['jury']['reason'], str(post.get('live')))
    await W(T,900); rl=await T.inner_text('.lvrefs'); ok('교사 성찰 목록에 판정단·판정 내용', '청중 판정단' in rl and '종합' in rl and '연통제의 한계' in rl)
    # 판정단이 없는 토론: 토론자가 직접 최종 투표
    r2=await mk({'#c-teamn':'2'})
    P=await stu('김가온', r2); Q=await stu('나다은', r2)
    await P.click('.lvrole.pro'); await W(P,700); await Q.click('.lvrole.con'); await W(Q,700); await W(T,900)
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,500); await T.click('[data-a=lv-state][data-v=ended]'); await W(T,400); await T.click('[data-a=lv-state][data-v=vote]'); await W(T,400); await W(P,1100)
    ok('판정단이 없으면 토론자에게 투표 버튼', await P.locator('[data-a=lv-vote]').count()==2 and await P.locator('.lvjudge').count()==0)
    await P.click('[data-a=lv-vote][data-v=pro]'); await W(P,700); await Q.click('[data-a=lv-vote][data-v=con]'); await W(Q,700)
    ok('토론자 투표 완료', '투표했어요' in await P.inner_text('.lvvote'))
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await T.screenshot(path='/tmp/claude-0/jury_teacher.png', full_page=True); await C.screenshot(path='/tmp/claude-0/jury_student.png', full_page=True)
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
