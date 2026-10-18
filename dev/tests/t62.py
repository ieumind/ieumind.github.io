# 가상 인물 대화 · AI 대화 지시문(프롬프트) 만들기
# 항목별 설정 → 생성(기본 틀 / Gemini) → 고치기 · 복사 · 다시 생성 · 적용 → 저장 → 수정 화면 복원 → 학생 대화에 지시문·차례가 전달되는지
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
HEADS=["1. 활동 개요","2. 가상 인물의 설정과 성격","3. 학생의 역할과 활동 목표","4. 대화 진행 규칙","5. 단계별 대화 진행 방식","6. 학생의 발언에 대한 대응 원칙","7. 학습 목표 달성 기준","8. 대화 종료 조건","9. 최종 피드백 및 결과 제시 방식","10. 교과 내용의 정확성을 위한 유의 사항"]
WIDE='''()=>{const W=document.documentElement.clientWidth; const out=[]; document.querySelectorAll("body *").forEach(e=>{const b=e.getBoundingClientRect(); if(b.right>W+1 && b.width>0 && getComputedStyle(e).position!=="fixed") out.push((e.id||e.className||e.tagName)+":"+Math.round(b.right))}); return [document.documentElement.scrollWidth, out.slice(0,6)]}'''
fails=[]
def ok(name, cond, extra=''):
  print(('PASS ' if cond else 'FAIL ')+name, extra)
  if not cond: fails.append(name)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.evaluate('navigator.clipboard.writeText = async t => { window.__copied = t }')
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=chat]'); await W(T)
    ok('지시문 칸과 두 방식 탭', await T.evaluate('!!document.querySelector("#pguide") && [...document.querySelectorAll("[data-a=pg-mode]")].map(x=>x.textContent).join("|")==="항목별 설정으로 만들기|직접 작성"'))
    ok('유형 카드 6개 + 설명', await T.evaluate('[...document.querySelectorAll("[data-a=pg-type]")].length===6 && document.querySelector("[data-a=pg-type] span").textContent.length>10'))
    ok('기본값: 횟수 8회 · 단계별 지원', await T.evaluate('document.getElementById("c-pgturns").value==="8" && document.getElementById("c-pgsup").value==="step"'))
    # 빈 입력
    await T.click('[data-a=pg-gen]'); await W(T)
    miss=await T.evaluate('S.pgen?.miss'); ok('빈 필수 항목 안내', miss==["활동 유형","교과","대상 학생","가상 인물 또는 역할","대화 상황","학생의 학습 목표"], str(miss))
    ok('빈 칸 표시(aria-invalid)', await T.evaluate('document.querySelectorAll("#pguide [aria-invalid=true]").length')>=6)
    ok('생성 결과 없음', await T.evaluate('!document.getElementById("c-pgout")'))
    # 입력
    await T.fill('#c-prompt','문을 열어야 할까, 닫아야 할까?')
    await T.click('[data-a=pg-type][data-v=persuade]'); await W(T)
    await T.select_option('#c-pgsubj','역사'); await W(T); await T.select_option('#c-pggrade','고등학교 2학년'); await W(T)
    await T.fill('#c-pgrole','1866년의 흥선대원군'); await T.fill('#c-pgsit','병인양요 직후, 서양과 통상할지 결정해야 하는 상황'); await T.fill('#c-pggoal','통상 수교 거부 정책의 배경과 한계를 설명할 수 있다')
    await T.select_option('#c-pgturns','5'); await W(T)
    await T.click('[data-a=pg-gen]'); await W(T,900)
    out=await T.input_value('#c-pgout')
    ok('기본 틀 생성: 10개 항목 모두', all(('['+h+']') in out for h in HEADS), str(len(out))+'자')
    ok('유형 규칙 반영(설득 단계·최종 결정·가상 결과)', all(x in out for x in ['설득 정도','최종 결정','가상의 결과','학생이 먼저 주장']))
    ok('입력값 반영(인물·상황·목표·5회·고2·단계별)', all(x in out for x in ['1866년의 흥선대원군','병인양요 직후','통상 수교 거부 정책','학생의 5번째 발언','고등학교 2학년','단계별 질문과 단서 제공']))
    ok('교과 유의 사항(역사)', '사료나 인물의 실제 발언' in out)
    sent=[x for x in await T.evaluate('__sbLog') if x.startswith('suggest:')]
    ok('Gemini 요청(op:guide)에 학생 정보 없이 항목·기본 틀만', len(sent)==1 and json.loads(sent[0][8:])['op']=='guide' and 'base' in json.loads(sent[0][8:]))
    ok('키 없음 → 기본 틀 + 안내', await T.evaluate('F("create").pgSrc')=='basic' and '기본 틀' in (await T.evaluate('document.getElementById("toast")?.textContent')))
    print('fn log:', [x for x in await T.evaluate('__sbLog') if x.startswith('fn:')]); ok('생성해도 대화는 시작되지 않음', not any(x.startswith('fn:chat:chat') for x in await T.evaluate('__sbLog')))
    # 다른 유형은 구조가 다르다
    other={}
    for k in ['negotiate','inquiry','expand','science','ethics']:
      other[k]=await T.evaluate(f'buildGuide({{...pgInput(F("create")), type:"{k}"}})')
    ok('유형마다 다른 지시문', len(set([out]+list(other.values())))==6)
    ok('협상: 성공·부분 성공·미성공 판정과 합의안', all(x in other['negotiate'] for x in ['성공:','부분 성공:','미성공:','합의안']))
    ok('개념 탐구: 정답 먼저 공개 금지·반례', '정답이나 완성된 정의를 먼저 말하지 않는다' in other['inquiry'] and '반례' in other['inquiry'])
    ok('답안 완성: 확인 단계·완성 답안', '(확인)' in other['expand'] and '— 완성 답안 —' in other['expand'] and '다른 주장으로 바꾸지 않는다' in other['expand'])
    ok('과학: 데이터 지어내지 않음·관찰/가설', '지어내지 않는다' in other['science'] and '관찰·가설·근거·결론' in other['science'])
    ok('윤리: 정답 강요 없음', '미리 정해진 답을 강요하지 않는다' in other['ethics'])
    # 고치기 → 다시 생성 보호
    await T.fill('#c-pgout', out+'\n- 선생님이 덧붙인 줄'); await T.click('[data-a=pg-gen][data-v=regen]'); await W(T)
    ok('고친 뒤 다시 생성은 한 번 더 확인', '한 번 더 누르면' in await T.evaluate('document.getElementById("toast")?.textContent') and (await T.input_value('#c-pgout')).endswith('덧붙인 줄'))
    await T.click('[data-a=pg-copy][data-v=out]'); await W(T)
    ok('프롬프트 복사(클립보드)', (await T.evaluate('window.__copied||""')).endswith('덧붙인 줄'))
    await T.click('[data-a=pg-gen][data-v=regen]'); await W(T,900)
    ok('두 번째 누름 → 입력값 유지한 채 다시 생성', not (await T.input_value('#c-pgout')).endswith('덧붙인 줄') and await T.input_value('#c-pgrole')=='1866년의 흥선대원군')
    # 적용
    await T.click('[data-a=pg-apply]'); await W(T)
    f=await T.evaluate('F("create")')
    ok('적용: 지시문·질문 수 5·대화 상대 채움', f['personaGuide']==f['pgOut'].strip() and f['maxTurns']=='5' and f['personaName']=='1866년의 흥선대원군', f.get('personaName'))
    ok('적용됨 표시', await T.evaluate('document.querySelector("[data-a=pg-apply]").disabled && document.querySelector(".pg-state").textContent.includes("적용되어 있어요")'))
    # 직접 작성 탭
    await T.click('[data-a=pg-mode][data-v=direct]'); await W(T)
    ok('직접 작성 탭에 적용된 지시문', (await T.input_value('#c-pguide'))==f['personaGuide'])
    await T.fill('#c-pguide','너는 흥선대원군이다. 선생님이 직접 쓴 지시문.'); await W(T)
    await T.click('[data-a=pg-mode][data-v=gen]'); await W(T)
    # Gemini 연결
    await T.evaluate('localStorage.setItem("__aikey","AIzaTESTKEY_abcdefghijklmnopqrstu")')
    await T.click('[data-a=pg-gen]'); await W(T,900)
    ai=await T.input_value('#c-pgout')
    ok('Gemini로 다듬은 지시문', ai.startswith('(Gemini 다듬음') and await T.evaluate('F("create").pgSrc')=='ai' and 'Gemini가 다듬은' in await T.evaluate('document.querySelector(".pg-out label").textContent'))
    ok('직접 쓴 지시문은 생성만으로 안 바뀜', await T.evaluate('F("create").personaGuide')=='너는 흥선대원군이다. 선생님이 직접 쓴 지시문.')
    await T.click('[data-a=pg-apply]'); await W(T)
    ok('직접 쓴 지시문 덮어쓰기 전 확인', await T.evaluate('F("create").personaGuide')=='너는 흥선대원군이다. 선생님이 직접 쓴 지시문.' and '한 번 더' in await T.evaluate('document.getElementById("toast")?.textContent'))
    await T.click('[data-a=pg-apply]'); await W(T)
    ok('두 번째 누름에 적용', (await T.evaluate('F("create").personaGuide')).startswith('(Gemini 다듬음'))
    for mode,want in [('bad','열 가지'),('err','답하지 못해')]:
      await T.evaluate(f'localStorage.setItem("__guidemode","{mode}")'); await T.evaluate('F("create").pgLast = F("create").pgOut')
      await T.click('[data-a=pg-gen][data-v=regen]'); await W(T,900)
      ok(f'Gemini {mode} → 기본 틀로 대신', await T.evaluate('F("create").pgSrc')=='basic' and want in await T.evaluate('document.getElementById("toast")?.textContent'), await T.evaluate('document.getElementById("toast")?.textContent'))
    await T.evaluate('localStorage.removeItem("__guidemode")')
    await T.screenshot(path='/tmp/claude-0/smoke/pguide_desk.png', full_page=True)
    # 저장
    await T.click('[data-a=create-save]'); await W(T,900)
    rid=await T.evaluate('S.roomId'); room=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs']['rooms/'+rid]['data']
    per=room['persona']
    ok('저장: persona.guide · gen · maxTurns', per.get('guide','').startswith('(Gemini 다듬음') and per['gen']['type']=='persuade' and per['gen']['turns']==5 and per['maxTurns']==5, str({k:(v if k!='guide' else v[:20]) for k,v in per.items()}))
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,500)
    ok('수정 화면에서 항목·지시문 복원', await T.evaluate('document.querySelector("[data-a=pg-type][data-v=persuade]").getAttribute("aria-pressed")==="true" && document.getElementById("c-pgrole").value==="1866년의 흥선대원군" && document.getElementById("c-pgturns").value==="5" && F("create").personaGuide.startsWith("(Gemini")'))
    await T.click('[data-a=pg-mode][data-v=direct]'); await W(T); await T.fill('#c-pguide','가'*6001); await W(T)
    await T.click('[data-a=create-save]'); await W(T,500)
    ok('6,000자 넘으면 저장 막음', '너무 길어요' in await T.evaluate('document.getElementById("toast")?.textContent') and await T.evaluate('S.view')=='create')
    await T.fill('#c-pguide', per['guide']); await W(T)
    # 예전 방식 활동: guide·gen 없음
    await T.evaluate('dropForm("create"); S.view="home"; render()'); await W(T)
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=chat]'); await W(T)
    await T.fill('#c-prompt','해방 직후 새 나라'); await T.fill('#c-pname','여운형'); await T.click('[data-a=create-save]'); await W(T,900)
    r0=await T.evaluate('S.roomId'); p0=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs']['rooms/'+r0]['data']['persona']
    ok('지시문 안 쓴 활동은 예전 모양 그대로', 'guide' not in p0 and 'gen' not in p0, str(p0))
    # 학생(과목 없는 활동 · 이름만) 대화
    G=await c.new_page(); G.on('pageerror',lambda e:errs.append('G:'+str(e)))
    await G.goto(U+'?who=anon#'+rid); await W(G,900); await G.fill('#g-nick','지우'); await G.click('[data-a=guest-join]'); await W(G,1500)
    if await G.query_selector('[data-a=to-stage]'): await G.click('[data-a=to-stage]'); await W(G,400)
    ok('학생 화면: 질문 0 / 5', '질문 0 / 5' in await G.evaluate('document.querySelector(".chatcard .foot")?.textContent||""'))
    ok('학생 화면에 지시문 안 보임', '대화 진행 규칙' not in await G.evaluate('document.body.innerText'))
    await G.fill(f'[id="chat:{rid}-msg"]','통상을 하셔야 합니다.'); await G.click('[data-a=chat-send]'); await W(G,900)
    ok('첫 발언: turn 1 전달', await G.evaluate('window.__lastChat?.turn')==1)
    await G.fill(f'[id="chat:{rid}-msg"]','서양 무기가 더 강합니다.'); await G.click('[data-a=chat-send]'); await W(G,900)
    ok('두 번째 발언: turn 2', await G.evaluate('window.__lastChat?.turn')==2 and '질문 2 / 5' in await G.evaluate('document.querySelector(".chatcard .foot")?.textContent||""'))
    # 휴대폰
    M=await c.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,700); await M.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(M,600)
    await M.evaluate('F("create").pgMode="gen"; render()'); await W(M,300)
    r1=await M.evaluate(WIDE); await M.evaluate('document.getElementById("pguide").scrollIntoView()'); await M.screenshot(path='/tmp/claude-0/smoke/mob/pguide_gen.png')
    await M.evaluate('F("create").pgMode="direct"; render()'); await W(M,300); r2=await M.evaluate(WIDE)
    await M.evaluate('document.getElementById("pguide").scrollIntoView()'); await M.screenshot(path='/tmp/claude-0/smoke/mob/pguide_direct.png')
    ok('휴대폰 390: 가로 넘침 없음', r1[0]<=390 and r2[0]<=390, str(r1)+str(r2))
    print('errors', errs); ok('페이지 오류 없음', not errs)
    print('FAILS', fails); await b.close()
asyncio.run(main())
