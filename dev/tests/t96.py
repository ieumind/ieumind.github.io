# 토론 게시판(생각 지도): 입장 이름 불일치 글도 보임 · 칸 안 카드에 중복 뱃지 없음 · 이름 먼저 · 첫 칸 굵게 · 최신 댓글 · 이동/정렬
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
SETUP='''(()=>{
  const r={id:"R9",template:"debate2",stances:["친일 청산을 우선해야 했다.","반공과 국가 체제 정비를 우선해야 했다."],fields:[{k:"claim",l:"주장"},{k:"reason",l:"근거"}],interact:"comment",reveal:"after",depth:"normal",features:{meet:true,change:false},open:true};
  const now=Date.now();
  const P=[{id:"p1",roomId:"R9",author:"김포과학기술고등학교 20425 이영은",stance:r.stances[0],body:{claim:"나는 친일 청산을 우선해야 한다고 생각한다. 과거의 잘못된 역사를 바로잡고, 나라를 위해 희생한 독립운동가들의 노력을 제대로 인정해야 하기 때문이다.",reason:"잘못된 역사를 바로잡아야 하기 때문이다."},createdAt:now-5000,submittedAt:now},
    {id:"p2",roomId:"R9",author:"명지고 20218 유시우",stance:r.stances[1],body:{claim:"나는 반공과 국가 체제 정비를 우선해야 했다고 생각한다.",reason:"해방 직후 혼란"},createdAt:now-9000,submittedAt:now},
    {id:"p3",roomId:"R9",author:"태장고 20425 정연수",stance:"엉뚱한 옛 입장 이름",body:{claim:"짧은 주장",reason:"이유"},createdAt:now-1000,submittedAt:now}];
  S.posts=P; S.replies=[{id:"c1",roomId:"R9",postId:"p2",author:"태장고 20425 정연수",kind:"comment",text:"그것도 중요하지만 친일파 처벌도 필요해",createdAt:now},{id:"c2",roomId:"R9",postId:"p2",author:"김포과학기술고등학교 20425 이영은",kind:"comment",text:"동의해",createdAt:now+1},{id:"h",roomId:"R9",postId:"p1",author:"x",kind:"heart",on:true}];
  window.__r=r;
  const box=document.createElement("div"); box.id="T96"; box.style.cssText="position:fixed;inset:0;overflow:auto;background:var(--bg);z-index:99999;padding:16px";
  box.innerHTML=stanceMap(r,P,x=>wallCard(r,x,null,P)); document.body.appendChild(box);
})()'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.wait_for_timeout(700)
    await T.evaluate(SETUP); await T.wait_for_timeout(200)
    n=await T.locator('#T96 article.wcard').count(); ok('불일치 입장 글도 보임 (3장)', n==3, n)
    ok('다른 입장 칸', await T.locator('#T96 .smap-col', has_text='다른 입장').count()==1)
    chips=await T.locator('#T96 .smap-col').nth(0).locator('.pad-h .chip.st').count(); ok('입장 칸 안 카드에 중복 뱃지 없음', chips==0, chips)
    ok('불일치 글은 뱃지 유지', await T.locator('#T96 .smap-col', has_text='다른 입장').locator('.pad-h .chip').count()==1)
    nm=await T.locator('#T96 article.wcard .pad-h .who b').nth(0).inner_text(); ok('이름 먼저(굵게)', nm in ('이영은','유시우','정연수'), nm)
    sub=await T.locator('#T96 article.wcard .pad-h .who span').nth(0).inner_text(); ok('학교·학번은 작은 줄', '20' in sub, sub)
    t=await T.locator('#T96 .smap-col').nth(0).locator('.pad-title').count(); ok('긴 주장도 굵은 제목', t==1)
    lr=await T.locator('#T96 .pad-last').count(); txt=await T.locator('#T96 .pad-last').nth(0).inner_text() if lr else ''
    ok('최신 댓글 한 줄 + 모두 보기', lr==1 and '동의해' in txt and '2개' in txt, txt)
    ok('입장 이동 버튼(모바일)', await T.locator('#T96 .smap-j').count()==3 and await T.locator('#T96 .smap-j').nth(0).is_visible())
    ok('정렬 버튼 4개', await T.locator('#T96 .smap-sort button').count()==4)
    await T.screenshot(path='/tmp/claude-0/shots/t96_m.png', full_page=False)
    # 정렬: 댓글 적은 글 → 반대 칸 등 영향 없이 정렬 함수 동작
    order=await T.evaluate('''(()=>{S.mapSort={R9:"heart"}; const h=stanceMap(__r,S.posts,x=>`<i data-x=${x.id}></i>`); return [...h.matchAll(/data-x=(\\w+)/g)].map(m=>m[1])})()''')
    ok('정렬 적용', order==['p1','p2','p3'], order)
    # wide: jump hidden
    await T.set_viewport_size({'width':1280,'height':900}); await T.wait_for_timeout(100)
    ok('넓은 화면에서는 이동 버튼 숨김', not await T.locator('#T96 .smap-j').nth(0).is_visible())
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
