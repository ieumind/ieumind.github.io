# 새 활동 화면 개선(2026-11-10g): 선택 표시 · AI 추천 접이 · 키워드 비우면 주제로 · 질문 유형 설명 · 단계 막대 · 학생 화면 미리보기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':1600,'height':1000}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await c.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    W=lambda ms=300: T.wait_for_timeout(ms)
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(800)
    await T.click('[data-a=create] >> nth=0'); await W(500)
    await T.click('[data-a=goal][data-v=question]'); await W()
    # 3. 고르지 않은 칸의 빈 동그라미는 숨김
    vis = await T.evaluate('[...document.querySelectorAll(".gcard")].map(g=>[g.getAttribute("aria-pressed"), getComputedStyle(g.querySelector(".gc-ck")).visibility])')
    ok('선택 안 한 칸은 빈 동그라미 없음', all(v=='hidden' for a,v in vis if a=='false'))
    ok('고른 칸은 체크 보임(넓은 화면)', any(v=='visible' for a,v in vis if a=='true'))
    ok('위치 표시(내 과목 › 새 활동)', '새 활동' in await T.locator('.crumb').inner_text())
    # 1단계(11-10h): 활동 유형 7개가 넓은 화면에서 한 줄, 고른 유형 설명은 아래 한 줄
    tops = await T.evaluate('[...new Set([...document.querySelectorAll(".gcard")].map(g=>Math.round(g.getBoundingClientRect().top)))].length')
    ok('활동 유형 7개가 한 줄', tops==1, tops)
    ok('고른 유형 설명 한 줄', '질문 활동' in await T.locator('#c-gsel').inner_text())
    # 2단계(11-10i): 필수(활동·주제·대상) 다음에 ‘더 설정하기’ — 활동 이름·깊이·세부 설정·수업 정보는 접혀 있음
    order = await T.evaluate('[...document.querySelectorAll(".cform > [data-cs]")].map(x=>x.dataset.cs).join(",")')
    ok('순서: 활동→주제→(단계 질문)→대상→더 설정하기', order in ('goal,topic,stepq,who,more','goal,topic,who,more'), order)
    folds = await T.evaluate('[...document.querySelectorAll(".cmore > details.cfold")].map(d=>d.dataset.keep+":"+d.open).join(",")')
    ok('더 설정하기 안은 모두 접힘', folds=='title:false,depth:false,adv:false,info:false', folds)
    ok('단계 막대 끝에 더 설정하기', (await T.locator('#cstep button').last.inner_text()).strip().endswith('더 설정하기'))
    # 4. AI 박스는 접혀 있고, 주제 입력칸이 먼저
    ok('AI 추천 박스는 접혀 있음', await T.evaluate('!document.querySelector("details.aisug").open'))
    ok('주제 입력칸이 AI 박스보다 위', await T.evaluate('document.getElementById("c-prompt").compareDocumentPosition(document.querySelector("details.aisug")) & Node.DOCUMENT_POSITION_FOLLOWING'))
    # 8. 단계 막대: 처음엔 주제 칸이 비어 ‘!’, 쓰면 바로 ‘✓’ (다시 그리지 않고)
    ok('단계 막대 5칸(번호 4 + 더 설정하기)', await T.locator('#cstep button').count()==5, await T.locator('#cstep button').count())
    ok('주제 비어 있으면 ! 표시', await T.locator('#cstep [data-v=topic] .st.need').count()==1)
    await T.fill('#c-prompt','3·1 운동에 대해 궁금한 것을 질문으로 만들어 보자.'); await W(250)
    ok('쓰면 바로 ✓', await T.locator('#cstep [data-v=topic] .st.ok').count()==1)
    # 9. 미리보기가 쓰는 대로 바뀜
    ok('미리보기에 핵심 질문 보임', '3·1 운동' in await T.locator('.cprev-b .cp-q').inner_text())
    await T.evaluate('document.querySelectorAll("details.cfold").forEach(d=>d.open=true)'); await T.wait_for_timeout(150)
    await T.fill('#c-title','3·1 운동 질문 만들기'); await T.fill('#c-intro','친구와 질문을 나눠요.'); await W(250)
    pv = await T.locator('.cprev-b').inner_text()
    ok('미리보기에 제목·소개 보임', '3·1 운동 질문 만들기' in pv and '친구와 질문을 나눠요' in pv, pv[:80])
    ok('넓은 화면: 미리보기가 오른쪽에 같이 보임', await T.evaluate('(()=>{const a=document.querySelector(".cprev").getBoundingClientRect(), m=document.getElementById("c-prompt").getBoundingClientRect(); return a.left>m.right && a.width>250})()'))
    # 5. 키워드 비우고 추천 → 주제로 추천
    await T.evaluate('localStorage.setItem("__aikey","AIzaTESTKEY0000000000000000000")')
    await T.click('details.aisug > summary'); await W(200)
    ok('열면 키워드·추천 버튼 보임', await T.locator('#c-kw').is_visible())
    await T.click('.btn.wand'); await W(1200)
    n = await T.evaluate('(S.aiSug && S.aiSug.items || []).length')
    ok('키워드 비워도 주제로 추천 나옴', n>0, n)
    lg = await T.evaluate('window.__sbLog.filter(x=>x.startsWith("suggest:")).pop()||""')
    ok('서버에 보낸 키워드 = 위에 쓴 주제', '3·1 운동에 대해 궁금한 것을' in lg, lg[:120])
    ok('추천이 뜨면 박스가 열린 채', await T.evaluate('document.querySelector("details.aisug").open'))
    # 주제도 키워드도 없으면 안내
    await T.evaluate('S.aiSug=null; S.form.create.prompt=""; S.form.create.aiKw=""; S.form.create.title=""; render()'); await W(300)
    await T.evaluate('document.querySelector("details.aisug").open=true'); await W(100)
    await T.click('.btn.wand'); await W(400)
    ok('둘 다 없으면 추천 안 하고 안내', (await T.evaluate('S.aiSug'))==None and await T.evaluate('!(S.aiSug&&S.aiSug.loading)'))
    # 6. 질문 유형: 툴팁 + 고른 유형 설명 한 줄 + 알약 버튼
    await T.fill('#c-prompt','질문을 만들어 보자'); await W(200)
    tip = await T.evaluate('document.querySelector("label.choice[title]")?.title||""')
    ok('유형 칩에 마우스 설명(title)', len(tip)>5, tip)
    await T.click('label.choice:has-text("논쟁적")'); await W(300)
    ok('고른 유형 뜻이 칩 아래에 한 줄', '사람마다 서로 다른 답' in await T.locator('#c-qtd').inner_text(), await T.locator('#c-qtd').inner_text())
    ok('유형 비교 버튼이 알약 모양', await T.locator('details.help.helpcta > summary').count()==1)
    # 7. 안내문 한 줄
    await T.evaluate('document.querySelector("details.aisug").open=true'); await W(100)
    note = await T.locator('.aisug-note').inner_text()
    nh = await T.evaluate('document.querySelector(".aisug-note").getBoundingClientRect().height')
    ok('AI 안내문 한 줄(짧게)', len(note)<80 and nh<40, f'{nh} {note!r}')
    # 8. 단계 막대로 이동
    await T.click('#cstep [data-v=who]'); await W(900)
    top = await T.evaluate('document.querySelector(".cform > .card[data-cs=who]").getBoundingClientRect().top')
    bh = await T.evaluate('document.getElementById("cstep").getBoundingClientRect().bottom')
    ok('⑤로 이동해 화면에 보임(문서 끝이면 더 못 올라감)', bh <= top <= 880 and await T.evaluate('scrollY')>300, f'{top} {bh}')
    ok('현재 단계 표시', await T.locator('#cstep [aria-current=step]').count()==1)
    # 좁은 화면: 미리보기는 접혀 있다가 눌러서 열기
    await T.set_viewport_size({'width':1100,'height':900}); await W(300); await T.evaluate('render()'); await W(300)
    ok('좁은 화면: 미리보기 접힘', not await T.locator('.cprev-b').is_visible())
    await T.click('.cprev-tog'); await W(300)
    ok('눌러서 열면 보임', await T.locator('.cprev-b .cp').is_visible())
    # 토론: 입장 2개 필요 → 단계 막대에 표시
    await T.set_viewport_size({'width':1600,'height':1000}); await W(200)
    await T.evaluate('window.scrollTo(0,0)')
    await T.click('[data-a=goal][data-v=compare]'); await W(300)
    await T.fill('#c-prompt','해방 직후 무엇을 먼저 해야 했을까?'); await T.fill('#c-st0',''); await T.fill('#c-st1',''); await W(250)
    ok('입장 비어 있으면 ! 표시', await T.locator('#cstep [data-v=topic] .st.need').count()==1)
    await T.fill('#c-st0','친일 청산'); await T.fill('#c-st1','국가 체제 정비'); await W(250)
    ok('입장 채우면 ✓', await T.locator('#cstep [data-v=topic] .st.ok').count()==1)
    ok('미리보기에 입장 칩', await T.locator('.cprev-b .chip.st').count()==2, await T.locator('.cprev-b .chip.st').count())
    ok('오류 없음', not errs, errs)
    await b.close()
  print('FAILS', fails); raise SystemExit(1 if fails else 0)
asyncio.run(main())
