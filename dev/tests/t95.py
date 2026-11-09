# 입장 뱃지 모양(이름이 조금 달라도 매칭) · 친구 글에 댓글만 달아도 '친구 생각' 완료
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.wait_for_timeout(600)
    r=await T.evaluate('''(()=>{const r={id:"R",stances:["친일 청산을 우선해야 했다.","국가 건설을 우선해야 했다."]};
      const o={};
      o.a=stanceIdx(r,"친일 청산을 우선해야 했다."); o.b=stanceIdx(r,"친일 청산 우선"); o.c=stanceIdx(r,"국가 건설 먼저"); o.d=stanceIdx(r,"전혀 다른 말"); o.e=stanceChip(r,"친일 청산 우선").includes("shp");
      S.posts=[{id:"P1",roomId:"R",author:"나"},{id:"P2",roomId:"R",author:"친구"}];
      S.replies=[{id:"x",roomId:"R",postId:"P2",author:"나",kind:"comment",text:"좋아"}];
      const rm={id:"R",template:"debate2",features:{meet:true},interact:"comment",stances:r.stances,fields:[]};
      o.read=readDone(rm,S.posts[0]); S.replies=[{id:"y",roomId:"R",postId:"P1",author:"나",kind:"comment"}]; o.self=readDone(rm,S.posts[0]);
      return o})()''')
    print(r)
    ok('정확히 같은 입장', r['a']==0); ok('이름이 바뀐 입장도 같은 입장으로', r['b']==0 and r['e']); ok('두번째 입장', r['c']==1); ok('전혀 다르면 매칭 안 함', r['d']==-1)
    ok('친구 글에 댓글 → 친구 생각 완료', r['read']==True); ok('내 글에 단 댓글은 해당 안 됨', r['self']==False)
    ok('에러 없음', not errs, errs)
  print('FAILS',fails)
asyncio.run(main())
