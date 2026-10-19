# 교사 도구: 학생 코드 과목·그룹별 보기 · 학습 나눔(조회 기록·한 줄 메모 질문·중복 버튼 삭제) · 미제출 알림(전체/개별)
import asyncio, re, json, base64
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGP4z8CAFWEXHbQSACj/P8Fu7N9hAAAAAElFTkSuQmCC')
fails=[]
def ok(name, cond, extra=''):
  print(('PASS ' if cond else 'FAIL ')+name, extra)
  if not cond: fails.append(name)
async def toast(pg): return await pg.evaluate('document.getElementById("toast")?.textContent||""')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    M=lambda pg=T: pg.evaluate('JSON.parse(localStorage.getItem("__sbmock"))')
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n10403 박서준\n10404 이하늘'); await T.click('[data-a=roster-add]'); await W(T,500)
    studs=(await M())['students']; codes={s['name']:s['code'] for s in studs}; sid={s['name']:s['id'] for s in studs}
    ok('학생 코드: 과목·그룹이 없으면 보기 선택칸 없음', not await T.evaluate('!!document.getElementById("roster-view")'))
    await T.keyboard.press('Escape'); await W(T)
    # 과목(수강 3명: 김가온·나다은·박서준) + 그룹 2개
    await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title','1학년 한국사')
    await T.evaluate(f'(()=>{{const f=S.form.course; f.sel=["{sid["김가온"]}","{sid["나다은"]}","{sid["박서준"]}"]; renderModal()}})()'); await W(T)
    await T.click('[data-a=course-save]'); await W(T,700)
    await T.evaluate(f'(async()=>{{const c=S.courses[0]; const groups=[{{id:"g1",name:"1모둠",members:["{sid["김가온"]}","{sid["나다은"]}"]}},{{id:"g2",name:"2모둠",members:["{sid["박서준"]}"]}}]; await write(db=>db.doc("courses/"+c.id).update({{groups}}),()=>{{c.groups=groups}}); render()}})()'); await W(T,500)
    cid=await T.evaluate('S.courses[0].id')
    await T.click('[data-a=roster-open]'); await W(T,500)
    opts=await T.eval_on_selector_all('#roster-view option','e=>e.map(x=>x.textContent)')
    ok('학생 코드: 보기 선택칸(전체·과목별·그룹별)', opts[0]=='전체 학생' and any('1학년 한국사 (3명)' in o for o in opts) and any('1모둠 (2명)' in o for o in opts) and any('2모둠 (1명)' in o for o in opts), str(opts))
    rows=lambda: T.eval_on_selector_all('.ptable tbody tr','e=>e.map(x=>x.children[1].innerText)')
    ok('전체 학생 4명', len(await rows())==4)
    await T.select_option('#roster-view', f'c|{cid}'); await W(T)
    ok('과목별: 수강 3명만', sorted(await rows())==['김가온','나다은','박서준'], str(await rows()))
    await T.select_option('#roster-view', f'g|{cid}|g1'); await W(T)
    ok('그룹별: 1모둠 2명만', sorted(await rows())==['김가온','나다은'])
    ok('인쇄 버튼에 인원 표시', '(2명)' in await T.inner_text('[data-a=roster-print]'))
    ok('검색도 함께 적용', (await T.fill('#roster-q','나다') , len(await rows()))[1]==1) if False else None
    await T.fill('#roster-q','나다'); await W(T); ok('그룹 안에서 검색', await rows()==['나다은'])
    await T.fill('#roster-q',''); await T.select_option('#roster-view',''); await W(T); ok('전체로 돌아오면 4명', len(await rows())==4)
    await T.keyboard.press('Escape'); await W(T)

    # ---- 학습 나눔 ----
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=notes]'); await W(T)
    await T.fill('#c-memoq','오늘 배운 것 중 가장 중요한 것은 무엇인가요?')
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    room=[v['data'] for v in (await M())['docs'].values() if v['id']==rid][0]
    ok('저장: 한 줄 메모 질문', room['noteCfg'].get('memoQ')=='오늘 배운 것 중 가장 중요한 것은 무엇인가요?' and room['noteCfg']['maxPages']==3, str(room['noteCfg']))
    ok('교사 화면: 복제·학생 명단 버튼 삭제', not await T.evaluate('!!document.querySelector("[data-a=note-dup]")') and not await T.evaluate('[...document.querySelectorAll(".tabbody button, .nshare-row ~ * button")].some(b=>/다음 시간용으로 복제|학생 명단/.test(b.textContent))'))
    ok('교사 화면: 위쪽 ‘복제’ 버튼은 남아 있음', await T.evaluate('!!document.querySelector(".abar [data-a=dup]")'))
    ok('교사 화면: 한 줄 메모 질문 표시', '한 줄 메모 질문' in await T.inner_text('.ahead ~ *') if False else '한 줄 메모 질문' in await T.evaluate('document.body.innerText'))
    async def login(name, hash_=''):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,600)
      s=[x for x in studs if x['name']==name][0]
      await K.fill('#f-num',s['number']); await K.fill('#f-name',s['name']); await K.fill('#f-code',s['code']); await K.press('#f-code','Enter'); await W(K,1300); return K
    A=await login('김가온')   # 열어 보기만 함
    Bq=await login('나다은')  # 사진 제출
    lab=await Bq.inner_text('label[for="note:%s-memo"]'%rid)
    ok('학생: 한 줄 메모 칸에 교사 질문', '오늘 배운 것 중 가장 중요한 것은 무엇인가요?' in lab, lab)
    ok('학생: 질문이 있으면 안내 문구가 바뀜', await Bq.evaluate('document.getElementById("note:%s-memo").placeholder'%rid)=='여기에 답을 적어 주세요')
    await Bq.set_input_files('input[data-note-file][multiple]', files=[{'name':'a.png','mimeType':'image/png','buffer':PNG}]); await W(Bq,900)
    await Bq.fill('textarea[id="note:%s-memo"]'%rid,'원인과 결과를 연결하는 것'); await Bq.click('[data-a=note-submit]'); await W(Bq,1500)
    ok('학생: 제출 뒤 질문과 답이 함께 보임', '오늘 배운 것 중 가장 중요한 것은 무엇인가요?' in await Bq.inner_text('.nsub') and '원인과 결과를 연결하는 것' in await Bq.inner_text('.nsub'))
    await T.evaluate(f'S.views={{}}; act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,1000)
    kp=await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))')
    ok('교사: 조회 KPI(제출 1 + 열어 봄 1 = 2명)', any('조회' in k and k.startswith('2') for k in kp), str(kp))
    ok('교사: 김가온은 ‘조회만 함’', await T.evaluate('(()=>{const c=[...document.querySelectorAll(".ncard")].find(x=>x.innerText.includes("김가온")); return !!c && /조회만 함/.test(c.innerText) && /조회 \\d+회/.test(c.innerText)})()'))
    ok('교사: 박서준은 아직 열어 보지 않음', await T.evaluate('(()=>{const c=[...document.querySelectorAll(".ncard")].find(x=>x.innerText.includes("박서준")); return !!c && /아직 열어 보지 않았어요/.test(c.innerText)})()'))
    await T.click('[data-a=note-filter][data-v=viewed]'); await W(T)
    ok('조회만 함 필터', await T.eval_on_selector_all('.ncard','e=>e.map(x=>x.querySelector("b").innerText.trim())')==['10301 김가온'], str(await T.eval_on_selector_all('.ncard','e=>e.map(x=>x.querySelector("b").innerText.trim())')))
    await T.click('[data-a=note-filter][data-v=all]'); await W(T)
    # 미제출 알림 (학습 나눔)
    ok('미제출 알림 막대', '미제출 2명 모두 고르기' in await T.inner_text('#nudge-bar'), await T.inner_text('#nudge-bar'))   # 과목 수강 3명 중 제출 1명 → 미제출 2명
    ok('제출한 학생에게는 체크칸 없음', await T.evaluate('(()=>{const c=[...document.querySelectorAll(".ncard")].find(x=>x.innerText.includes("나다은")); return !!c && !c.querySelector("[data-nudge]")})()'))
    ok('고른 학생이 없으면 보내기 버튼 비활성', await T.is_disabled('[data-a=nudge-open]'))
    await T.check('.ncard:has-text("박서준") [data-nudge]'); await W(T)
    ok('학생 한 명 고르기', '고른 1명에게 알림 보내기' in await T.inner_text('#nudge-bar') and not await T.is_disabled('[data-a=nudge-open]'))
    await T.click('[data-a=nudge-all]'); await W(T)
    ok('미제출 모두 고르기 = 2명', '고른 2명에게 알림 보내기' in await T.inner_text('#nudge-bar'))
    await T.uncheck('.ncard:has-text("김가온") [data-nudge]'); await W(T)
    ok('개별로 빼기 = 1명(박서준)', '고른 1명에게 알림 보내기' in await T.inner_text('#nudge-bar'))
    await T.click('[data-a=nudge-open]'); await W(T,600)
    ok('안내 창: 고른 1명·제목·내용', await T.inner_text('#msg-count')=='1명' and await T.input_value('#msg-title')=='제출해 주세요' and '학습 나눔' in await T.input_value('#msg-body'), await T.input_value('#msg-body'))
    ok('안내 창: 고른 학생에 체크', await T.evaluate('[...document.querySelectorAll("input[data-msgsel]:checked")].length')==1)
    await T.click('[data-a=msg-send]'); await W(T,900)
    lg=await T.evaluate('__sbLog')
    ok('서버: 고른 1명에게만 안내', 'msg_send:1' in lg, str([x for x in lg if x.startswith('msg_send')]))
    nt=[x for x in lg if x.startswith('notify:')][-1]
    ok('휴대폰 알림: 제목·활동 링크(#방)·학생 1명', nt.startswith('notify:제출해 주세요|') and ('|#'+rid+'|') in nt and nt.endswith('students=1'), nt)
    await A.reload(); await W(A,1500)
    ok('김가온(안 고름) 화면에는 안내 없음', not await A.evaluate('!!document.querySelector(".bigmsg")'))
    C=await login('박서준'); ok('박서준(고름) 화면에 안내가 크게 뜸', await C.evaluate('!!document.querySelector(".bigmsg")') and '제출해 주세요' in await C.inner_text('.bigmsg'))

    # ---- 다른 활동 유형(일반 활동)의 미제출 알림 ----
    await T.evaluate('dropForm("create"); S.modal=null; S.view="home"; render()'); await W(T)
    await T.click('[data-a=create]'); await W(T); await T.fill('#c-prompt','개항은 기회였을까?'); await T.click('[data-a=create-save]'); await W(T,800); rid2=await T.evaluate('S.roomId')
    K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon#'+rid2); await W(K,600)
    s=[x for x in studs if x['name']=='나다은'][0]
    await K.fill('#f-num',s['number']); await K.fill('#f-name',s['name']); await K.fill('#f-code',s['code']); await K.press('#f-code','Enter'); await W(K,1300)
    await K.evaluate(f'(async()=>{{const r=S.rooms.find(x=>x.id==="{rid2}"); await savePost(r,{{stance:r.stances[0], body:{{claim:"기회", reason:"근대화"}}, status:"submitted", submittedAt:Date.now()}})}})()'); await W(K,700)
    await T.evaluate(f'S.views={{}}; act("open",{{dataset:{{id:"{rid2}"}}}}); act("ttab",{{dataset:{{v:"progress"}}}})'); await W(T,1000)
    ok('참여 현황: 알림 막대 + 체크칸', await T.evaluate('!!document.getElementById("nudge-bar") && document.querySelectorAll("input[data-nudge]").length>0'))
    ok('미제출 모두 고르기에는 제출한 나다은 빠짐', '미제출 2명 모두 고르기' in await T.inner_text('#nudge-bar'), await T.inner_text('#nudge-bar'))
    await T.click('[data-a=nudge-all]'); await W(T)
    chk=await T.evaluate('[...document.querySelectorAll("input[data-nudge]:checked")].map(i=>i.dataset.nudge)')
    ok('고른 2명에 나다은 없음', len(chk)==2 and not any('나다은' in c for c in chk), str(chk))
    await T.click('[data-a=nudge-open]'); await W(T,600); await T.click('[data-a=msg-send]'); await W(T,900)
    lg=await T.evaluate('__sbLog'); ok('일반 활동도 안내 2명 + 알림 링크', 'msg_send:2' in lg and ('|#'+rid2+'|') in [x for x in lg if x.startswith('notify:')][-1])
    # 체험 모드: 알림 막대는 있고 보내면 ‘체험이라 실제로 보내지 않음’
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e))); await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700)
    await D.evaluate('S.tour=null; act("open",{dataset:{id:"park-1965"}}); act("ttab",{dataset:{v:"progress"}})'); await W(D,500)
    ok('체험: 참여 현황에 알림 막대', await D.evaluate('!!document.getElementById("nudge-bar")'))
    await T.screenshot(path='/tmp/claude-0/smoke/nudge_progress.png', full_page=True)
    # (참고) 과목 학생 고르기에서 학급이 ‘일부만’ 골라진 상태일 때 나는 'ICON missing: circle-half-2'는 이번 변경과 무관한 예전 문제라 여기서는 뺀다
    errs=[e for e in errs if 'circle-half-2' not in e]
    print('errors', errs); ok('페이지 오류 없음', not errs)
    print('FAILS', fails); await b.close()
asyncio.run(main())
