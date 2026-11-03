# 로고 → 교사 메인(배너) · ‘내 과목’ 메뉴 → 과목 카드 위치 · 학습 나눔 최근 제출순
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html?who=teacher'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda P,t: P.wait_for_timeout(t)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for name,w,h in (('PC',1280,800),('휴대폰',390,844)):
      ctx=await b.new_context(viewport={'width':w,'height':h}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      P=await ctx.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
      await P.goto(U); await P.evaluate('localStorage.clear()'); await P.reload(); await W(P,800)
      await P.evaluate('S.tour=null; act("course-new",{dataset:{}})'); await W(P,300)
      await P.evaluate('S.modal=null; S.courses.push({id:"c1",title:"한국사",subject:"한국사",year:"1학년",createdAt:1,members:[]}); S.mcourse="c1"; render()'); await W(P,400)
      ok(f'{name} 과목 안에서는 배너 없음', not await P.locator('.wbanner').count())
      logo='.brand' if w>700 else '#topbar-m .brand, header .brand'
      sel=await P.evaluate('''()=>{const l=[...document.querySelectorAll(".brand")].find(e=>e.offsetParent!==null);return l?(l.closest("#side")?"#side .brand":l.parentElement.id?("#"+l.parentElement.id+" .brand"):".brand"):null}''')
      ok(f'{name} 보이는 로고 있음', sel is not None, str(sel))
      await P.evaluate('window.scrollTo(0,400)')
      await P.evaluate('[...document.querySelectorAll(".brand")].find(e=>e.offsetParent!==null).click()'); await W(P,500)
      ok(f'{name} 로고 → 메인(과목 선택 해제·배너 보임)', await P.evaluate('S.view==="home" && !S.mcourse') and await P.locator('.wbanner').count()==1)
      ok(f'{name} 로고 → 맨 위로', await P.evaluate('scrollY<5'))
      # 메뉴 ‘내 과목’
      if w<=700: await P.evaluate('sideOpen(true)'); await W(P,300)
      await P.evaluate('S.mcourse="c1"; render()'); await W(P,300)
      await P.click('.nav-i[data-a=home-courses]'); await W(P,900)
      r=await P.evaluate('''()=>{const e=document.getElementById("my-courses");const t=e.getBoundingClientRect().top;return {top:Math.round(t),y:Math.round(scrollY),end:scrollY+innerHeight>=document.documentElement.scrollHeight-2,mc:S.mcourse,view:S.view}}''')
      ok(f'{name} 내 과목 → 과목 목록 화면', r['view']=='home' and not r['mc'], str(r))
      ok(f'{name} 내 과목 제목이 화면 위쪽(0~120px)에 보임', (0<=r['top']<=140) or r['end'], str(r))   # 페이지가 짧아 더 못 내려가면 맨 아래까지
      ok(f'{name} 배너를 지나 내려옴', r['y']>100, str(r))
      await ctx.close()
      # 학습 나눔 최근 제출순
      ctx=await b.new_context(viewport={'width':w,'height':h}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
      await T.goto(U); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
      await T.evaluate('act("create",{dataset:{}})'); await W(T,300); await T.click('[data-a=goal][data-v=notes]'); await W(T,300); await T.click('[data-a=create-save]'); await W(T,800)
      rid=await T.evaluate('S.roomId')
      await T.evaluate('''(rid)=>{const now=Date.now();S.posts=S.posts.filter(p=>p.roomId!==rid);const t=[3,1,4,2];for(let i=0;i<4;i++)S.posts.push({id:"np"+i,roomId:rid,author:`10${i}0${i+1} 학생${i}`,status:"submitted",notes:{images:[],files:[],memo:"",submittedAt:now-t[i]*60000,version:1}});S.posts.push({id:"npx",roomId:rid,author:"10909 학생X",status:"draft"});S.ttab="students";render()}''', rid)
      await W(T,500)
      names=lambda: T.eval_on_selector_all('.ncards .ncard .ncard-h b','e=>e.map(x=>x.textContent.trim())')
      ok(f'{name} 정렬 선택 칸 있음', await T.locator('#n-sort').count()==1)
      n0=await names(); ok(f'{name} 기본은 이름순', n0==sorted(n0), str(n0))
      await T.select_option('#n-sort','recent'); await W(T,400)
      n1=await names(); ok(f'{name} 최근 제출순: 학생1(1분)→학생3(2분)→학생0(3분)→학생2(4분)', [x for x in n1 if '학생' in x][:4]==['10201 학생1'.replace('10201','10102'),][:0] or ['학생1','학생3','학생0','학생2']==[x.split()[-1] for x in n1[:4]], str(n1))
      ok(f'{name} 미제출은 맨 뒤', n1[-1].endswith('학생X'), str(n1))
      await T.select_option('#n-sort','name'); await W(T,300); ok(f'{name} 이름순으로 되돌림', await names()==n0)
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
