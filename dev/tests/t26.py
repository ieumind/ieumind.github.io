import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p22.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto(U+'?demo=1'); await D.evaluate('localStorage.clear()'); await D.reload(); await W(D,900)
    print('demo rooms:', await D.eval_on_selector_all('.mcard h2','e=>e.map(x=>x.textContent.trim())'))
    await D.evaluate('act("open",{dataset:{id:"demo-draw"}})'); await W(D,600)
    print('draw kpis:', (await D.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))[:2])
    await D.click('[data-a=ttab][data-v=students]'); await W(D,400); print('draw imgs in students tab:', len(await D.query_selector_all('#slist img, .sitem img, img')))
    await D.screenshot(path='mob/d_draw.png', full_page=True)
    await D.evaluate('act("open",{dataset:{id:"demo-chat"}})'); await W(D,600)
    await D.click('[data-a=ttab][data-v=students]'); await W(D,400)
    await D.click('[data-a=open-post]'); await W(D,400)
    txt=await D.inner_text('#app'); print('chat transcript shown:', '명령을 처리하는 관리' in txt, '| reflect shown:', '책임이 있다고' in txt)
    await D.screenshot(path='mob/d_chat.png', full_page=True)
    # preview as student for draw
    await D.evaluate('act("open",{dataset:{id:"demo-draw"}})'); await W(D,400); await D.click('[data-a=preview]'); await W(D,500)
    print('student draw board cta:', await D.text_content('.cta b'))
    await D.click('[data-a=preview-exit]'); await W(D)
    # depth options
    await D.click('[data-a=create]'); await W(D)
    for goal,tpl in [('chat',None),('sketch','draw'),('sketch','sketch'),('compare',None),('notes',None)]:
      await D.click(f'[data-a=goal][data-v={goal}]'); await W(D)
      if tpl: await D.click(f'[data-a=tpl][data-v={tpl}]'); await W(D)
      print(goal, tpl, 'depths:', await D.eval_on_selector_all('[data-a=depth]','e=>e.filter(x=>x.checkVisibility()).map(x=>x.dataset.v)'), '| maxp:', (await D.input_value('#c-maxp')) if await D.query_selector('#c-maxp') else '-')
    print('maxp attrs:', await D.evaluate('[document.querySelector("#c-maxp").min, document.querySelector("#c-maxp").max]'))
    # student home label toggle
    S=await ctx.new_page(); S.on('pageerror',lambda e:errs.append('S:'+str(e)))
    await S.goto(U+'?who=teacher'); await W(S,600)
    await S.click('[data-a=roster-open]'); await W(S); await S.fill('#roster-add','10301 김가온'); await S.click('[data-a=roster-add]'); await W(S,400); await S.keyboard.press('Escape')
    code=(await S.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students'][0]['code']
    for prompt,unit,yr in [('토론 주제 하나','근대 · 개항','3차시'),('질문 주제','','')]:
      await S.click('[data-a=create]'); await W(S); await S.fill('#c-prompt',prompt)
      await S.evaluate('document.querySelectorAll("details.adv").forEach(d=>d.open=true)'); await S.fill('#c-subject','한국사'); await S.fill('#c-unit',unit); await S.fill('#c-year',yr)
      await S.click('[data-a=create-save]'); await W(S,500)
    await S.goto(U+'?who=anon'); await W(S,600)
    await S.fill('#f-num','10301'); await S.fill('#f-name','김가온'); await S.fill('#f-code',code); await S.press('#f-code','Enter'); await W(S,1200)
    await S.click('.dcard'); await W(S,400)
    for i in range(5):
      print('label', await S.text_content('.hlbl'), '→', await S.eval_on_selector_all('.scard .subj','e=>e.map(x=>x.textContent)'))
      if i==0: await S.screenshot(path='mob/h_label.png')
      await S.click('.hlbl'); await W(S)
    print('errors', errs); await b.close()
asyncio.run(main())
