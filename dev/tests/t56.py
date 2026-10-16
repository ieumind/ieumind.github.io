# 체험: 개별 안내 보내기 → 학생 화면 미리보기에서 크게 뜸 · 포트폴리오에서 이 학생에게 · 휴대폰 교사 화면
import asyncio, re
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    mc=await b.new_context(viewport={'width':390,'height':844}); await mc.route(re.compile(r'https://.*'), lambda r: r.abort())
    D=await mc.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700); await D.evaluate('S.tour=null; render()'); await W(D)
    print('m overflow home:', await D.evaluate('document.documentElement.scrollWidth'))
    await D.screenshot(path='/tmp/claude-0/smoke/mob/m_thead_msg.png')
    await D.click('[data-a=msg-open]'); await W(D,400)
    print('demo list n:', len(await D.query_selector_all('#msg-list .mrow')), '| push toggle:', bool(await D.query_selector('#msg-push')))
    await D.click('[data-a=msg-tab][data-v=sent]'); await W(D); print('seed sent:', await D.eval_on_selector_all('.mread','e=>e.map(x=>x.textContent)'))
    await D.click('[data-a=msg-tab][data-v=new]'); await W(D)
    await D.fill('#msg-q','김가온'); await W(D); await D.click('[data-a=msg-all]'); await W(D); print('sel:', await D.inner_text('#msg-count'))
    await D.fill('#msg-body','체험 안내입니다'); await D.click('[data-a=msg-send]'); await W(D,400)
    print('demo toast:', await D.evaluate('document.getElementById("toast")?.textContent'))
    print('m modal overflow:', await D.evaluate('document.documentElement.scrollWidth'))
    await D.screenshot(path='/tmp/claude-0/smoke/mob/m_msg_sent.png')
    await D.click('#modal [data-a=modal-close]'); await W(D)
    await D.evaluate('act("preview-home",{dataset:{}})'); await W(D,500)
    print('preview pop:', await D.evaluate('S.modal?.type'), (await D.inner_text('.bigmsg')).replace('\n',' | '))
    await D.click('[data-a=inbox-ok]'); await W(D); print('bar:', (await D.inner_text('.inboxbar')).replace('\n',' '))
    await D.evaluate('act("preview-exit",{dataset:{}})'); await W(D,300)
    # 포트폴리오 → 이 학생에게
    pc=await b.new_context(viewport={'width':1280,'height':900}); await pc.route(re.compile(r'https://.*'), lambda r: r.abort())
    P=await pc.new_page(); P.on('pageerror',lambda e:errs.append('P:'+str(e)))
    await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(P,700); await P.evaluate('S.tour=null; act("mcourse",{dataset:{v:"c-demo"}})'); await W(P,400)
    await P.click('.cport > summary'); await W(P,400); await P.click('.cport-t tbody tr:nth-child(2) [data-a=port-student]'); await W(P,300)
    who=await P.inner_text('#modal h3'); await P.click('#modal [data-a=msg-open]'); await W(P,300)
    print('port →', who[:20], '| preselected:', await P.evaluate('MSGF().sel'), await P.inner_text('#msg-count'))
    print('errors', errs); await b.close()
asyncio.run(main())
