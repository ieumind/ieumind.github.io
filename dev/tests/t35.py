import asyncio, re, json
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
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n11005 박서준'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['name']:s for s in (await DB(T))['students']}
    await T.click('.dadd'); await W(T); print('placeholders:', await T.get_attribute('#course-title','placeholder'), '|', await T.get_attribute('#course-subject','placeholder'))
    await T.fill('#course-title','1학년 통합과학'); await T.fill('#course-subject','과학'); await T.click('[data-a=course-save]'); await W(T,700)
    print('auto members modal:', await T.evaluate('S.modal?.type'), '| chips:', await T.eval_on_selector_all('.mchip','e=>e.map(x=>x.textContent.trim())'))
    await T.click('.mchip >> text=1-3'); await W(T); print('after chip:', await T.text_content('#mem-count'), await T.eval_on_selector_all('.mchip','e=>e.map(x=>x.className+":"+x.textContent.trim())'))
    await T.fill('#mem-q','박서'); await W(T); print('search rows:', await T.eval_on_selector_all('.mrow','e=>e.map(x=>x.textContent.trim())'))
    await T.screenshot(path='mob/mem_modal.png')
    await T.click('[data-a=mem-save]'); await W(T,500)
    c1=await T.evaluate('S.mcourse'); print('memline:', (await T.inner_text('.memline')).replace('\n',' '))
    # course 2 with individual pick
    await T.click('[data-a=mcourse][data-v=""]'); await W(T); await T.click('.dadd'); await W(T)
    await T.fill('#course-title','고급 생명과학 온라인 공동교육과정'); await T.click('[data-a=course-save]'); await W(T,700)
    await T.check(f'input[data-mem="{studs["박서준"]["id"]}"]'); await W(T); print('c2 count:', await T.text_content('#mem-count'))
    await T.click('[data-a=mem-save]'); await W(T,500); c2=await T.evaluate('S.mcourse')
    docs=(await DB(T))['docs']; print('members:', docs['courses/'+c1]['data'].get('members'), docs['courses/'+c2]['data'].get('members'))
    # activity in course 1
    await T.click(f'[data-a=mcourse][data-v=""]'); await W(T); await T.click(f'.dcard[data-v="{c1}"]'); await W(T)
    await T.click('.thead [data-a=create]'); await W(T); await T.fill('#c-prompt','기후 위기 대응, 원자력 발전을 늘려야 할까?'); await T.fill('#c-title','원자력 토론')
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    print('notify:', [x for x in await T.evaluate('__sbLog') if x.startswith('notify')])
    await T.click('[data-a=home]'); await W(T); print('card dw:', await T.eval_on_selector_all('.dgrid .dcard .dw','e=>e.map(x=>x.textContent)'))
    print('tiles:', await T.eval_on_selector_all('.tstat','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    await T.click('.tstat.t2'); await W(T,400); print('tile open filter:', await T.evaluate('[S.mf,S.msort]'))
    print('card acts:', await T.eval_on_selector_all('.mcard .macts button','e=>e.map(x=>x.textContent.trim())'))
    await T.screenshot(path='mob/t_home2.png', full_page=True)
    # students
    async def login(num, nm):
      pg=await ctx.new_page(); pg.on('pageerror',lambda e:errs.append(nm+':'+str(e)))
      await pg.goto(U+'?who=anon'); await W(pg,500)
      print(nm, 'gate top has 기록:', bool(await pg.query_selector('#topr [data-a=mine]')))
      await pg.fill('#f-num',num); await pg.fill('#f-name',nm); await pg.fill('#f-code',studs[nm]['code']); await pg.press('#f-code','Enter'); await W(pg,1200)
      print(nm, 'after login 기록:', bool(await pg.query_selector('#topr [data-a=mine]')), '| dcards:', await pg.eval_on_selector_all('.dcard .dt','e=>e.map(x=>x.textContent.trim())'), '| rooms:', await pg.evaluate('S.rooms.map(r=>r.title)'))
      return pg
    G=await ctx.new_page(); await G.set_viewport_size({'width':390,'height':844}); await G.goto(U+'?who=anon'); await W(G,600); await G.screenshot(path='mob/gate_m.png', full_page=True); await G.close()
    P=await login('11005','박서준')
    K=await login('10301','김가온')
    N=await login('10302','나다은')
    # posts: inject submitted posts for 나다은 and 김가온
    st=await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").stances')
    D=await DB(T)
    now=1791718000000
    for pid,nm,sid in [('pN','10302 나다은',studs['나다은']['id']),('pK','10301 김가온',studs['김가온']['id'])]:
      D['docs']['posts/'+pid]={'col':'posts','id':pid,'owner':sid,'data':{'roomId':rid,'author':nm,'stance':st[0],'body':{'claim':nm+'의 주장','reason':'이유'},'status':'submitted','createdAt':now,'updatedAt':now}}
    await T.evaluate('d=>localStorage.setItem("__sbmock",JSON.stringify(d))', D)
    await K.reload(); await W(K,800); await K.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(K,600)
    print('K wall acts:', await K.eval_on_selector_all('.wact','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    print('own heart disabled:', await K.evaluate('[...document.querySelectorAll(".post.mine .hbtn")].map(b=>b.disabled)'))
    await K.click('.wcard:not(.mine) .hbtn'); await W(K,500)
    print('after heart:', await K.eval_on_selector_all('.wcard:not(.mine) .hbtn','e=>e.map(x=>x.className+":"+x.innerText)'))
    await K.click('.wcard:not(.mine) .cbtn'); await W(K,500)
    print('comment focused:', await K.evaluate('document.activeElement?.dataset?.form'))
    await K.keyboard.type('나도 비슷하게 생각했어!'); await K.click('[data-a=save-comment]'); await W(K,600)
    await K.screenshot(path='mob/wall_heart.png', full_page=False)
    reps=[v['data'] for v in (await DB(K))['docs'].values() if v['col']=='replies']
    print('replies:', [(x['kind'],x.get('on'),x.get('text')) for x in reps])
    await K.click('.wcard:not(.mine) .hbtn, .post.open .hbtn'); await W(K,400)
    print('unheart:', [(v['data']['kind'],v['data'].get('on')) for v in (await DB(K))['docs'].values() if v['col']=='replies'])
    await N.reload(); await W(N,800); await N.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(N,600)
    print('N sees own card acts:', await N.eval_on_selector_all('.post.mine .wact','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    # 박서준 cannot see course1 room
    await P.reload(); await W(P,800); print('P rooms:', await P.evaluate('S.rooms.map(r=>r.title)'), '| courses:', await P.evaluate('S.courses.map(c=>c.title)'))
    # auto group
    D=await DB(T); D['docs']['courses/c3']={'col':'courses','id':'c3','owner':None,'data':{'title':'그룹 과목','groups':[{'id':'g13','name':'1학년 3반'},{'id':'g110','name':'1-10'}]}}
    await T.evaluate('d=>localStorage.setItem("__sbmock",JSON.stringify(d))', D); await K.reload(); await W(K,800); await P.reload(); await W(P,800)
    print('auto group K:', await K.evaluate('myGroup("c3")'), '| P:', await P.evaluate('myGroup("c3")'))
    # legacy course guess in teacher
    await T.reload(); await W(T,800); await T.click('.dcard[data-v="c3"]'); await W(T); print('legacy memline:', (await T.inner_text('.memline')).replace('\n',' ')[:80])
    await T.click('[data-a=mem-open]'); await W(T,400); print('guess:', await T.text_content('#mem-count'))
    print('errors', errs); await b.close()
asyncio.run(main())
