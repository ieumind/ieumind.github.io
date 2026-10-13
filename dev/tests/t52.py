# 질문 유형 선택 사항 · 필수 * 표시 · 단계별 질문 틀 6개 · 과목 여러 개 고르기(과목마다 활동) · 그룹별 공개 접기 · 타이머 초 단위
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10401 나다은'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['number']:s for s in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']}
    for t in ['A반 사회','B반 사회']:
      await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title',t); await T.click('[data-a=mem-all]'); await T.click('[data-a=course-save]'); await W(T,500)
      await T.click('[data-a=home]'); await W(T); await T.evaluate('act("mcourse",{dataset:{v:""}})'); await W(T)
    ca,cb=await T.evaluate('S.courses.map(c=>c.id)')
    s1,s2=studs['10301']['id'],studs['10401']['id']
    await T.evaluate(f'(async()=>{{const c=S.courses.find(x=>x.id==="{ca}"); const groups=Array.from({{length:12}},(_, i)=>({{id:"g"+i,name:"모둠 "+(i+1),members:i===0?["{s1}"]:["{s2}"]}})); await write(db=>db.doc("courses/"+c.id).update({{groups}}),()=>{{c.groups=groups}}); render()}})()'); await W(T,400)
    await T.click('[data-a=create]'); await W(T,400)
    print('required stars:', await T.eval_on_selector_all('.req','e=>e.map(x=>x.parentElement.innerText.replace(/\\s+/g," ").slice(0,22))'))
    print('frames:', await T.eval_on_selector_all('.stepq-card .toolchip b','e=>e.map(x=>x.textContent)'))
    await T.evaluate('act("tpl",{dataset:{v:"inquiry"}})'); await W(T,300)
    print('qtype opts:', await T.eval_on_selector_all('input[data-k=qtype]','e=>e.map(x=>(x.value||"(없음)")+(x.checked?"✓":""))'), '| legend:', await T.inner_text('fieldset:has(input[data-k=qtype]) legend'))
    await T.click('[data-a=pick-tool][data-v=problem]'); await W(T); print('problem qs:', await T.eval_on_selector_all('[data-qf=q]','e=>e.map(x=>x.value)'))
    await T.fill('#c-prompt','우리 학교 급식 잔반 문제를 어떻게 해결할까?')
    # 과목 두 개 고르기
    await T.click(f'[data-a=c-course][data-v="{ca}"]'); await W(T); await T.click(f'[data-a=c-course][data-v="{cb}"]'); await W(T)
    print('picked:', await T.eval_on_selector_all('[data-a=c-course][aria-pressed=true]','e=>e.map(x=>x.textContent.trim())'), '| hint:', await T.inner_text('.cpick + .hint'))
    print('group details open?:', await T.evaluate('[...document.querySelectorAll(".gsched-d")].map(d=>d.open)'), '| summary:', await T.inner_text('.gsched-d summary'))
    page_h=await T.evaluate('document.documentElement.scrollHeight')
    await T.click('.gsched-d summary'); await W(T,300); print('opened rows:', len(await T.query_selector_all('.gsched-d[open] .gsrow')), '| page grows:', await T.evaluate('document.documentElement.scrollHeight') - page_h)
    await T.screenshot(path='/tmp/claude-0/smoke/mob/c_pick.png', clip={'x':0,'y':await T.evaluate('document.querySelector(".cpick").getBoundingClientRect().top+scrollY-80'),'width':1280,'height':520}, full_page=True)
    await T.click('[data-a=create-save]'); await W(T,1200)
    rs=await T.evaluate('S.rooms.map(r=>[r.title,r.courseId, Object.keys(r.assign||{}).length, r.qtype])')
    print('rooms:', rs, '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    print('notify log:', [x.split('|')[-2:] for x in await T.evaluate('__sbLog') if x.startswith('notify')])
    # 과목 없이로 되돌리기 (해제)
    await T.click('[data-a=create]'); await W(T); await T.click(f'[data-a=c-course][data-v="{ca}"]'); await W(T); await T.click(f'[data-a=c-course][data-v="{ca}"]'); await W(T)
    print('toggle off:', await T.eval_on_selector_all('[data-a=c-course][aria-pressed=true]','e=>e.map(x=>x.textContent.trim())'))
    # 수정 화면: 과목 하나만
    rid=await T.evaluate(f'S.rooms.find(r=>r.courseId==="{cb}").id')
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,400); await T.click(f'[data-a=c-course][data-v="{ca}"]'); await W(T)
    print('edit single:', await T.eval_on_selector_all('[data-a=c-course][aria-pressed=true]','e=>e.map(x=>x.textContent.trim())'))
    # 타이머 초
    await T.evaluate(f'act("home",{{dataset:{{}}}}); act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,400)
    print('timer chips:', await T.eval_on_selector_all('.tmrpanel [data-a=tmr-start][data-s]','e=>e.map(x=>x.textContent)'))
    await T.click('.tmrpanel [data-s="30"]'); await W(T,400); print('30s:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").timer.dur'), await T.inner_text('.tmrpanel .tmr-t'))
    await T.click('[data-a=tmr-add][data-v="30"]'); await W(T,300); print('+30s dur:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").timer.dur'))
    await T.click('[data-a=tmr-stop]'); await W(T,300); await T.fill('#tmr-min','1'); await T.fill('#tmr-sec','20'); await T.click('.tmr-custom [data-a=tmr-start]'); await W(T,400)
    print('1m20s:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").timer.dur'), '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    M=await ctx.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,800); await M.click('.thead [data-a=create]'); await W(M,400); print('m overflow:', await M.evaluate('document.documentElement.scrollWidth'))
    print('errors', errs); await b.close()
asyncio.run(main())
