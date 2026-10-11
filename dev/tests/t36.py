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
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n10401 다솜\n11005 박서준'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    studs={s['name']:s for s in (await DB(T))['students']}
    await T.click('.dadd'); await W(T,500)
    print('modal sections:', await T.eval_on_selector_all('#modal .cm-h b','e=>e.map(x=>x.textContent)'))
    await T.fill('#course-title','1학년 통합과학'); await T.fill('#course-subject','과학')
    await T.click('.mchip >> text=1-3'); await T.click('.mchip >> text=1-4'); await W(T)
    print('count:', await T.text_content('#mem-count'))
    await T.click('[data-a=course-gsplit]'); await W(T,300)
    print('groups:', await T.eval_on_selector_all('#modal .grow input[data-k^="gn:"]','e=>e.map(x=>x.value)'), await T.eval_on_selector_all('#modal .grow .pill','e=>e.map(x=>x.textContent)'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/cm_modal.png')
    await T.click('[data-a=course-save]'); await W(T,700); cid=await T.evaluate('S.mcourse')
    c=(await DB(T))['docs']['courses/'+cid]['data']; print('saved members', len(c['members']), 'groups', [(g['name'], len(g.get('members',[]))) for g in c['groups']])
    await T.screenshot(path='/tmp/claude-0/smoke/mob/chead.png', full_page=True)
    print('chead acts:', await T.eval_on_selector_all('.chead-acts button','e=>e.map(x=>x.textContent.trim())'), '| notice open:', await T.evaluate('document.querySelector(".tnotice").open'))
    await T.click('.tnotice > summary'); await W(T); print('notice open after click:', await T.evaluate('document.querySelector(".tnotice").open'), '| toggle:', await T.text_content('.tgl'))
    # activity assigned to group 1-4 only
    await T.click('.thead [data-a=create]'); await W(T)
    print('depth cards:', await T.eval_on_selector_all('.depth','e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    await T.click('[data-a=depth][data-v=normal]'); await W(T); print('normal flow:', (await T.inner_text('.pv-stages')).replace('\n',' '))
    await T.click('[data-a=depth][data-v=deep]'); await W(T); print('deep flow:', (await T.inner_text('.pv-stages')).replace('\n',' '))
    await T.click('[data-a=depth][data-v=quick]'); await W(T); print('quick flow:', (await T.inner_text('.pv-stages')).replace('\n',' '))
    await T.click('[data-a=depth][data-v=normal]'); await W(T)
    await T.screenshot(path='/tmp/claude-0/smoke/mob/depth.png')
    await T.fill('#c-prompt','물질의 상태 변화는 왜 일어날까?'); await T.fill('#c-title','상태 변화')
    g14=[g['id'] for g in c['groups'] if g['name']=='1-4'][0]
    await T.evaluate(f'(()=>{{const f=S.form.create; f.groups=["{g14}"]}})()')
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    print('room assign:', list((await DB(T))['docs']['rooms/'+rid]['data'].get('assign',{}).keys()), 'g14', g14)
    await T.click('[data-a=ttab][data-v=progress]'); await W(T,500)
    print('kpis:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    await T.click('[data-a=home]'); await W(T,400)
    print('card tools:', await T.eval_on_selector_all('.mcard .mctools button','e=>e.map(x=>x.textContent.trim())'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/thome3.png', full_page=True)
    # students
    async def login(num, nm):
      pg=await ctx.new_page(); pg.on('pageerror',lambda e:errs.append(nm+':'+str(e)))
      await pg.goto(U+'?who=anon'); await W(pg,500)
      await pg.fill('#f-num',num); await pg.fill('#f-name',nm); await pg.fill('#f-code',studs[nm]['code']); await pg.press('#f-code','Enter'); await W(pg,1300)
      return pg
    for num,nm in [('10301','김가온'),('10401','다솜'),('11005','박서준')]:
      pg=await login(num,nm)
      print(nm, 'mySids', await pg.evaluate('[...(S.mySids||[])].length'), '| group', await pg.evaluate(f'myGroup("{cid}")'), '| dcards', await pg.eval_on_selector_all('.dcard .dt','e=>e.map(x=>x.textContent.trim())'), '| todo', await pg.eval_on_selector_all('.todolist b','e=>e.map(x=>x.textContent)'))
      if nm=='다솜': await pg.screenshot(path='/tmp/claude-0/smoke/mob/sdash.png', full_page=True)
    # edit keeps
    await T.evaluate(f'(()=>{{S.mcourse="{cid}";render()}})()'); await W(T); await T.click('.chead-acts [data-focus=students]'); await W(T,500)
    print('edit modal sel:', await T.text_content('#mem-count'), '| selects:', await T.eval_on_selector_all('select[data-memg]','e=>e.filter(x=>!x.disabled).map(x=>x.selectedOptions[0].textContent)'))
    print('errors', errs); await b.close()
asyncio.run(main())
