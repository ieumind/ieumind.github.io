import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p25.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900})
    await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    print('head:', (await T.inner_text('.thead')).replace('\n',' | ')[:200])
    print('cards:', await T.eval_on_selector_all('.dgrid .dcard .dt','e=>e.map(x=>x.textContent.trim())'), '| chips gone:', not await T.query_selector('.cchips'))
    await T.click('[data-a=create]'); await W(T)
    print('debate placeholder:', await T.get_attribute('#c-prompt','placeholder'))
    print('aisug shown:', bool(await T.query_selector('.aisug')), '| btn:', await T.text_content('[data-a=ai-suggest]'))
    await T.click('[data-a=ai-suggest]'); await W(T); print('empty kw toast:', await T.text_content('#toast'))
    await T.fill('#c-kw','콜럼버스, 원주민'); await T.press('#c-kw','Enter'); await W(T,500)
    print('no key -> modal:', await T.evaluate('S.modal?.type'), '| toast:', await T.text_content('#toast'))
    print('guide link:', await T.get_attribute('.aiguide a','href'), '| status:', (await T.inner_text('#modal')).count('아직 연결되지'))
    await T.fill('#ai-key','short'); await T.click('[data-a=ai-key-save]'); await W(T); print('short toast:', await T.text_content('#toast'))
    await T.fill('#ai-key','AIzaSyTESTKEY_1234567890abcd'); await T.click('[data-a=ai-key-save]'); await W(T,600)
    print('saved toast:', await T.text_content('#toast'), '| ok line:', await T.text_content('.aikey-ok'))
    await T.keyboard.press('Escape'); await W(T)
    await T.click('[data-a=ai-suggest]'); await W(T,500)
    print('items:', await T.eval_on_selector_all('.aisug-item','e=>e.map(x=>x.innerText.replace(/\\n/g," / "))'))
    await T.click('.aisug-item >> nth=0'); await W(T)
    print('prompt:', await T.input_value('#c-prompt'), '| stances:', await T.input_value('#c-st0'), await T.input_value('#c-st1'))
    print('sent:', [x for x in await T.evaluate('__sbLog') if x.startswith('suggest')][-1])
    await T.screenshot(path='mob/ai_create.png', full_page=False)
    # inquiry
    await T.click('[data-a=goal][data-v=question]'); await W(T)
    print('inquiry placeholder:', await T.get_attribute('#c-prompt','placeholder'))
    await T.click('details.help summary >> text=질문 유형 설명 보기'); await W(T)
    print('qtype ex:', await T.eval_on_selector_all('.help-body .muted.small','e=>e.map(x=>x.textContent)'))
    # chat template has no aisug
    await T.click('[data-a=goal][data-v=chat]'); await W(T); print('chat aisug:', bool(await T.query_selector('.aisug')))
    # bad key path
    await T.evaluate('localStorage.setItem("__aikey","BADKEY_123456789012345")')
    await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=ai-suggest]'); await W(T,500)
    print('bad key:', await T.evaluate('S.modal?.type'), await T.text_content('#toast'))
    await T.click('[data-a=ai-key-del]'); await W(T,400); print('after del:', await T.evaluate('S.aiStatus'))
    print('errors', errs); await b.close()
asyncio.run(main())
