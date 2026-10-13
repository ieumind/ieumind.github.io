# 알림은 과목 활동만 · 그룹별 공개(바로/예약)·그룹 알림 · 예약 알림 등록/해제
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    log=lambda: T.evaluate('__sbLog.filter(x=>x.startsWith("notify")||x.startsWith("sched"))')
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10401 나다은'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['number']:s for s in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']}
    # 1) 과목 없는 활동: 알림 칸 없음, 알림 안 감
    await T.click('[data-a=create]'); await W(T)
    print('no-course notify box:', bool(await T.query_selector('[data-k=notify]')))
    await T.fill('#c-prompt','과목 없는 질문?'); await T.click('[data-a=create-save]'); await W(T,700)
    print('log after no-course create:', await log())
    # 2) 과목 + 그룹(학생 명단)
    await T.click('[data-a=home]'); await W(T); await T.evaluate('act("mcourse",{dataset:{v:""}})'); await W(T)
    await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title','1학년 사회'); await T.click('[data-a=mem-all]'); await T.click('[data-a=course-save]'); await W(T,600)
    cid=await T.evaluate('S.courses[0].id')
    s1,s2=studs['10301']['id'],studs['10401']['id']
    await T.evaluate(f'(async()=>{{const c=S.courses[0]; const groups=[{{id:"g3",name:"1-3",members:["{s1}"]}},{{id:"g4",name:"1-4",members:["{s2}"]}}]; await write(db=>db.doc("courses/"+c.id).update({{groups}}),()=>{{c.groups=groups}}); render()}})()'); await W(T,500)
    await T.click('[data-a=create]'); await W(T)
    print('course notify box:', bool(await T.query_selector('[data-k=notify]')), '| group rows:', await T.eval_on_selector_all('.gsrow','e=>e.map(x=>x.innerText.replace(/\\s+/g," ").trim())'))
    await T.fill('#c-prompt','개항은 기회였을까?')
    await T.click('.gsched-d summary'); await W(T,300); await T.select_option('select[data-k="gsm:g4"]','at'); await W(T)
    await T.click('[data-a=create-save]'); await W(T,500); print('no time toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    await T.evaluate('''(()=>{const d=new Date(Date.now()+3*3600e3), z=n=>String(n).padStart(2,"0"); const v=`${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}T${z(d.getHours())}:${z(d.getMinutes())}`; const el=document.querySelector('input[data-k="gsa:g4"]'); el.value=v; el.dispatchEvent(new Event("input",{bubbles:true}))})()''')
    await T.screenshot(path='/tmp/claude-0/smoke/mob/gsched_pc.png', clip={'x':0,'y':await T.evaluate('document.querySelector(".gsched").getBoundingClientRect().top+scrollY-60'),'width':1280,'height':330}, full_page=True)
    await T.click('[data-a=create-save]'); await W(T,900)
    rid=await T.evaluate('S.roomId')
    print('assign:', await T.evaluate(f'JSON.stringify(Object.fromEntries(Object.entries(S.rooms.find(r=>r.id==="{rid}").assign).map(([g,a])=>[g,a.status+(a.startAt?"+at":"")])))'), '| notify flag:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").notify'))
    print('log after group create:', (await log())[-3:], '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    # 학생: 1-3은 보이고 1-4는 아직
    async def stu(num):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e)+' '+(e.stack or '')[:400])); await K.goto(U+'?who=anon'); await W(K,500)
      await K.fill('#f-num',num); await K.fill('#f-name',studs[num]['name']); await K.fill('#f-code',studs[num]['code']); await K.press('#f-code','Enter'); await W(K,1300); return K
    K3=await stu('10301'); print('1-3 student todo:', await K3.eval_on_selector_all('.todolist b','e=>e.map(x=>x.textContent)'))
    await K3.close()
    K4=await stu('10401'); print('1-4 student todo (scheduled):', await K4.eval_on_selector_all('.todolist b','e=>e.map(x=>x.textContent)'))
    # 교사가 1-4를 지금 열기 → 1-4에만 알림, 예약 지움
    await T.evaluate('act("ttab",{dataset:{v:"overview"}})'); await W(T,300)
    await T.click('[data-a=asg-st][data-g=g4][data-v=open]'); await W(T,800)
    print('log after open g4:', (await log())[-2:], '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    await W(K4,800); print('1-4 student todo now:', await K4.eval_on_selector_all('.todolist b','e=>e.map(x=>x.textContent)'))
    # 수정 화면 다시 열면 예약 값 채워짐 (1-4는 이제 바로 공개)
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,400)
    print('edit prefill:', await T.evaluate('[S.form.create["gsm:g3"], S.form.create["gsm:g4"]]'))
    # 공지(과목) 알림은 과목으로
    print('errors', errs); await b.close()
asyncio.run(main())
