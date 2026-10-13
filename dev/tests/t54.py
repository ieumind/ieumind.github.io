# 함께 보기 1~3명·이름 보기 · 개요의 단계별 질문 상자·다음 진행 제안(초록 상자 없앰) · 첫 화면 인물 예시
import asyncio, re
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    D=await ctx.new_page(); D.on('pageerror',lambda e:errs.append('D:'+str(e)))
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html'); await W(D,700)
    print('welcome:', [t for t in await D.eval_on_selector_all('p','e=>e.map(x=>x.innerText)') if '연기' in t][:1])
    await D.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(D,700)
    await D.evaluate('''(()=>{S.tour=null; const r=S.rooms.find(x=>x.id==="park-1965"); r.fields=[{k:"q1",l:"질문1",q:"협정의 내용은 무엇인가요?",h:"자료 1을 보세요"},{k:"q2",l:"질문2",q:"당시 한국의 상황은 어땠나요?"},{k:"q3",l:"질문3",q:"나는 어떻게 평가하나요?"}];
      const now=Date.now(); S.posts=S.posts.filter(p=>p.roomId!=="park-1965"); for(let i=0;i<5;i++) S.posts.push({id:"pp"+i, roomId:"park-1965", author:"1030"+i+" 학생"+i, stance:r.stances[i%2], body:{q1:"내용 "+i, q2:"상황 "+i, q3:"평가 "+i}, status:"submitted", createdAt:now-(100-i)*60000, updatedAt:now-(50-i)*60000});
      act("open",{dataset:{id:"park-1965"}})})()'''); await W(D,500)
    print('green box gone:', not await D.query_selector('.hintcard'), '| next hint:', await D.inner_text('.nexthint') if await D.query_selector('.nexthint') else None)
    print('overview label:', await D.inner_text('.tabbody .card .eyebrow >> nth=-1') if False else await D.evaluate('[...document.querySelectorAll(".tabbody .eyebrow")].map(x=>x.textContent)'), '| sqbox:', (await D.inner_text('.sqbox')).replace('\n',' / '))
    await D.evaluate('''(()=>{const c=document.querySelector(".sqbox"); c.scrollIntoView({block:"center"})})()'''); await W(D,200); await D.screenshot(path='/tmp/claude-0/smoke/mob/ov_sqbox.png')
    await D.evaluate('act("present",{dataset:{id:"park-1965"}}); act("pmode",{dataset:{v:"bys"}})'); await W(D,300)
    print('pper opts:', await D.eval_on_selector_all('[data-a=pper]','e=>e.map(x=>x.textContent)'))
    await D.click('[data-a=pper][data-v="1"]'); await W(D,300); print('1 per page:', len(await D.query_selector_all('.pstu-card')), await D.inner_text('.pnav .mono'))
    print('names off:', await D.eval_on_selector_all('.pstu-card header b','e=>e.map(x=>x.textContent)'))
    await D.click('[data-a=pnames]'); await W(D,300); print('names on:', await D.eval_on_selector_all('.pstu-card header b','e=>e.map(x=>x.textContent)'), '| btn:', await D.inner_text('[data-a=pnames]'))
    await D.screenshot(path='/tmp/claude-0/smoke/mob/present_1.png')
    await D.evaluate('act("pmode",{dataset:{v:"byq"}})'); await W(D,300); print('byq names:', await D.eval_on_selector_all('.pq-grid .who','e=>e.map(x=>x.textContent.trim().split(" ").slice(0,2).join(" "))'))
    await D.click('[data-a=pnames]'); await W(D,300); print('byq anon:', await D.eval_on_selector_all('.pq-grid .who','e=>e.map(x=>x.textContent.trim().split(" ").slice(0,2).join(" "))'))
    print('errors', errs); await b.close()
asyncio.run(main())
