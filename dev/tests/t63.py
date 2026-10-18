# 가상 인물 대화 · 캐릭터 설정 / AI 프롬프트 / 최대 대화 횟수로 다시 짠 만들기 화면 + 학생 대화 화면
# (t60 ‘AI용 인물 자료’ 칸, t62 ‘AI 대화 지시문’ 칸 테스트를 대신한다)
import asyncio, re, json, base64
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
HEADS=["1. 활동 개요","2. 가상 인물의 설정과 성격","3. 학생의 역할과 활동 목표","4. 대화 진행 규칙","5. 단계별 대화 진행 방식","6. 학생의 발언에 대한 대응 원칙","7. 학습 목표 달성 기준","8. 대화 종료 조건","9. 최종 피드백 및 결과 제시 방식","10. 교과 내용의 정확성을 위한 유의 사항"]
WIDE='''()=>{const W=document.documentElement.clientWidth; const out=[]; document.querySelectorAll("body *").forEach(e=>{const b=e.getBoundingClientRect(); if(b.right>W+1 && b.width>0 && getComputedStyle(e).position!=="fixed") out.push((e.id||e.className||e.tagName)+":"+Math.round(b.right))}); return [document.documentElement.scrollWidth, out.slice(0,6)]}'''
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGP4z8CAFWEXHbQSACj/P8Fu7N9hAAAAAElFTkSuQmCC')
fails=[]
def ok(name, cond, extra=''):
  print(('PASS ' if cond else 'FAIL ')+name, extra)
  if not cond: fails.append(name)
async def toast(pg): return await pg.evaluate('document.getElementById("toast")?.textContent||""')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.evaluate('navigator.clipboard.writeText = async t => { window.__copied = t }')
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=chat]'); await W(T)
    heads=await T.eval_on_selector_all('.card h3','e=>e.map(x=>x.textContent.replace(/\\s+/g," ").trim())')
    i1=[i for i,h in enumerate(heads) if '캐릭터 설정' in h]; i2=[i for i,h in enumerate(heads) if '무엇에 대해 대화할까요' in h]; i3=[i for i,h in enumerate(heads) if 'AI 프롬프트' in h]
    ok('세 덩어리 순서: 캐릭터 → 대화 주제·자료 → AI 프롬프트', bool(i1 and i2 and i3) and i1[0] < i2[0] < i3[0], str(heads[:8]))
    ok('보임/안 보임 표시', '학생에게 보여요' in heads[i1[0]] and '학생에게 보이지 않아요' in heads[i3[0]])
    ok('겹치던 칸 없음(말투·AI용 인물 자료·지시문 안 인물/상황/횟수)', not await T.evaluate('!!document.querySelector("#c-pstyle,#c-pfacts,#c-pgrole,#c-pgsit,#c-pgturns,[data-a=ai-persona]")'))
    ok('캐릭터 칸: 이미지·이름·소개·학생 역할·부르는 말·시작 메시지·추천 질문·최대 대화 횟수', await T.evaluate('["c-pname","c-pabout","c-puser","c-pcall","c-pgreet","c-pstart","c-pmax"].every(id=>document.getElementById(id)) && !!document.querySelector("[data-avatar-file]")'))
    # 활동 유형 4가지(비슷한 유형 통폐합) · 최대 대화 횟수 3·5·8·10, 기본 5
    ok('활동 유형 4가지', await T.eval_on_selector_all('[data-a=pg-type]','e=>e.map(x=>x.dataset.v)')==['persuade','inquiry','ethics','expand'])
    ok('최대 대화 횟수: 3·5·8·10회 중 선택, 기본 5회', await T.evaluate('(()=>{const e=document.getElementById("c-pmax"); return e.tagName==="SELECT" && [...e.options].map(o=>o.value).join()==="3,5,8,10" && e.value==="5"})()'))
    # 이미지 올리기 (Supabase 흉내: materials 보관함)
    await T.set_input_files('[data-avatar-file]', files=[{'name':'a.png','mimeType':'image/png','buffer':PNG}]); await W(T,900)
    img=await T.evaluate('F("create").personaImg||""'); ok('캐릭터 이미지 올림', bool(img) and await T.evaluate('!!document.querySelector(".cimg img.cav")'), img[:60])
    # 빈 입력으로 생성
    await T.click('[data-a=pg-gen]'); await W(T)
    miss=await T.evaluate('S.pgen?.miss'); ok('빈 필수 항목 안내', miss==["캐릭터 이름","대화 주제","활동 유형","교과","대상 학생","학생의 학습 목표"], str(miss))
    await T.fill('#c-pname','고종'); await T.fill('#c-pabout','조선의 26대 왕. 개항과 개화 사이에서 고민한다.')
    await T.fill('#c-prompt','<1> 고종에게 위정척사파의 핵심 주장을 요약하여 보고하세요.\n<2> 세력을 하나 골라 고종을 설득하세요.')
    await T.select_option('#c-pmax','5'); await T.fill('#c-puser','개화파 젊은 관리')
    await T.click('[data-a=pg-type][data-v=persuade]'); await W(T)
    await T.select_option('#c-pgsubj','역사'); await W(T); await T.select_option('#c-pggrade','고등학교 1학년'); await W(T)
    await T.fill('#c-pggoal','위정척사·개화의 논리를 당시 상황에 근거해 설명할 수 있다')
    await T.click('[data-a=pg-gen]'); await W(T,900)
    out=await T.input_value('#c-pgout')
    ok('기본 틀: 10개 항목', all(('['+h+']') in out for h in HEADS), str(len(out))+'자')
    bad=[]
    for ty in ['persuade','inquiry','ethics','expand']:
      await T.click(f'[data-a=pg-type][data-v={ty}]'); await W(T); await T.click('[data-a=pg-gen]'); await W(T,500)
      o=await T.input_value('#c-pgout')
      if not all(('['+h+']') in o for h in HEADS) or 'undefined' in o: bad.append(ty)
    ok('4가지 유형 모두 10개 항목 기본 틀', not bad, str(bad))
    await T.click('[data-a=pg-type][data-v=persuade]'); await W(T); await T.click('[data-a=pg-gen]'); await W(T,500)
    ok('위의 캐릭터·주제·횟수·학생 역할을 그대로 씀', all(x in out for x in ['너는 고종이다','대화 주제(학생 과제): <1> 고종에게','학생의 5번째 발언','개화파 젊은 관리','조선의 26대 왕']), '')
    ok('대화 주제를 문장 속에 끼워 넣지 않음', '보고하세요. / <2>' in out and '보고하세요. 상황에서' not in out)
    ok('Gemini 키 없음 → 기본 틀', await T.evaluate('F("create").pgSrc')=='basic' and '기본 틀' in await toast(T))
    ok('생성해도 대화 시작 안 함', not any(x.startswith('fn:chat:chat') for x in await T.evaluate('__sbLog')))
    # Gemini 연결 → 프롬프트 + 캐릭터 추천
    await T.evaluate('localStorage.setItem("__aikey","AIzaTESTKEY_abcdefghijklmnopqrstu")')
    await T.click('[data-a=pg-gen][data-v=regen]'); await W(T,900)
    sent=json.loads([x for x in await T.evaluate('__sbLog') if x.startswith('suggest:')][-1][8:])
    ok('Gemini 요청에 캐릭터·주제·역할 포함(학생 글 없음)', sent['op']=='guide' and sent['name']=='고종' and sent['user']=='개화파 젊은 관리' and '<1>' in sent['question'] and 'base' in sent)
    ok('Gemini 프롬프트', (await T.input_value('#c-pgout')).startswith('(Gemini 다듬음') and await T.evaluate('!!document.querySelector(".pg-sug")'))
    await T.click('[data-a=pg-copy][data-v=out]'); await W(T); ok('프롬프트 복사', (await T.evaluate('window.__copied||""')).startswith('(Gemini'))
    await T.click('[data-a=pg-apply]'); await W(T)
    f=await T.evaluate('F("create")')
    ok('적용: 프롬프트 + 비어 있던 칸만 추천으로 채움', f['personaGuide'].startswith('(Gemini') and f['personaGreeting'].startswith('(테스트 시작)') and f['personaCall']=='경' and f['personaUser']=='개화파 젊은 관리' and f['personaStarters']=='보고드리겠습니다\n개화가 필요합니다', str({k:f.get(k) for k in ['personaUser','personaCall']}))
    ok('적용 안내에 채운 칸', '시작 메시지' in await toast(T) and '학생의 역할' not in (await toast(T)).split('비어 있던')[-1].split('도 채웠')[0])
    # 직접 작성 탭
    await T.click('[data-a=pg-mode][data-v=direct]'); await W(T)
    ok('직접 작성: 적용된 프롬프트', (await T.input_value('#c-pguide')).startswith('(Gemini'))
    await T.click('[data-a=pg-mode][data-v=gen]'); await W(T)
    await T.screenshot(path='/tmp/claude-0/smoke/chat_create.png', full_page=True)
    # 저장
    await T.click('[data-a=create-save]'); await W(T,900)
    rid=await T.evaluate('S.roomId'); per=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs']['rooms/'+rid]['data']['persona']
    ok('저장: 캐릭터·프롬프트·횟수', per['name']=='고종' and per['maxTurns']==5 and per['img']==img and per['user']=='개화파 젊은 관리' and per['call']=='경' and per['greeting'].startswith('(테스트') and per['starters']==['보고드리겠습니다','개화가 필요합니다'] and per['guide'].startswith('(Gemini') and per['gen']=={'type':'persuade','subj':'역사','grade':'고등학교 1학년','goal':'위정척사·개화의 논리를 당시 상황에 근거해 설명할 수 있다','support':'step'},
       str({k:(v[:15] if isinstance(v,str) else v) for k,v in per.items()}))
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,500)
    ok('수정 화면에서 모두 복원', await T.evaluate('document.getElementById("c-pcall").value==="경" && document.getElementById("c-pmax").value==="5" && document.getElementById("c-pstart").value.startsWith("보고") && document.querySelector("[data-a=pg-type][data-v=persuade]").getAttribute("aria-pressed")==="true" && !!document.querySelector(".cimg img")'))
    await T.evaluate('dropForm("create"); S.view="home"; render()'); await W(T)
    # 예전에 저장한 유형(negotiate·science)·횟수(12회)는 합친 유형·이전 설정으로 열린다
    await T.evaluate(f'''(()=>{{const m=JSON.parse(localStorage.getItem("__sbmock")); const d=m.docs["rooms/{rid}"].data.persona; d.gen={{...(d.gen||{{}}),type:"negotiate"}}; d.maxTurns=12; localStorage.setItem("__sbmock",JSON.stringify(m))}})()''')
    await T.reload(); await W(T,800); await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,500)
    ok('예전 유형(협상) → 설득·협상형으로 열림', await T.evaluate('document.querySelector("[data-a=pg-type][data-v=persuade]").getAttribute("aria-pressed")==="true"'))
    ok('예전 횟수 12회는 ‘이전 설정’으로 남음(저장해도 안 바뀜)', await T.evaluate('(()=>{const e=document.getElementById("c-pmax"); return e.value==="12" && [...e.options].map(o=>o.value).join()==="3,5,8,10,12" && /이전 설정/.test(e.selectedOptions[0].textContent)})()'))
    await T.evaluate('dropForm("create"); S.view="home"; render()'); await W(T)
    # 예전 활동(‘AI용 인물 자료’만 있음) 호환
    await T.evaluate(f'''(()=>{{const m=JSON.parse(localStorage.getItem("__sbmock")); const d=m.docs["rooms/{rid}"].data; d.persona={{name:"여운형",about:"",facts:"- 1945년 건준을 만들었다.",style:"persona",maxTurns:8}}; localStorage.setItem("__sbmock",JSON.stringify(m))}})()''')
    await T.reload(); await W(T,800); await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,500)
    ok('예전 인물 자료 안내', await T.evaluate('!!document.querySelector(".pg-legacy")'))
    await T.click('[data-a=pg-facts][data-v=move]'); await W(T)
    f=await T.evaluate('F("create")'); ok('프롬프트로 옮기기', f['personaGuide']=='[캐릭터 자료]\n- 1945년 건준을 만들었다.' and f['personaFacts']=='' and f['pgMode']=='direct')
    await T.evaluate('dropForm("create"); S.view="home"; render()'); await W(T)
    # 원래 설정으로 되돌려 학생 화면 확인
    await T.evaluate(f'''(()=>{{const m=JSON.parse(localStorage.getItem("__sbmock")); m.docs["rooms/{rid}"].data.persona={json.dumps(per, ensure_ascii=False)}; localStorage.setItem("__sbmock",JSON.stringify(m))}})()''')
    G=await c.new_page(); G.on('pageerror',lambda e:errs.append('G:'+str(e)))
    await G.goto(U+'?who=anon#'+rid); await W(G,900); await G.fill('#g-nick','지우'); await G.click('[data-a=guest-join]'); await W(G,1500)
    if await G.query_selector('[data-a=to-stage]'): await G.click('[data-a=to-stage]'); await W(G,400)
    ok('학생: 캐릭터 머리(이미지·이름·소개·나의 역할)', await G.evaluate('!!document.querySelector(".chathead img.cav") && document.querySelector(".chathead").textContent.includes("나의 역할: 개화파 젊은 관리")'))
    ok('학생: 시작 메시지가 첫 말풍선', (await G.evaluate('document.querySelector(".chatlog .bub.ai.greet p")?.textContent||""')).startswith('(테스트 시작)'))
    ok('학생: 추천 질문 버튼', await G.eval_on_selector_all('[data-a=chat-starter]','e=>e.map(x=>x.textContent)')==['보고드리겠습니다','개화가 필요합니다'])
    ok('학생: 대화 0 / 5', '대화 0 / 5' in await G.evaluate('document.querySelector(".chatcard .foot")?.textContent||""'))
    ok('학생: 프롬프트 안 보임', '활동 개요' not in await G.evaluate('document.body.innerText'))
    await G.click('[data-a=chat-starter] >> nth=0'); await G.click('[data-a=chat-send]'); await W(G,900)
    lc=await G.evaluate('window.__lastChat'); ok('보낸 대화: turn 1, 학생 말만(시작 메시지는 서버가 붙임)', lc['turn']==1 and len(lc['history'])==1 and lc['history'][0]['content']=='보고드리겠습니다', str(lc))
    ok('학생: 대화 1 / 5', '대화 1 / 5' in await G.evaluate('document.querySelector(".chatcard .foot")?.textContent||""'))
    await G.screenshot(path='/tmp/claude-0/smoke/chat_student.png', full_page=True)
    # 휴대폰
    M=await c.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,700); await M.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(M,600)
    r1=await M.evaluate(WIDE); await M.evaluate('document.querySelector(".ccard").scrollIntoView()'); await M.screenshot(path='/tmp/claude-0/smoke/mob/chat_char.png')
    await M.evaluate('document.getElementById("pguide").scrollIntoView()'); await M.screenshot(path='/tmp/claude-0/smoke/mob/chat_prompt.png')
    await G.set_viewport_size({'width':390,'height':844}); await W(G,400); r2=await G.evaluate(WIDE); await G.screenshot(path='/tmp/claude-0/smoke/mob/chat_student.png')
    ok('휴대폰 390: 넘침 없음(만들기·학생)', r1[0]<=390 and r2[0]<=390, str(r1)+str(r2))
    print('errors', errs); ok('페이지 오류 없음', not errs)
    print('FAILS', fails); await b.close()
asyncio.run(main())
