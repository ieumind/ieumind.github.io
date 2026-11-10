# 휴대폰 폭에서 글자 잘림·단어 중간 줄바꿈 전수 점검(교사·학생, 단계별)
import asyncio, re, sys
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda pg,ms=300: pg.wait_for_timeout(ms)
SCAN=r"""()=>{
const out=[];const vw=document.documentElement.clientWidth;
const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'};
const desc=e=>(e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(e.className&&typeof e.className==='string'?'.'+e.className.trim().split(/\s+/).join('.'):'')).slice(0,70)+' «'+(e.innerText||'').trim().replace(/\s+/g,' ').slice(0,40)+'»';
document.querySelectorAll('body *').forEach(e=>{
  if(!vis(e)||e.classList.contains('sr')) return; const cs=getComputedStyle(e); const r=e.getBoundingClientRect();
  if(r.right>vw+1 && !(()=>{for(let a=e.parentElement;a&&a!==document.body;a=a.parentElement){const o=getComputedStyle(a).overflowX;if(o==='auto'||o==='scroll')return true}return false})() && cs.position!=='fixed') out.push(['넘침(화면밖)',desc(e),Math.round(r.right)+'>'+vw]);
  const clip=['hidden','clip'].includes(cs.overflowX)||['hidden','clip'].includes(cs.overflow);
  if(clip && e.scrollWidth>e.clientWidth+1 && (e.innerText||'').trim() && cs.textOverflow!=='ellipsis') out.push(['잘림(가로)',desc(e),e.scrollWidth+'>'+e.clientWidth]);
  if(['hidden','clip'].includes(cs.overflowY) && e.scrollHeight>e.clientHeight+2 && (e.innerText||'').trim() && !cs.webkitLineClamp && cs.display!=='-webkit-box') out.push(['잘림(세로)',desc(e),e.scrollHeight+'>'+e.clientHeight]);
});
// 단어 중간 줄바꿈(한글 음절 사이에서 줄이 바뀜)
const hang=/[가-힣]/;
const seen=new Set();
document.querySelectorAll('button,a,label,li,p,span,b,strong,h1,h2,h3,h4,legend,dd,dt,em,small,div').forEach(e=>{
  if(!vis(e)) return;
  for(const n of e.childNodes){ if(n.nodeType!==3) continue; const t=n.textContent; if(t.trim().length<2) continue;
    const rg=document.createRange(); let prevTop=null, prevCh='';
    for(let i=0;i<t.length;i++){ rg.setStart(n,i); rg.setEnd(n,i+1); if(/\s/.test(t[i])){prevCh=' ';continue} const rc=rg.getClientRects()[0]; if(!rc||rc.width===0){continue}
      if(prevTop!==null && rc.top>prevTop+rc.height*0.6 && hang.test(prevCh) && hang.test(t[i])){ const k=desc(e); if(!seen.has(k)){seen.add(k);out.push(['단어 중간 줄바꿈',k,prevCh+'|'+t[i]])} }
      prevTop=rc.top; prevCh=t[i]; }
  }});
return out}"""
async def scan(pg,tag):
  r=await pg.evaluate(SCAN)
  for x in r: print('   ',tag,x)
  ok(f'{tag}: 잘림/단어 끊김 없음', len(r)==0, len(r))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':375,'height':800}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.set_viewport_size({'width':1280,'height':900})
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=tpl][data-v=live]'); await W(T,300)
    await T.fill('#c-prompt','반민특위는 정말 필요했을까?'); await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    await T.set_viewport_size({'width':375,'height':800})
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(nm+':'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1500); return K
    A=await stu('김가온'); B=await stu('나다은'); C=await stu('박서준')
    await A.click('.lvrole.pro'); await W(A,700); await B.click('.lvrole.con'); await W(B,700); await W(C,1500)
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,2500)
    await T.evaluate("document.querySelector('[data-a=lv-team][data-v=jury]')")
    for K,t in ((C,'jury'),):
      pass
    async def sc(label):
      await scan(T,'교사 '+label); await scan(A,'찬성 '+label); await scan(C,'판정단 '+label)
    await sc('대기')
    for st,lab in (('live','토론중'),('ended','토론 종료'),('vote','투표'),('result','결과')):
      await T.click(f'[data-a=lv-state][data-v={st}]'); await W(T,1800)
      if st=='live':
        await A.fill('#lv-input','안녕하세요 이것은 긴 메시지 테스트입니다 한국어 문장이 길게 이어집니다') if await A.locator('#lv-input').count() else None
      await sc(lab)
      await T.screenshot(path=f'/tmp/claude-0/scr/scan_t_{st}.png',full_page=True)
    # 공백 없는 긴 글(학생 채팅) + 다른 화면
    LONG='가나다라마바사아자차카타파하'*6
    await A.evaluate("S.tour=null")
    await T.evaluate('act("lv-state",{dataset:{v:"live"}})'); await W(T,1800)
    if await A.locator('#lv-input').count():
      await A.fill('#lv-input',LONG); await A.keyboard.press('Enter'); await W(A,1200)
      await scan(A,'찬성 긴 글'); await scan(T,'교사 긴 글')
    await T.set_viewport_size({'width':1280,'height':900}); await T.evaluate('location.hash=""'); await W(T,1000)
    await T.set_viewport_size({'width':360,'height':780}); await W(T,600)
    await scan(T,'교사 홈 360')
    await T.evaluate('act("create",{dataset:{}})'); await W(T,600); await scan(T,'만들기 360')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
