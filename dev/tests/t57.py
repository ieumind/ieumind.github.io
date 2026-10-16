# 📊 수행평가 점수 안내: 엑셀 붙여 넣기 → 학생마다 다른 안내 → 학생 예/아니오 → 응답 엑셀(CSV) 받기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}, accept_downloads=True); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-school','한백고'); await T.fill('#roster-add','10301 김가온\n10302 나다은'); await T.click('[data-a=roster-add]'); await W(T,500)
    await T.fill('#roster-school',''); await T.fill('#roster-add','가나고 20105 박하늘'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape'); await W(T)
    st=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']; code={x['name']:x['code'] for x in st}
    await T.click('[data-a=msg-open]'); await W(T,500); await T.click('[data-a=msg-kind][data-v=score]'); await W(T,300)
    print('score form:', await T.eval_on_selector_all('#modal .q > label','e=>e.map(x=>x.innerText.split("\\n")[0])'))
    print('tpl:', await T.input_value('#sc-tpl')); print('ask:', await T.eval_on_selector_all('[data-ask]','e=>e.map(x=>x.value)'))
    print('prev (예시):', await T.inner_text('#sc-prev'))
    await T.click('.scpaste > summary'); await W(T)
    await T.fill('#sc-paste','학번\t이름\t탐구 보고서\t발표\n10301\t김가온\t18\t27\n10302\t나다은\t20\t25\n99999\t없는학생\t1\t1')
    await T.click('[data-a=sc-paste]'); await W(T,400)
    print('paste toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    print('items:', await T.evaluate('scoreF().items'), '| sel:', await T.inner_text('#msg-count'), '| rows:', await T.eval_on_selector_all('.sctbl tbody tr','e=>e.map(x=>x.innerText.trim())'))
    print('prev:', await T.inner_text('#sc-prev'))
    # 박하늘도 골라서 점수 비워 두면 막힘
    await T.fill('#msg-q','박하늘'); await W(T); await T.click('#msg-list input[data-msgsel]'); await W(T,300)
    print('rows now:', len(await T.query_selector_all('.sctbl tbody tr')), '| send label:', await T.inner_text('[data-a=msg-send]'))
    await T.click('[data-a=msg-send]'); await W(T,300); print('empty toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    sid=await T.evaluate('msgRoster().find(x=>x.name==="박하늘").id')
    await T.fill(f'[data-sc="{sid}"][data-i="0"]','15'); await T.fill(f'[data-sc="{sid}"][data-i="1"]','22')
    # 멘트 고치기
    await T.fill('#sc-tpl','안녕하세요. 온라인 공동교육과정 담당 교사입니다. {학생명} 학생 수행평가 점수입니다. {점수} 이의가 있으면 금요일까지 알려 주세요.')
    print('prev edited:', await T.inner_text('#sc-prev'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/sc_compose.png', full_page=False)
    await T.click('[data-a=msg-send]'); await W(T,900)
    print('sent toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    print('push:', [x for x in await T.evaluate('__sbLog') if x.startswith('notify:')][-1:])
    print('badge:', await T.eval_on_selector_all('.mread','e=>e.map(x=>x.innerText)'))
    # 학생: 김가온
    K=await ctx.new_page(); await K.set_viewport_size({'width':390,'height':844}); K.on('pageerror',lambda e:errs.append('K:'+str(e)))
    await K.goto(U+'?who=anon'); await W(K,500); await K.fill('#f-num','10301'); await K.fill('#f-name','김가온'); await K.fill('#f-code',code['김가온']); await K.press('#f-code','Enter'); await W(K,1500)
    print('K pop body:', await K.inner_text('.bm-body'))
    print('K submit disabled:', await K.get_attribute('[data-a=inbox-submit]','disabled') is not None, await K.inner_text('[data-a=inbox-submit]'))
    await K.click('.askq:nth-child(1) [data-b="1"]'); await W(K,150); print('half:', await K.get_attribute('[data-a=inbox-submit]','disabled') is not None)
    await K.click('.askq:nth-child(2) [data-b="1"]'); await W(K,150)
    await K.screenshot(path='/tmp/claude-0/smoke/mob/sc_pop.png')
    await K.click('.askq:nth-child(2) [data-b="0"]'); await W(K,150); await K.click('.askq:nth-child(2) [data-b="1"]'); await W(K,150)   # 바꿨다가 다시 ‘예’
    await K.click('[data-a=inbox-submit]'); await W(K,500)
    print('K after:', await K.evaluate('S.modal?.type||null'), await K.evaluate('document.getElementById("toast")?.textContent'), [x for x in await K.evaluate('__sbLog') if x.startswith('msg_answer')])
    await K.reload(); await W(K,1500); print('K reopen pop:', await K.evaluate('S.modal?.type||null'), '| bar:', (await K.inner_text('.inboxbar')).replace('\n',' '))
    await K.click('.inboxbar'); await W(K,300); print('K list:', (await K.inner_text('#modal')).replace('\n',' | ')[:260])
    await K.screenshot(path='/tmp/claude-0/smoke/mob/sc_list.png'); print('K overflow:', await K.evaluate('document.documentElement.scrollWidth'))
    # 학생 나다은: 열고 닫기(Esc) → 아직 미응답 → 목록에서 답하기
    B=await ctx.new_page(); B.on('pageerror',lambda e:errs.append('B:'+str(e))); await B.goto(U+'?who=anon'); await W(B,500)
    await B.fill('#f-num','10302'); await B.fill('#f-name','나다은'); await B.fill('#f-code',code['나다은']); await B.press('#f-code','Enter'); await W(B,1500)
    print('B body:', await B.inner_text('.bm-body'))
    await B.click('.askq:nth-child(1) [data-b="1"]'); await B.click('.askq:nth-child(2) [data-b="0"]'); await B.click('[data-a=inbox-submit]'); await W(B,500)
    # 선생님: 결과 표 + 엑셀
    await T.click('[data-a=msg-tab][data-v=new]'); await W(T,200); await T.click('[data-a=msg-tab][data-v=sent]'); await W(T,600)
    print('badge after:', await T.eval_on_selector_all('.mread','e=>e.map(x=>x.innerText)'))
    await T.click('.mitem.sc > summary'); await W(T,300)
    print('res rows:', await T.eval_on_selector_all('.scres tbody tr','e=>e.map(x=>[...x.children].map(c=>c.innerText.split("\\n")[0]).join(" | "))'))
    await T.screenshot(path='/tmp/claude-0/smoke/mob/sc_sent.png')
    async with T.expect_download() as dl: await T.click('[data-a=sc-export]')
    d=await dl.value; path=await d.path(); print('file:', d.suggested_filename)
    raw=open(path,'rb').read(); print('bom:', raw[:3]==b'\xef\xbb\xbf'); print(raw.decode('utf-8-sig'))
    print('repush label:', await T.inner_text('.mitem.sc [data-a=msg-repush]'))
    print('errors', errs); await b.close()
asyncio.run(main())
