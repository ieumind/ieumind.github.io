# 과목이 3개를 넘으면 ‘더 보기’ · 과목 보관(지난 학기) → 교사 목록·학생 화면에서 빠짐, 보관 해제
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    code=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students'][0]['code']
    for i,t in enumerate(['1학년 한국사','2학년 세계사','통합사회','동아시아사','지난 학기 한국사']):
      await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title',t); await T.click('[data-a=mem-all]'); await T.click('[data-a=course-save]'); await W(T,500)
      await T.click('[data-a=create]'); await W(T); await T.fill('#c-prompt',f'{t} 질문?'); await T.click('[data-a=create-save]'); await W(T,600)
      await T.click('[data-a=home]'); await W(T); await T.evaluate('act("mcourse",{dataset:{v:""}})'); await W(T,300)
    cards=lambda pg: pg.eval_on_selector_all('.dgrid > .dcard:not(.dadd)','e=>e.map(x=>x.querySelector(".dt").innerText.trim())')
    print('teacher cards:', await cards(T), '| more:', await T.inner_text('[data-a=courses-more]'), '| tile:', await T.inner_text('.tstat.t1 b'))
    await T.click('[data-a=courses-more]'); await W(T); print('after more:', len(await cards(T)), await T.inner_text('[data-a=courses-more]'))
    # archive '지난 학기 한국사' via modal
    cid=await T.evaluate('S.courses.find(c=>c.title==="지난 학기 한국사").id')
    await T.evaluate(f'act("mcourse",{{dataset:{{v:"{cid}"}}}})'); await W(T,300)
    await T.click(f'.chead [data-a=course-edit]:not([data-focus])'); await W(T,400)
    print('modal archive btn:', await T.inner_text('#modal [data-a=course-archive]'))
    await T.click('#modal [data-a=course-archive]'); await W(T,500)
    print('archived:', await T.evaluate(f'S.courses.find(c=>c.id==="{cid}").archived'), '| view:', await T.evaluate('S.mcourse'), '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    print('cards now:', await cards(T), '| tile:', await T.inner_text('.tstat.t1 b'), '| arch link:', await T.inner_text('[data-a=courses-arch]'))
    print('all-activities count (archived hidden):', len(await T.query_selector_all('.mcard')))
    await T.click('[data-a=courses-arch]'); await W(T); print('archbox:', await T.eval_on_selector_all('.archbox .dt','e=>e.map(x=>x.innerText.trim())'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/courses_arch.png', full_page=True)
    await T.click('[data-a=create]'); await W(T); print('create select has archived:', await T.evaluate(f'[...document.querySelectorAll("#c-course option")].some(o=>o.value==="{cid}")'))
    # edit course keeps archived
    await T.evaluate(f'act("home",{{dataset:{{}}}}); act("mcourse",{{dataset:{{v:"{cid}"}}}})'); await W(T,300)
    print('banner:', await T.inner_text('.archwarn'))
    await T.click(f'.chead [data-a=course-edit]:not([data-focus])'); await W(T,300); await T.fill('#course-title','지난 학기 한국사 (2026-1)'); await T.click('[data-a=course-save]'); await W(T,500)
    print('still archived after edit:', await T.evaluate(f'S.courses.find(c=>c.id==="{cid}").archived'))
    # student
    K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon'); await W(K,500)
    await K.fill('#f-num','10301'); await K.fill('#f-name','김가온'); await K.fill('#f-code',code); await K.press('#f-code','Enter'); await W(K,1300)
    print('student cards:', await cards(K), '| more:', await K.inner_text('[data-a=dash-more]') if await K.query_selector('[data-a=dash-more]') else None)
    print('student todo titles:', await K.eval_on_selector_all('.todolist b','e=>e.map(x=>x.textContent)'))
    await K.click('[data-a=dash-more]'); await W(K); print('student after more:', len(await cards(K)))
    # unarchive
    await T.click('.archwarn [data-a=course-archive]'); await W(T,600); await W(K,800)
    print('unarchived:', await T.evaluate(f'S.courses.find(c=>c.id==="{cid}").archived'), '| student now:', len(await cards(K)))
    # mobile
    M=await ctx.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=teacher'); await W(M,700); print('m overflow:', await M.evaluate('document.documentElement.scrollWidth')); await M.screenshot(path='/tmp/claude-0/smoke/mob/m_courses.png', full_page=True)
    print('errors', errs); await b.close()
asyncio.run(main())
