# 새 활동 화면: 활동 이름·소개 맨 위 · 핵심 질문 + 단계별 질문(질문 틀/직접 만들기) · 교사 이름 정하기·바꾸기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    # 교사 이름: 처음 로그인
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher&newteacher=1'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    print('first modal:', (await T.inner_text('#modal h3')) if await T.query_selector('#modal h3') else None, '| prefill:', await T.input_value('#t-name') if await T.query_selector('#t-name') else None)
    await T.fill('#t-name','  이태형  선생님 '); await T.click('[data-a=tname-save]'); await W(T,600)
    print('greeting:', await T.inner_text('.thead h1'), '| log:', [x for x in await T.evaluate('__sbLog') if x.startswith('tname') or x.startswith('updateUser')])
    await T.reload(); await W(T,800); print('modal after reload:', bool(await T.query_selector('#modal h3')), '| name:', await T.evaluate('S.sbName'))
    # 과목 하나 만들고 이름 바꾸기 → 과목에도
    await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title','1학년 사회'); await T.click('[data-a=mem-all]') if await T.query_selector('[data-a=mem-all]') else None; await T.click('[data-a=course-save]'); await W(T,600)
    print('course teacherName:', await T.evaluate('S.courses[0].teacherName'))
    await T.click('[data-a=home]'); await W(T); await T.evaluate('act("mcourse",{dataset:{v:""}})'); await W(T)
    await T.click('[data-a=tb-acct]'); await T.click('.tb-pop [data-a=tname-open]'); await W(T); await T.fill('#t-name','이선생'); await T.click('[data-a=tname-save]'); await W(T,700)
    print('renamed:', await T.inner_text('.thead h1'), '| course:', await T.evaluate('S.courses[0].teacherName'), '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    # 새 활동 화면 배치
    await T.click('[data-a=create]'); await W(T,400)
    print('order:', await T.evaluate('''[...document.querySelectorAll("#app .card > h3, .ctop label[for=c-title]")].map(x=>x.innerText.split("\\n")[0].trim().slice(0,24))'''))
    print('default qs:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'), '| adv has tool chips:', bool(await T.query_selector('details[data-adv] .toolchip')))
    await T.fill('#c-title','누구를 위한 근대화였을까'); await T.fill('#c-prompt','일제 강점기의 철도와 공장은 누구를 위한 근대화였을까?')
    await T.evaluate('act("tpl",{dataset:{v:"inquiry"}})') ; await W(T,300)
    print('inquiry default qs:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'))
    await T.click('[data-a=pick-tool][data-v=causeEffect]'); await W(T); print('causeEffect qs:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'))
    await T.click('[data-a=q-custom]'); await W(T)
    qs=['철도는 어디와 어디를 이었나요?','그 철도로 무엇이 옮겨졌나요?','그 결과 누가 이익을 얻었나요?']
    await T.fill('[data-qi="0"][data-qf=q]',qs[0]); await T.fill('[data-qi="1"][data-qf=q]',qs[1]); await T.click('[data-a=q-add]'); await W(T); await T.fill('[data-qi="2"][data-qf=q]',qs[2]); await T.fill('[data-qi="0"][data-qf=h]','지도 자료를 보세요')
    await T.click('[data-a=q-add]'); await W(T); await T.click('[data-a=q-del][data-i="3"]'); await W(T)
    await T.click('[data-a=q-move][data-i="1"][data-d="-1"]'); await W(T); print('after move:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'))
    await T.click('[data-a=q-move][data-i="0"][data-d="1"]'); await W(T)
    await T.screenshot(path='/tmp/claude-0/smoke/mob/create_top.png', full_page=False)
    y=await T.evaluate('document.querySelector(".stepq-card").getBoundingClientRect().top+scrollY-10'); await T.screenshot(path='/tmp/claude-0/smoke/mob/stepq.png', clip={'x':0,'y':y,'width':1280,'height':560}, full_page=True)
    await T.click('[data-a=create-save]'); await W(T,800); rid=await T.evaluate('S.roomId')
    print('saved fields:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").fields.map(x=>x.k+":"+(x.q||x.l)+(x.h?"("+x.h+")":""))'), '| title:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").title'))
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,400); print('edit qs:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'), '| custom pressed:', await T.get_attribute('[data-a=q-custom]','aria-pressed'))
    # 학생 화면 미리보기에서 질문 보이기
    await T.evaluate(f'act("home",{{dataset:{{}}}})'); await W(T)
    await T.evaluate(f'act("preview",{{dataset:{{id:"{rid}"}}}})'); await W(T,600)
    await T.evaluate(f'(()=>{{const r=room(); S.work=r.id; S.step[r.id]="write"; render()}})()'); await W(T,500)
    print('student sees:', await T.eval_on_selector_all('#stage legend, #stage label, #stage .fq','e=>e.map(x=>x.innerText.trim().split("\\n")[0]).filter(t=>t.length>3).slice(0,8)'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/stepq_student.png', full_page=True)
    M=await ctx.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,800); await M.click('.thead [data-a=create]'); await W(M,400); await M.click('[data-a=q-custom]'); await W(M)
    print('m overflow:', await M.evaluate('document.documentElement.scrollWidth')); y=await M.evaluate('document.querySelector(".stepq-card").getBoundingClientRect().top+scrollY-10'); await M.screenshot(path='/tmp/claude-0/smoke/mob/stepq_m.png', clip={'x':0,'y':y,'width':390,'height':600}, full_page=True)
    print('errors', errs); await b.close()
asyncio.run(main())
