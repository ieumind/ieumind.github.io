# 교사 설치 버튼 · 체험 세계사 과목 · 둘러보기(결과 보기→학생 생각) · 댓글로 만나기 · 입장 색 쪽지 · 자료 펼침·사진
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    # demo
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700)
    print('teacher install btn:', bool(await D.query_selector('#topr [data-a=install-help]')))
    print('demo courses:', await D.evaluate('S.courses.map(c=>c.title+":"+S.rooms.filter(r=>r.courseId===c.id).map(r=>r.id).join("/"))'))
    seen=[]
    for i in range(16):
      t=await D.text_content('#tour h3') if await D.query_selector('#tour h3') else None
      if not t: break
      seen.append(t)
      if '결과 보기' in t:
        await D.click('.mcard:has([data-id="demo-draw"]) [data-a="open"].pri'); await W(D,400); continue   # 직접 누르기
      if "‘학생 생각’" in t:
        await D.click('[data-a="ttab"][data-v="students"]'); await W(D,400); continue
      if '결과물' in t: await D.screenshot(path='/tmp/claude-0/smoke/mob/tour_result.png')
      nx=await D.query_selector('[data-a=tour-next]')
      if not nx: break
      await nx.click(); await W(D,300)
    print('tour:', seen)
    print('after tour view:', await D.evaluate('[S.view,S.ttab]'))
    # supa flow
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['name']:s for s in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']}
    await T.click('.thead [data-a=create]'); await W(T)
    await T.fill('#c-prompt','콜럼버스의 날을 원주민의 날로 바꿔야 할까?'); await T.fill('#c-context','콜럼버스는 1492년 아메리카에 도착했다.\n참고: https://example.com')
    await T.set_input_files('input[data-ctx-file]', ['/tmp/claude-0/smoke/pic1.jpg','/tmp/claude-0/smoke/pic2.jpg']); await W(T,1500)
    print('ctx imgs in form:', await T.evaluate('(S.form.create.ctxImgs||[]).length'), '| uploads:', [x for x in await T.evaluate('__sbLog') if x.startswith('mupload')][:2])
    await T.click('[data-a=ctx-img-del][data-i="1"]'); await W(T); print('after del:', await T.evaluate('S.form.create.ctxImgs.length'))
    await T.set_input_files('input[data-ctx-file]', ['/tmp/claude-0/smoke/pic2.jpg']); await W(T,1200)
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    print('room ctxImgs:', await T.evaluate(f'(S.rooms.find(r=>r.id==="{rid}").ctxImgs||[]).length'))
    st=await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").stances')
    Dm=await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'); now=1791740000000
    Dm['docs']['posts/pN']={'col':'posts','id':'pN','owner':studs['나다은']['id'],'data':{'roomId':rid,'author':'10302 나다은','stance':st[1],'body':{'claim':'그대로 두자','reason':'역사적 의미'},'status':'submitted','createdAt':now,'updatedAt':now}}
    await T.evaluate('d=>localStorage.setItem("__sbmock",JSON.stringify(d))', Dm)
    K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e)))
    await K.goto(U+'?who=anon'); await W(K,500)
    await K.fill('#f-num','10301'); await K.fill('#f-name','김가온'); await K.fill('#f-code',studs['김가온']['code']); await K.press('#f-code','Enter'); await W(K,1300)
    await K.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(K,600)
    print('source open:', await K.evaluate('document.querySelector("details.source")?.open'), '| imgs:', len(await K.query_selector_all('.srcimgs img')), '| link:', await K.eval_on_selector_all('details.source a.autolink','e=>e.map(x=>x.href)'))
    await K.screenshot(path='/tmp/claude-0/smoke/mob/source.png')
    # write own post via savePost then read step
    await K.evaluate(f'(async()=>{{const r=S.rooms.find(x=>x.id==="{rid}"); await savePost(r,{{stance:r.stances[0], body:{{claim:"바꿔야 한다", reason:"피해를 기억"}}, status:"submitted", submittedAt:Date.now()}}); S.work=r.id; S.step[r.id]="read"; render()}})()'); await W(K,800)
    print('step:', await K.evaluate(f'selectedStep(S.rooms.find(x=>x.id==="{rid}"), myPost(S.rooms.find(x=>x.id==="{rid}")))'), '| pick btns:', len(await K.query_selector_all('[data-a=pick-diff]')), '| pad-add:', len(await K.query_selector_all('.pad-add')))
    print('card colors:', await K.eval_on_selector_all('.post.wcard','e=>e.map(x=>x.getAttribute("style"))'))
    await K.click('.wcard:not(.mine) .pad-add'); await W(K,400); await K.keyboard.type('그 의견도 일리가 있어'); await K.click('.pad-cmt [data-a=save-comment]'); await W(K,800)
    me=await K.evaluate(f'myPost(S.rooms.find(x=>x.id==="{rid}"))')
    print('readAt set:', bool(me.get('readAt')), '| meet:', me.get('meet',{}).get('diffPostId'), '| step now:', await K.evaluate(f'selectedStep(S.rooms.find(x=>x.id==="{rid}"), myPost(S.rooms.find(x=>x.id==="{rid}")))'))
    await K.click('[data-a=to-board]') if await K.query_selector('[data-a=to-board]') else None
    await K.evaluate('S.work=null; render()'); await W(K,400); await K.screenshot(path='/tmp/claude-0/smoke/mob/stance_pads.png', full_page=True)
    print('errors', errs); await b.close()
asyncio.run(main())
