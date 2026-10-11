import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p23.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T)
    flow=lambda: T.text_content('.preview-steps .flowline')
    print('default flow:', (await flow()).replace('\n',' '))
    await T.click('details[data-keep=adv] > summary'); await W(T)
    print('options:', await T.eval_on_selector_all('details[data-keep=adv] label[for], details[data-keep=adv] .feat > label','e=>e.map(x=>x.textContent.trim().slice(0,14))'))
    print('combos now:', await T.evaluate('["start","react","end"].map(k=>document.querySelector("[data-combo="+k+"]").value)'), await T.is_checked('#c-evid'))
    for sel,val in [('#c-start','predict'),('#c-react','none'),('#c-end','both')]:
      await T.select_option(sel,val); await W(T)
      print(f'after {sel}={val}: open=', await T.evaluate('document.querySelector("details[data-keep=adv]").open'), '| flow:', (await flow()).replace('\n',' '))
    await T.click('#c-evid'); await W(T); print('evidence on: open=', await T.evaluate('document.querySelector("details[data-keep=adv]").open'), '| types shown:', len(await T.query_selector_all('[data-k=evidenceTypes]')), '| flags:', await T.evaluate('(f=>[f.evidenceType,f.warrant,f.terms])(S.form.create)'))
    await T.click('#c-anonymous'); await W(T); print('checkbox change: open=', await T.evaluate('document.querySelector("details[data-keep=adv]").open'))
    await T.click('details[data-keep=info] > summary'); await W(T); await T.select_option('#c-grade','중2'); await W(T)
    print('info stays open:', await T.evaluate('document.querySelector("details[data-keep=info]").open'))
    await T.click('[data-a=depth][data-v=quick]'); await W(T); print('quick depth combos:', await T.evaluate('["start","react","end"].map(k=>document.querySelector("[data-combo="+k+"]").value)'), '| flow:', (await flow()).replace('\n',' '))
    await T.click('[data-a=depth][data-v=deep]'); await W(T); print('deep depth combos:', await T.evaluate('["start","react","end"].map(k=>document.querySelector("[data-combo="+k+"]").value)'), await T.is_checked('#c-evid'))
    await T.fill('#c-prompt','시험 논제'); await T.click('[data-a=create-save]'); await W(T,500)
    rid=await T.evaluate('S.roomId'); room=[v['data'] for v in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs'].values() if v['id']==rid][0]
    print('saved:', room['depth'], room['interact'], {k:room['features'][k] for k in ['initial','predict','meet','change','revise','evidenceType','warrant','counter','terms']})
    print('errors', errs); await b.close()
asyncio.run(main())
