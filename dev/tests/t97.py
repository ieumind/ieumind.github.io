# 교사 학생 카드(토론): 입장 모양 색 · 쓴 댓글 수 · 입장 필터/정렬 · 분포 막대 · 한 줄 머리 · '피드백 전'
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
  const P=[{id:"p1",roomId:"R9",author:"김포과학기술고 20114 이서준",stance:r.stances[0],body:{claim:"친일 청산을 우선해야 한다고 생각한다. 과거의 잘못된 역사를 바로잡고, 나라를 위해 희생한 독립운동가들의 노력을 제대로 인정해야 하기 때문이다.",reason:"잘못된 역사를 바로잡아야 하기 때문이다."},createdAt:now-5000,submittedAt:now,readAt:now},
    {id:"p2",roomId:"R9",author:"명지고 20218 유시우",stance:r.stances[1],body:{claim:"나는 반공을 우선",reason:"혼란"},createdAt:now-9000,submittedAt:now},
    {id:"p3",roomId:"R9",author:"태장고 20425 정연수",stance:"엉뚱한 옛 이름",body:{claim:"x",reason:"y"},createdAt:now-9000,submittedAt:now}];
  S.posts=P; S.replies=[{id:"c1",roomId:"R9",postId:"p2",author:"김포과학기술고 20114 이서준",kind:"comment",text:"그것도 중요하지만",createdAt:now},{id:"c2",roomId:"R9",postId:"p3",author:"김포과학기술고 20114 이서준",kind:"comment",text:"음",createdAt:now}];
  window.__r=r; window.__st={all:P,roster:["태장고 20999 미참여"],sub:P};
  const box=document.createElement("div"); box.id="T"; box.style.cssText="position:fixed;inset:0;overflow:auto;background:var(--bg);z-index:99999;padding:16px";
  S.sf="all"; S.ss="no"; S.sview="card";
  box.innerHTML=tabStudents(r,__st); document.body.appendChild(box);
})()'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.wait_for_timeout(700)
    await T.evaluate(SETUP); await T.wait_for_timeout(200)
    col=await T.evaluate('getComputedStyle(document.querySelector("#T article.tcard .chip.st .shp")).color')
    ok('입장 모양이 회색이 아님', col!='rgb(104, 117, 113)', col)
    meta=await T.locator('#T article.tcard .tc-meta').nth(0).inner_text()
    ok('쓴 댓글 수', '쓴 2' in meta and '받은 0' in meta, meta.replace('\n',' '))
    ok('피드백 전', '피드백 전' in meta)
    ok('분포 막대', await T.locator('#T .tdist .dist').count()==1)
    fl=await T.locator('#T .mfilters button').all_inner_texts(); fl=[x.replace('\n',' ') for x in fl]
    ok('입장 필터', any('친일 청산을' in x and '1' in x for x in fl) and any('입장 확인 필요' in x for x in fl), fl)
    ok('입장 확인 표시', await T.locator('#T .tc-warn').count()==1)
    hh=await T.locator('#T article.tcard .tc-h').nth(0).bounding_box(); ok('이름·날짜 한 줄', hh['height']<30, hh)
    ok('상태+단계 한 줄', await T.locator('#T article.tcard .tc-prog .sst').count()==3)
    # sorts
    for k in ['stance','cmt']:
      o=await T.evaluate(f'''(()=>{{S.ss="{k}"; const v=studentView(__r,__st); return v.list.map(e=>e.p?e.p.id:"none")}})()''')
      ok('정렬 '+k, o[-1]=='none' and (o[0]=='p1'), o)
    o=await T.evaluate('''(()=>{S.ss="no"; S.sf="st1"; return studentView(__r,__st).list.map(e=>e.p&&e.p.id)})()'''); ok('입장 필터 동작', o==['p2'], o)
    await T.screenshot(path='/tmp/claude-0/shots/t97.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
