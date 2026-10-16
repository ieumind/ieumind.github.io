import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p20.html'
IM=['/tmp/claude-0/smoke/imgs/note1.jpg','/tmp/claude-0/smoke/imgs/note2.jpg','/tmp/claude-0/smoke/imgs/note3.jpg']
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900})
    mob=await b.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
    for c in (ctx,mob): await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,600)
    M=lambda pg=T: pg.evaluate('JSON.parse(localStorage.getItem("__sbmock"))')
    STORE=lambda pg=T: pg.evaluate('Object.keys(JSON.parse(localStorage.getItem("__sbstore")||"{}"))')
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은\n10403 박서준'); await T.click('[data-a=roster-add]'); await W(T,400); await T.keyboard.press('Escape')
    codes={s['name']:s['code'] for s in (await M())['students']}
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=notes]'); await W(T)
    print('create: prompt=', (await T.input_value('#c-prompt'))[:20], '| depth visible:', await T.evaluate('document.querySelector(".depth-card").checkVisibility()'), '| maxp:', await T.input_value('#c-maxp'))
    await T.click('[data-a=create-save]'); await W(T,600)
    rid=await T.evaluate('S.roomId'); room=[v['data'] for v in (await M())['docs'].values() if v['id']==rid][0]
    print('room:', room['title'], room['template'], room['reveal'], room.get('noteCfg'))
    print('T view kpis:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'), '| cards:', len(await T.query_selector_all('.ncard')))
    # student A mobile
    A=await ctx.new_page(); await A.set_viewport_size({'width':390,'height':844}); A.on('pageerror',lambda e:errs.append('A:'+str(e)))
    await A.goto(U+'?who=anon#'+rid); await W(A,600)
    await A.fill('#f-num','10301'); await A.fill('#f-name','김가온'); await A.fill('#f-code',codes['김가온']); await A.press('#f-code','Enter'); await W(A,1200)
    print('A view:', await A.text_content('.cta b'), '| tabs?', bool(await A.query_selector('.rtabs')), '| submit disabled:', await A.is_disabled('[data-a=note-submit]'))
    await A.set_input_files('input[data-note-file][multiple]', IM); await W(A,1500)
    print('A drafts:', len(await A.query_selector_all('.nup .nthumb')), '| status:', await A.text_content('.nup .foot [role=status]'))
    first=await A.get_attribute('.nup .nthumb img','src')
    await A.click('.nup .nthumb:nth-child(1) [data-a=note-move]'); await W(A)
    print('A moved: first changed', first != await A.get_attribute('.nup .nthumb img','src'))
    await A.click('.nup .nthumb:nth-child(3) [data-a=note-rm]'); await W(A); print('A after remove:', len(await A.query_selector_all('.nup .nthumb')))
    await A.click('.nup .nthumb:nth-child(1) .nzoom'); await W(A); print('A preview modal:', await A.text_content('.lb-h')); await A.screenshot(path='mob/n2_preview.png')
    await A.click('#modal [data-a=modal-close]'); await W(A)
    await A.fill('textarea[id="note:%s-memo"]'%rid, '3·1 운동은 전국으로 퍼졌다')
    await A.screenshot(path='mob/n1_student_draft.png', full_page=True)
    await A.click('[data-a=note-submit]'); await W(A,1500)
    print('A after submit:', await A.text_content('.cta b'), '|', await A.text_content('.cta span'), '| own thumbs:', len(await A.query_selector_all('.nsub .nthumb img')))
    await A.screenshot(path='mob/n3_student_done.png', full_page=True)
    post=[v['data'] for v in (await M(A))['docs'].values() if v['col']=='posts'][0]
    print('  post:', post['status'], len(post['notes']['images']), post['notes']['images'][0]['p'][:30], post['notes']['memo'], '| store files:', len(await STORE(A)))
    # student B camera
    B=await ctx.new_page(); await B.set_viewport_size({'width':390,'height':844}); B.on('pageerror',lambda e:errs.append('B:'+str(e)))
    await B.goto(U+'?who=anon#'+rid); await W(B,600)
    await B.fill('#f-num','10302'); await B.fill('#f-name','나다은'); await B.fill('#f-code',codes['나다은']); await B.press('#f-code','Enter'); await W(B,1200)
    await B.set_input_files('input[data-note-file][capture]', IM[2]); await W(B,800); await B.click('[data-a=note-submit]'); await W(B,1200)
    print('B:', await B.text_content('.cta b'))
    sec=await B.evaluate('''(async()=>{ const sidA = Object.values(JSON.parse(localStorage.getItem("__sbmock")).students).find(s=>s.name==="김가온").id;
       const r = await SB.storage.from("notes").upload("%s/"+sidA+"/hack.jpg", new Blob(["x"],{type:"image/jpeg"})); 
       const s = await SB.storage.from("notes").createSignedUrls(["%s/"+sidA+"/x.jpg"], 60); return {upload:!!r.error, sign: s.data[0].signedUrl}})()'''%(rid,rid))
    print('B security (into A folder):', sec)
    # teacher
    await T.reload(); await W(T,900); await T.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,1200)
    print('T kpis:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    print('T cards:', await T.eval_on_selector_all('.ncard','e=>e.map(x=>x.querySelector(".ncard-h").innerText.replace(/\\n/g," ")+" imgs:"+x.querySelectorAll("img").length)'))
    print('T classes:', await T.eval_on_selector_all('#n-cls option','e=>e.map(x=>x.textContent)'))
    await T.click('[data-a=note-filter][data-v=none]'); await W(T); print('T 미제출:', await T.eval_on_selector_all('.ncard b','e=>e.map(x=>x.textContent)'))
    await T.click('[data-a=note-filter][data-v=all]'); await W(T)
    await T.screenshot(path='mob/n4_teacher.png', full_page=True)
    await T.click('.ncard:has-text("김가온") [data-a=note-view]'); await W(T,600)
    print('T viewer:', await T.text_content('.lb-h'), '| img:', bool(await T.query_selector('.lb-img img')))
    await T.click('[data-a=note-nav][data-d="1"]'); await W(T); print('  next:', await T.text_content('.lb-h .muted'))
    await T.screenshot(path='mob/n5_viewer.png')
    await T.click('#modal [data-a=note-req]'); await W(T); await T.fill('#nreq-msg','두 번째 쪽이 흐려요. 다시 찍어 주세요.'); await T.click('[data-a=note-req-send]'); await W(T,500)
    print('T req push:', [x for x in await T.evaluate('__sbLog') if x.startswith('notify:')][-1:], '| toast:', await T.evaluate('document.getElementById("toast")?.textContent'))
    print('T after req:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    # A resubmit
    await A.reload(); await W(A,1200)
    print('A sees req:', await A.text_content('.cta b'), '|', await A.text_content('.cta span'), '| uploader:', bool(await A.query_selector('.nup')))
    await A.set_input_files('input[data-note-file][multiple]', IM[1]); await W(A,800); await A.click('[data-a=note-submit]'); await W(A,1500)
    post=[v['data'] for v in (await M(A))['docs'].values() if v['col']=='posts' and v['data']['author'].endswith('김가온')][0]
    print('A resubmitted:', await A.text_content('.cta span'), '| version', post['notes']['version'], '| req', post.get('resubmitReq'), '| store files', len(await STORE(A)))
    # home
    await A.click('[data-a=home]'); await W(A); print('A todolist:', await A.inner_text('.todolist') if await A.query_selector('.todolist') else '-'); await A.click('.dcard'); await W(A); print('A home card:', await A.text_content('.scard .sst'))
    await T.reload(); await W(T,900); await T.evaluate(f'act("open",{{dataset:{{id:"{rid}"}}}})'); await W(T,1000)
    print('T final kpis:', await T.eval_on_selector_all('.kpi','e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    await T.click('[data-a=note-dup]'); await W(T,800)
    f=await T.evaluate('S.form.create'); print('T dup -> view', await T.evaluate('S.view'), '| template', f['template'], '| title', repr(f.get('title')), '| prompt', f['prompt'][:15], '| editId', bool(f.get('editId')))
    print('errors', errs); await b.close()
asyncio.run(main())
