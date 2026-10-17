# 가상 인물 대화: ‘AI용 인물 자료’ 칸 · Gemini 초안 버튼(키 없음→연결 창, 키 있음→초안) · 저장된 persona.facts · 체험 예시
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('.thead [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=chat]'); await W(T)
    print('fields:', await T.eval_on_selector_all('#c-pname, #c-pabout, #c-pfacts','e=>e.map(x=>x.id)'))
    await T.click('[data-a=ai-persona]'); await W(T); print('no name toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    await T.fill('#c-pname','여운형'); await T.fill('#c-prompt','1945년 8월 해방 직후, 새 나라를 어떻게 세울 것인가')
    await T.click('[data-a=ai-persona]'); await W(T,600); print('no key → modal:', await T.evaluate('S.modal?.type'))
    await T.keyboard.press('Escape'); await T.evaluate('localStorage.setItem("__aikey","AIzaTESTKEY_abcdefghijklmnopqrstu")')
    await T.click('[data-a=ai-persona]'); await W(T,700)
    print('facts:', repr(await T.input_value('#c-pfacts')))
    print('sent:', [x for x in await T.evaluate('__sbLog') if x.startswith('suggest:')][-1])
    await T.fill('#c-pfacts','- 1945년 8월 15일 건준을 만들었다.'); await T.click('[data-a=ai-persona]'); await W(T,400)
    print('overwrite guard:', await T.evaluate('document.getElementById("toast")?.textContent'), '| kept:', await T.input_value('#c-pfacts'))
    await T.screenshot(path='/tmp/claude-0/smoke/ic/pfacts.png', full_page=False)
    await T.click('[data-a=create-save]'); await W(T,800)
    rid=await T.evaluate('S.roomId'); room=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs']['rooms/'+rid]['data']
    print('saved persona:', room['persona'])
    await T.evaluate(f'act("edit-room",{{dataset:{{id:"{rid}"}}}})'); await W(T,500); print('edit loads facts:', await T.input_value('#c-pfacts'))
    # 체험
    D=await c.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e))); await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700)
    await D.evaluate('S.tour=null; act("create",{dataset:{}})'); await W(D); await D.click('[data-a=goal][data-v=chat]'); await W(D); await D.fill('#c-pname','정조'); await D.click('[data-a=ai-persona]'); await W(D,800)
    print('demo:', (await D.input_value('#c-pfacts'))[:60], '|', await D.evaluate('document.getElementById("toast")?.textContent'))
    M=await c.new_page(); await M.set_viewport_size({'width':390,'height':844}); await M.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(M,700)
    await M.evaluate('S.tour=null; act("create",{dataset:{}})'); await W(M); await M.click('[data-a=goal][data-v=chat]'); await W(M); print('m overflow:', await M.evaluate('document.documentElement.scrollWidth'))
    print('errors', errs); await b.close()
asyncio.run(main())
