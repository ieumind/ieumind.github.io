# 체험·휴대폰: 수행평가 점수 안내 → 미리보기 학생 예/아니오 · 휴대폰 교사 화면 넘침
import asyncio, re
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    mc=await b.new_context(viewport={'width':390,'height':844}); await mc.route(re.compile(r'https://.*'), lambda r: r.abort())
    D=await mc.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700); await D.evaluate('S.tour=null; render()'); await W(D)
    await D.click('[data-a=msg-open]'); await W(D,400); await D.click('[data-a=msg-kind][data-v=score]'); await W(D,300)
    await D.click('[data-a=msg-all]'); await W(D,300)
    print('rows:', len(await D.query_selector_all('.sctbl tbody tr')), '| overflow:', await D.evaluate('document.documentElement.scrollWidth'))
    await D.screenshot(path='/tmp/claude-0/smoke/mob/m_sc_compose.png')
    ids=await D.evaluate('MSGF().sel')
    for i,sid in enumerate(ids):
      await D.fill(f'[data-sc="{sid}"][data-i="0"]',str(10+i)); await D.fill(f'[data-sc="{sid}"][data-i="1"]',str(20+i))
    await D.click('[data-a=msg-send]'); await W(D,400); print('demo toast:', await D.evaluate('document.getElementById("toast")?.textContent'))
    print('sent badges:', await D.eval_on_selector_all('.mread','e=>e.map(x=>x.innerText)'))
    await D.click('#modal [data-a=modal-close]'); await W(D)
    await D.evaluate('act("preview-home",{dataset:{}})'); await W(D,500)
    print('preview pop:', await D.inner_text('.bm-body'))
    await D.click('.askq:nth-child(1) [data-b="1"]'); await D.click('.askq:nth-child(2) [data-b="0"]'); await D.click('[data-a=inbox-submit]'); await W(D,300)
    print('after:', await D.evaluate('S.modal?.type||null'), (await D.inner_text('.inboxbar')).replace('\n',' '))
    print('errors', errs); await b.close()
asyncio.run(main())
