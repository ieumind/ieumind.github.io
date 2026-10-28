# 내 생각 기록: 지도로 보기(가운데 = 과목) · 목록 전환 · 필터 · 쪽 넘기기 · 전체화면
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
SEED='''(()=>{
  const now=Date.now(), day=864e5; S.name="김가온"; S.myNames=new Set(["김가온"]);
  S.courses=[{id:"c1",title:"1학년 한국사"},{id:"c2",title:"통합과학"}];
  const mk=(i,c,t,deg,st0,st1,age)=>{ const id="r"+i; S.rooms.push({id,title:t,year:"1학년",subject:c==="c1"?"한국사":c==="c2"?"과학":"",courseId:c,template:"debate2",stances:["찬성","반대"],status:"open",createdAt:now-age*day,context:i==0?"자료: 교과서 12쪽을 읽고 오세요. https://example.com/a":"",ctxImgs:[]});
    S.posts.push({id:"p"+i,roomId:id,author:"김가온",stance:st1,initial:{stance:st0,claim:"처음에는 "+st0+"이라고 생각했다"},body:{claim:t+"에 대한 내 생각",reason:"교과서에서 읽은 근거"},evidenceType:"교과서",change:deg?{degree:deg,now:"지금은 "+st1+"에 가깝다. 이유는 친구 글을 읽고 달라졌기 때문이다.",nowStance:st1,biggest:"친구의 근거"}:null,status:"submitted",createdAt:now-age*day}); };
  // 한국사 11개(두 쪽): 입장 바뀜 / 깊어짐 / 유지 / 정리 전
  for(let i=0;i<11;i++){ mk(i,"c1",["3·1 운동의 의미","갑오개혁 평가","흥선대원군의 정책","동학농민운동의 성격","개항의 영향","독립협회 활동","의병과 애국계몽","물산장려운동","6·10 만세","광복군 활동","대한민국 임시정부"][i], i%4===0?"much":i%4===1?"some":i%4===2?"little":null, "찬성", i%4===0?"반대":"찬성", i*9+1); }
  mk(20,"c2","빛의 성질 토론","some","찬성","찬성",3); mk(21,"c2","기후 위기 대응","much","찬성","반대",5); mk(22,"","자유 주제 글쓰기","little","찬성","찬성",2);
  S.view="mine"; render();
})()'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=200: pg.wait_for_timeout(ms)
    for name,w,h in (('PC',1280,900),('휴대폰',390,844)):
      c=await b.new_context(viewport={'width':w,'height':h}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); P=await c.new_page(); P.on('pageerror',lambda e:errs.append(f'{name}:'+str(e)))
      await P.goto(U+'?who=anon'); await P.evaluate('localStorage.clear()'); await P.reload(); await W(P,600)
      await P.evaluate(SEED); await W(P,300)
      view=await P.evaluate('mineView()')
      ok(f'{name} 기본 보기: PC는 지도, 휴대폰은 목록', view==('map' if w>700 else 'list'), view)
      if w<=700: await P.click('[data-a=mine-view][data-v=map]'); await W(P,300)
      ok(f'{name} 지도: 가운데 = 과목(가장 최근 활동 과목)', '1학년 한국사' in await P.inner_text('.mmap-c') or '통합과학' in await P.inner_text('.mmap-c'), await P.inner_text('.mmap-c'))
      sel=await P.evaluate('[...document.querySelectorAll("#mine-crs option")].map(o=>o.textContent.trim())')
      ok(f'{name} 과목 선택에 3개 묶음(과목 없는 활동 포함)', len(sel)==3 and any('과목 없는 활동' in x for x in sel), str(sel))
      await P.select_option('#mine-crs','c1'); await W(P,300)
      ok(f'{name} 한 화면에 8개 노드', await P.evaluate('document.querySelectorAll(".mmap-n").length')==8)
      ok(f'{name} 오른쪽 목록은 11개 전부', await P.evaluate('document.querySelectorAll(".mmap-li").length')==11)
      ok(f'{name} 쪽 표시 1/2', '1 / 2' in await P.inner_text('.mmap-pg'))
      tones=await P.evaluate('[...new Set([...document.querySelectorAll(".mmap-n")].map(n=>[...n.classList].find(c=>c.startsWith("t-"))))].sort().join()')
      ok(f'{name} 변화 색 구분(입장 바뀜·깊어짐·유지·정리 중)', tones=='t-deep,t-keep,t-moved,t-wip', tones)
      ok(f'{name} 입장이 바뀐 노드는 테두리 두 겹(two)', await P.evaluate('document.querySelectorAll(".mmap-n.two").length')>=1)
      ok(f'{name} 범례', '입장이 바뀜' in await P.inner_text('.mmap-lg') and '테두리 두 겹' in await P.inner_text('.mmap-lg'))
      # 겹침 없음
      ov=await P.evaluate('(()=>{const r=[...document.querySelectorAll(".mmap-n,.mmap-c")].map(e=>e.getBoundingClientRect());let n=0;for(let i=0;i<r.length;i++)for(let j=i+1;j<r.length;j++){const a=r[i],b=r[j];if(a.left<b.right-2&&b.left<a.right-2&&a.top<b.bottom-2&&b.top<a.bottom-2)n++}return n})()')
      ok(f'{name} 노드끼리·가운데와 겹치지 않음', ov==0, str(ov))
      await P.screenshot(path=f'/tmp/claude-0/smoke/t80_{name}.png')
      # 노드를 누르면 아래 상세 + 목록 강조
      await P.click('.mmap-n >> nth=1'); await W(P,400)
      ttl=await P.evaluate('document.querySelector(".mmap-n[aria-pressed=true] b").textContent')
      ok(f'{name} 노드를 누르면 아래에 그 활동 상세', ttl in await P.inner_text('.mmap-dt') and '① ' in await P.inner_text('#mmap-detail') and '지금의 생각' in await P.inner_text('#mmap-detail'), ttl)
      ok(f'{name} 목록에서도 같은 활동이 표시됨', await P.evaluate('document.querySelector(".mmap-li[aria-current=true] .li-t").textContent')==ttl)
      # 목록에서 2쪽 활동 고르면 그 쪽으로
      await P.click('.mmap-li >> nth=10'); await W(P,500)
      ok(f'{name} 목록에서 다른 쪽 활동을 고르면 그 쪽으로 넘어감', '2 / 2' in await P.inner_text('.mmap-pg'))
      ok(f'{name} 2쪽에는 노드 3개', await P.evaluate('document.querySelectorAll(".mmap-n").length')==3)
      await P.click('[data-a=mine-page][data-d="-1"]'); await W(P,300); ok(f'{name} 더 최근 쪽으로', '1 / 2' in await P.inner_text('.mmap-pg'))
      # 자료
      await P.click('.mmap-li >> nth=0'); await W(P,300)
      mats=await P.inner_text('.mmap-side .mmap-box:nth-of-type(2)') if False else await P.inner_text('.mmap-side')
      # 필터
      await P.select_option('#mine-f','changed'); await W(P,300)
      n=await P.evaluate('document.querySelectorAll(".mmap-li").length'); ok(f'{name} 필터: 달라진 것만', 0<n<11, str(n))
      await P.select_option('#mine-f','kept'); await W(P,300)
      ok(f'{name} 필터: 유지한 것만', await P.evaluate('[...document.querySelectorAll(".mmap-n")].every(n=>n.classList.contains("t-keep"))'))
      await P.select_option('#mine-f','all'); await W(P,200)
      # 과목 바꾸기
      await P.select_option('#mine-crs','c2'); await W(P,300)
      ok(f'{name} 다른 과목으로 바꾸면 가운데·노드가 바뀜', '통합과학' in await P.inner_text('.mmap-c') and await P.evaluate('document.querySelectorAll(".mmap-n").length')==2)
      # 전체화면
      await P.click('[data-a=mine-fs]'); await W(P,300)
      ok(f'{name} 전체화면', await P.evaluate('getComputedStyle(document.querySelector(".mmapwrap")).position')=='fixed')
      await P.keyboard.press('Escape'); await W(P,300)
      ok(f'{name} Esc로 전체화면 닫힘', await P.evaluate('getComputedStyle(document.querySelector(".mmapwrap")).position')!='fixed')
      # 목록으로 보기
      await P.click('[data-a=mine-view][data-v=list]'); await W(P,300)
      ok(f'{name} 목록으로 보기 전환(기존 카드)', await P.evaluate('document.querySelectorAll("details.pcard").length')>=14, str(await P.evaluate('document.querySelectorAll("details.pcard").length')))
      await P.click('details.pcard summary >> nth=0'); await W(P,200)
      ok(f'{name} 목록 카드 펼침 내용 그대로', '① ' in await P.inner_text('details.pcard[open] .pbody') and '선생님 피드백' in await P.inner_text('details.pcard[open] .pbody'))
      await P.reload(); await W(P,600); await P.evaluate(SEED)
      ok(f'{name} 고른 보기 방식이 기억됨', await P.evaluate('mineView()')=='list')
      await c.close()
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
