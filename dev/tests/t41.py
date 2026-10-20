# 패들렛 쪽지 · 하트 · 댓글 · 교사 학생 카드(바로 피드백) · 논술 깊이 · 오류·건의 보내기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    DB=lambda pg: pg.evaluate('JSON.parse(localStorage.getItem("__sbmock"))')
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n10303 박서준'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['name']:s for s in (await DB(T))['students']}
    # essay depth
    await T.click('.thead [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=write]'); await W(T)
    for d in ['quick','normal','deep']:
      await T.click(f'[data-a=depth][data-v={d}]'); await W(T)
      print('essay', d, '->', await T.evaluate('[...document.querySelectorAll(".depth")].filter(x=>x.getAttribute("aria-pressed")==="true").map(x=>x.dataset.v).join()'), await T.evaluate('S.form.create.reveal'))
    await T.click('[data-a=goal][data-v=compare]'); await W(T)
    await T.fill('#c-prompt','콜럼버스의 날을 원주민의 날로 바꿔야 할까?'); await T.fill('#c-title','콜럼버스 토론')
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    st=await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").stances')
    D=await DB(T); now=1791730000000
    for i,(pid,nm,claim,reason) in enumerate([('pK','10301 김가온','바꿔야 한다','원주민이 겪은 피해를 기억해야 하니까'),('pN','10302 나다은','그대로 두자','역사 속 인물로서의 의미도 있으니까 설명을 덧붙이면 돼요'),('pB','10303 박서준','바꿔야 한다','기념일은 오늘의 가치를 보여 주니까')]):
      sid=studs[nm.split()[1]]['id']
      D['docs']['posts/'+pid]={'col':'posts','id':pid,'owner':sid,'data':{'roomId':rid,'author':nm,'stance':st[0 if claim=='바꿔야 한다' else 1],'body':{'claim':claim,'reason':reason},'status':'submitted','createdAt':now+i,'updatedAt':now+i}}
    await T.evaluate('d=>localStorage.setItem("__sbmock",JSON.stringify(d))', D)
    K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e)))
    await K.goto(U+'?who=anon'); await W(K,500)
    await K.fill('#f-num','10301'); await K.fill('#f-name','김가온'); await K.fill('#f-code',studs['김가온']['code']); await K.press('#f-code','Enter'); await W(K,1300)
    await K.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(K,600)
    print('pads:', await K.eval_on_selector_all('.post.wcard','e=>e.map(x=>x.querySelector(".pad-h .who b").textContent+" | "+(x.querySelector(".pad-title")?.textContent||"")+" | "+x.getAttribute("style"))'))
    await K.click('.wcard:not(.mine) .hbtn'); await W(K,400)
    await K.click('.wcard:not(.mine) .pad-add'); await W(K,500)
    print('focused:', await K.evaluate('document.activeElement?.dataset?.form'))
    await K.keyboard.type('좋은 생각이야!'); await K.click('.pad-cmt [data-a=save-comment]'); await W(K,600)
    await K.click('[data-a=close-post]'); await W(K,300)
    await K.screenshot(path='/tmp/claude-0/smoke/mob/pads.png', full_page=True)
    await K.set_viewport_size({'width':390,'height':844}); await W(K,300); await K.screenshot(path='/tmp/claude-0/smoke/mob/pads_m.png', full_page=True)
    # feedback modal survives re-render
    await K.click('#side-tog'); await W(K); await K.click('[data-a=feedback-open]'); await W(K); await K.fill('#fb-body','게시판이 좋아요'); await K.evaluate('render()'); await W(K)
    print('fb kept after render:', await K.input_value('#fb-body')); await K.click('[data-a=fb-send]'); await W(K,500)
    print('fb stored:', [x['body'] for x in await K.evaluate('JSON.parse(localStorage.getItem("__fb")||"[]")')])
    # teacher students tab
    await T.reload(); await W(T,800); await T.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,500)
    await T.click('[data-a=ttab][data-v=students]'); await W(T,400)
    print('tcards:', await T.eval_on_selector_all('.tcard .tc-meta','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    await T.click('.tcard [data-a=qfb] >> nth=0'); await W(T); await T.click('.qfb-chips .chip >> nth=0'); await W(T)
    print('fb text:', await T.input_value('.qfb textarea'))
    await T.click('.qfb [data-a=save-feedback]'); await W(T,500)
    print('after fb:', await T.eval_on_selector_all('.tc-fb','e=>e.map(x=>x.textContent)'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/tcards.png', full_page=True)
    print('errors', errs); await b.close()
asyncio.run(main())
