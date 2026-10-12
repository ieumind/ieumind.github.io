# 학생 한 명이 두 선생님 과목 듣기(＋ 과목 추가) · 선생님마다 다른 이름표로 글쓰기 · 과목 정렬(사용자 지정·오래된 순·최신순)과 순서 바꾸기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    async def teacher(who, roster, courses):
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(who+':'+str(e)))
      await T.goto(U+'?who='+who); await W(T,700)
      await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add',roster); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
      for t in courses:
        await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title',t); await T.click('[data-a=mem-all]'); await T.click('[data-a=course-save]'); await W(T,500)
        await T.click('[data-a=create]'); await W(T); await T.fill('#c-prompt',f'{t} 질문?'); await T.click('[data-a=create-save]'); await W(T,600)
        await T.click('[data-a=home]'); await W(T); await T.evaluate('act("mcourse",{dataset:{v:""}})'); await W(T,200)
      return T
    P0=await ctx.new_page(); await P0.goto(U+'?who=teacher'); await P0.evaluate('localStorage.clear()'); await P0.close()
    A=await teacher('teacher','10301 김가온',['사회','역사','지리','윤리'])
    B=await teacher('teacher2','한백고 10301 김가온',['과학'])
    D=(await A.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))
    codes={(s.get('tid') or 'T'):s['code'] for s in D['students']}
    print('teacher A sees:', await A.evaluate('S.courses.map(c=>c.title)'), '| B sees:', await B.evaluate('S.courses.map(c=>c.title)'))
    K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon'); await W(K,500)
    await K.fill('#f-num','10301'); await K.fill('#f-name','김가온'); await K.fill('#f-code',codes['T']); await K.press('#f-code','Enter'); await W(K,1300)
    print('student before:', await K.evaluate('S.courses.map(c=>c.title)'), '| join btn:', await K.inner_text('[data-a=join-open]'))
    await K.click('[data-a=join-open]'); await W(K); print('prefill:', await K.input_value('#j-num'), await K.input_value('#j-name'))
    await K.fill('#j-code','WRONG1'); await K.click('[data-a=join-save]'); await W(K,600); print('wrong code toast:', await K.evaluate('document.getElementById("toast")?.textContent'))
    await K.fill('#j-code',codes['T2']); await K.click('[data-a=join-save]'); await W(K,1800)
    print('student after:', sorted(await K.evaluate('S.courses.map(c=>c.title)')), '| idents:', await K.evaluate('S.idents.map(x=>x.tid+":"+x.name)'), '| toast:', await K.evaluate('document.getElementById("toast")?.textContent'))
    # post into teacher B's room with B's label and into A's room with A's label
    for title in ['과학 질문?','사회 질문?']:
      rid=await K.evaluate(f'S.rooms.find(r=>r.prompt==="{title}").id')
      ok=await K.evaluate(f'(async()=>{{const r=S.rooms.find(x=>x.id==="{rid}"); return await savePost(r,{{stance:r.stances[0], body:{{claim:"내 생각", reason:"이유"}}, status:"submitted", submittedAt:Date.now()}})}})()'); await W(K,500)
      print('post in', title, ok, '| author:', await K.evaluate(f'S.posts.find(p=>p.roomId==="{rid}")?.author'), '| myPost:', bool(await K.evaluate(f'myPost(S.rooms.find(x=>x.id==="{rid}"))')))
    await W(B,800); print('teacher B sees post by:', await B.evaluate('S.posts.map(p=>p.author)'))
    # join same teacher again
    await K.click('[data-a=join-open]'); await W(K); await K.fill('#j-code',codes['T2']); await K.click('[data-a=join-save]'); await W(K,600); print('again toast:', await K.evaluate('document.getElementById("toast")?.textContent'))
    # sorting (student)
    await K.evaluate('S.allDash=true; render()'); await W(K)
    dt=lambda pg: pg.eval_on_selector_all('.dgrid .dcard:not(.dadd) .dt','e=>e.map(x=>x.innerText.trim().split("\\n").pop())')
    print('student custom:', await dt(K))
    await K.select_option('#c-sort','new'); await W(K); print('student new:', await dt(K), '| edit btn:', bool(await K.query_selector('[data-a=corder-edit]')))
    await K.select_option('#c-sort','custom'); await W(K); await K.click('[data-a=corder-edit]'); await W(K)
    first=(await dt(K))[0]; await K.click(f'.dedit:first-child [data-d="1"]'); await W(K); print('student moved first->2nd:', await dt(K), '| saved:', await K.evaluate('localStorage.getItem("nonjae.corder")') is not None)
    src=K.locator('.dedit').nth(3); dst=K.locator('.dedit').nth(0); await src.drag_to(dst); await W(K,400); print('student after pw drag 4th->1st:', await dt(K))
    await K.evaluate('''(()=>{const c=[...document.querySelectorAll(".dedit")]; const dtf=new DataTransfer(); const f=(el,t)=>el.dispatchEvent(new DragEvent(t,{bubbles:true,cancelable:true,dataTransfer:dtf})); f(c[4],"dragstart"); f(c[0],"dragover"); f(c[0],"drop"); f(c[4],"dragend")})()'''); await W(K,400); print('student after synthetic drag 5th->1st:', await dt(K))
    await K.click('[data-a=corder-edit]'); await W(K); await K.reload(); await W(K,1500); await K.evaluate('S.allDash=true; render()'); await W(K); print('student order after reload:', await dt(K))
    # teacher A custom order persisted to course docs
    await A.evaluate('S.allCourses=true; render()'); await W(A)
    print('teacher custom:', await dt(A))
    await A.click('[data-a=corder-edit]'); await W(A); await A.click('.dedit:nth-child(1) [data-d="1"]'); await W(A,500)
    print('teacher moved:', await dt(A), '| ords:', await A.evaluate('S.courses.map(c=>c.title+":"+c.ord)'))
    await A.select_option('#c-sort','old'); await W(A); print('teacher old:', await dt(A))
    await A.select_option('#c-sort','custom'); await W(A); await A.reload(); await W(A,1200); await A.evaluate('S.allCourses=true; render()'); await W(A); print('teacher after reload:', await dt(A))
    await A.screenshot(path='/tmp/claude-0/smoke/mob/csort_t.png')
    await K.set_viewport_size({'width':390,'height':844}); await K.evaluate('S.corderEdit=true; render()'); await W(K); print('m overflow:', await K.evaluate('document.documentElement.scrollWidth')); await K.screenshot(path='/tmp/claude-0/smoke/mob/csort_m.png', full_page=True)
    print('errors', errs); await b.close()
asyncio.run(main())
