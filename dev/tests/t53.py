# 함께 보기: 질문별·학생별 보기, 익명 번호, 학생 생각 넘겨 보기 · 학습 나눔: 이름 바뀜, 학생끼리 서로 보기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
IM=['/tmp/claude-0/smoke/imgs/note1.jpg','/tmp/claude-0/smoke/imgs/note2.jpg']
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700)
    # 토론 활동에 단계별 질문 3개 + 학생 8명 넣기
    await D.evaluate('''(()=>{S.tour=null; const r=S.rooms.find(x=>x.id==="park-1965"); r.fields=[{k:"q1",l:"질문1",q:"협정의 내용은 무엇인가요?"},{k:"q2",l:"질문2",q:"당시 한국의 상황은 어땠나요?"},{k:"q3",l:"질문3",q:"나는 어떻게 평가하나요?"}];
      const now=Date.now(); S.posts=S.posts.filter(p=>p.roomId!=="park-1965"); for(let i=0;i<8;i++) S.posts.push({id:"pp"+i, roomId:"park-1965", author:"1030"+i+" 학생"+i, stance:r.stances[i%2], body:{q1:"내용 "+i, q2:i%3? "상황 "+i : "", q3:"평가 "+i}, status:"submitted", createdAt:now-(100-i)*60000, updatedAt:now-(50-i)*60000});
      act("open",{dataset:{id:"park-1965"}}); act("present",{dataset:{id:"park-1965"}})})()'''); await W(D,500)
    print('modes:', await D.eval_on_selector_all('.pmodes button','e=>e.map(x=>x.textContent)'))
    await D.evaluate('act("pmode",{dataset:{v:"thoughts"}})'); await W(D,300)
    print('thoughts page1:', await D.eval_on_selector_all('.pquote .who','e=>e.map(x=>x.textContent.trim().split(" ").slice(0,2).join(" "))'), '| pager:', await D.inner_text('.pnav .mono'))
    await D.keyboard.press('ArrowRight'); await W(D,300); print('thoughts page2:', await D.eval_on_selector_all('.pquote .who','e=>e.map(x=>x.textContent.trim().split(" ").slice(0,2).join(" "))'), await D.inner_text('.pnav .mono'))
    await D.evaluate('act("pmode",{dataset:{v:"byq"}})'); await W(D,300)
    print('byq q1:', await D.inner_text('.pq-q'), '| answers:', len(await D.query_selector_all('.pq-grid .pquote')), '| pager:', await D.inner_text('.pnav .mono') if await D.query_selector('.pnav .mono') else None)
    await D.screenshot(path='/tmp/claude-0/smoke/mob/present_byq.png')
    await D.click('[data-a=pq][data-v="1"]'); await W(D,300); print('byq q2:', await D.inner_text('.pq-q'), '| answers (blank skipped):', len(await D.query_selector_all('.pq-grid .pquote')))
    await D.evaluate('act("pmode",{dataset:{v:"bys"}})'); await W(D,300)
    print('bys cards:', await D.eval_on_selector_all('.pstu-card header b','e=>e.map(x=>x.textContent)'), '| first card:', (await D.inner_text('.pstu-card')).replace('\n',' / ')[:120])
    await D.screenshot(path='/tmp/claude-0/smoke/mob/present_bys.png')
    await D.click('[data-a=pper][data-v="2"]'); await W(D,300); print('bys per2:', len(await D.query_selector_all('.pstu-card')), await D.inner_text('.pnav .mono'))
    # 학습 나눔 이름
    await D.evaluate('act("present-exit",{dataset:{}}); act("create",{dataset:{}})'); await W(D,300)
    print('goal label:', await D.inner_text('[data-a=goal][data-v=notes] b'))
    # 실서비스 흐름: 교사 학습 나눔(서로 보기) → 학생 두 명 업로드 → 서로 보기
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은'); await T.click('[data-a=roster-add]'); await W(T,400); await T.keyboard.press('Escape'); await W(T)
    codes={s['name']:s['code'] for s in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']}
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=notes]'); await W(T)
    print('share select:', await T.eval_on_selector_all('#c-nshare option','e=>e.map(x=>x.textContent+(x.selected?"✓":""))'))
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    print('title:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").title'), '| reveal:', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").reveal'))
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      num='10301' if nm=='김가온' else '10302'
      await K.fill('#f-num',num); await K.fill('#f-name',nm); await K.fill('#f-code',codes[nm]); await K.press('#f-code','Enter'); await W(K,1300)
      await K.set_input_files('input[data-note-file][multiple]', IM[0]); await W(K,1200); await K.click('[data-a=note-submit]'); await W(K,1500); return K
    A=await stu('김가온'); B=await stu('나다은')
    print('B gallery (teacher only):', bool(await B.query_selector('.ngal')))
    await T.click('[data-a=note-share][data-v=after]'); await W(T,600); await W(B,900)
    print('B gallery (shared):', await B.eval_on_selector_all('.ngal .ncard-h b','e=>e.map(x=>x.textContent)'), '| imgs:', await B.evaluate('[...document.querySelectorAll(".ngal img")].filter(i=>i.getAttribute("src")).length'))
    await B.screenshot(path='/tmp/claude-0/smoke/mob/note_share.png', full_page=True)
    await T.click('[data-a=note-share][data-v=teacher]'); await W(T,600); await W(B,900); print('B gallery after closing:', bool(await B.query_selector('.ngal')))
    print('errors', errs); await b.close()
asyncio.run(main())
