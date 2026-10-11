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
    await T.click('.thead [data-a=create]'); await W(T)
    pressed=lambda: T.evaluate('[...document.querySelectorAll(".depth")].map(x=>x.getAttribute("aria-pressed")==="true"?x.dataset.v:"").join("")')
    stages=lambda: T.eval_on_selector_all('.pv-st','e=>e.map(x=>x.innerText.replace(/\\n/g,": "))')
    await T.click('details[data-keep=adv] > summary'); await W(T)
    secs=lambda: T.eval_on_selector_all('.adv-sec h4','e=>e.map(x=>x.textContent)')
    for d in ['quick','normal','deep']:
      await T.click(f'[data-a=depth][data-v={d}]'); await W(T)
      print(d, 'pressed', await pressed(), '| stages', await stages(), '| adv', await secs())
    print('tools:', await T.eval_on_selector_all('.toolchip b','e=>e.map(x=>x.textContent)'))
    print('react opts:', await T.eval_on_selector_all('#c-react option','e=>e.map(x=>x.textContent)'), '| end:', await T.eval_on_selector_all('#c-end option','e=>e.map(x=>x.textContent)'))
    print('reveal opts:', await T.eval_on_selector_all('#c-reveal option','e=>e.map(x=>x.textContent)'))
    await T.click('#c-initial'); await W(T); print('initial on:', await T.evaluate('S.form.create.initial'), '| stages', await stages())
    await T.click('.toolchip >> text=비교하기'); await W(T); print('tool:', await T.evaluate('S.form.create.tool'), '| adv still open:', await T.evaluate('document.querySelector("details[data-keep=adv]").open'))
    await T.select_option('#c-end','both'); await W(T); print('end both stages', await stages())
    await T.screenshot(path='/tmp/claude-0/smoke/mob/create_new.png', full_page=True)
    # change to normal keeps consistent
    await T.click('[data-a=depth][data-v=normal]'); await W(T); print('normal again stages', await stages(), '| f', await T.evaluate('[S.form.create.change,S.form.create.revise,S.form.create.initial]'))
    await T.fill('#c-prompt','물질은 왜 상태가 바뀔까?'); await T.click('[data-a=create-save]'); await W(T,600)
    rid=await T.evaluate('S.roomId'); r=[v['data'] for v in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs'].values() if v['id']==rid][0]
    print('saved', r['depth'], r['tool'], {k:r['features'][k] for k in ['initial','meet','change','revise']})
    await T.click('[data-a=home]'); await W(T); print('card depth chip:', await T.eval_on_selector_all('.mcard .chip.tpl','e=>e.map(x=>x.textContent)'))
    print('errors', errs); await b.close()
asyncio.run(main())
