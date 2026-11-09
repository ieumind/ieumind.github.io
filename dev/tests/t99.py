# 나의 생각 흐름: 활동 단계에 맞는 흐름 문구(모든 유형) · 제목 중복 없음 · 칸 하나면 칸 이름 없음 · 친구 둘러보기 머리 · 긴 쪽지 '전체 보기'
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await c.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.wait_for_timeout(700)
    # 흐름 문구: 모든 유형 × 깊이에서 실제 단계와 맞는지
    bad=await T.evaluate('''(()=>{const bad=[]; const STEPW={read:/친구/, reflect:/돌아보기|생각 변화|다시 생각/, revise:/다시 쓰기|수정한 생각/, compose:/글쓰기/, feedback:/피드백/, back:/발견한 점/, develop:/새로운 질문/, think:/처음 생각|예측/};
      for(const t of Object.keys(TEMPLATES)) for(const d of ["quick","normal","deep"]) for(const v of [{}, {meet:false}, {change:false}, {revise:false,feedback:false}]){
        if(t==="notes"||t==="live") continue;
        const T0=TEMPLATES[t], r={id:"R",template:t,stances:T0.stances||[],features:{...DEPTHS[d].features,...v},depth:d,interact:"comment",reveal:"after"};
        const st=stepsOf(r), s=flowSummaryOf(r);
        for(const [k,re] of Object.entries(STEPW)){ const has=st.includes(k), say=re.test(s); if(k==="think" && t==="essay") continue; if(k==="read" && t==="relay") continue; if(has!==say) bad.push([t,d,JSON.stringify(v),k,has,s]) } }
      return bad})()''')
    ok('흐름 문구가 실제 단계와 일치 (모든 유형)', not bad, bad[:6])
    q=await T.evaluate('flowSummaryOf({id:"R",template:"reflect",stances:[],features:{meet:false,change:false},depth:"quick",fields:[{k:"text",l:"내 생각·느낌"}]})')
    ok('스크린샷 상황(감상·성찰 한 칸)', q=='내 생각', q)
    html=await T.evaluate('''(()=>{const r={id:"R",template:"reflect",stances:[],features:{meet:false,change:false},depth:"quick",anonymous:true,reveal:"after",fields:[{k:"text",l:"내 생각·느낌"}],interact:"comment",open:true};
      const me={id:"m",roomId:"R",author:S.name||"나",body:{text:"ㅇㅇㅇ"},status:"submitted",submittedAt:1,createdAt:1};
      const long="1. 나라가 백성을 제대로 지켜주지 못했다고 느끼며 조선에 대한 실망과 원망을 표현한 말이라고 생각한다\\n2. 독립운동은 일본의 지배에서 벗어나 우리 민족의 자유와 권리를 되찾기 위해 필요했다 독립운동가들의 희생이 있었기에 지금 우리가 자유롭게 살아갈 수 있다고 생각한다 그래서 더 많이 써 본다 더 많이";
      const o1={id:"o1",roomId:"R",author:"친구1",body:{text:long},status:"submitted",submittedAt:1,createdAt:1}, o2={id:"o2",roomId:"R",author:"친구2",body:{text:"짧은 글"},status:"submitted",submittedAt:1,createdAt:1};
      S.posts=[me,o1,o2]; S.replies=[]; window.isMe = window.isMe; 
      return stepRecord(r, me)})()''')
    ok('흐름 카드에 제목 중복 없음', '<h3>' not in html.split('fsum')[0] and '이 활동의 흐름 · 내 생각' in html)
    ok('칸 하나면 칸 이름 없음', '<dt>' not in html)
    ok('친구 둘러보기 머리 정리', 'class="card fsum"' in html and '친구들 생각 둘러보기' in html and '편</span>' in html)
    ok('긴 쪽지에만 전체 보기', html.count('pad-more')==1, html.count('pad-more'))
    await T.evaluate(f'''(()=>{{const d=document.createElement("div"); d.id="X"; d.style.cssText="position:fixed;inset:0;overflow:auto;background:var(--bg);z-index:99999;padding:16px"; d.innerHTML={html!r}; document.body.appendChild(d); d.querySelector("details.fsum").open=true}})()''')
    await T.wait_for_timeout(200); await T.screenshot(path='/tmp/claude-0/shots/t99.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
