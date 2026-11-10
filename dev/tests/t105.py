# 휴대폰(390px)·다크: 타이머 띠 한 줄, 채팅 입력칸 안내 글 잘림 없음
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda pg,ms=300: pg.wait_for_timeout(ms)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=compare]'); await W(T); await T.click('[data-a=tpl][data-v=live]'); await W(T,300)
    await T.fill('#c-prompt','반민특위는 정말 필요했을까?'); await T.click('[data-a=create-save]'); await W(T,900); rid=await T.evaluate('S.roomId')
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(nm+':'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1500); return K
    A=await stu('김가온'); B=await stu('나다은'); C=await stu('박서준')
    await A.click('.lvrole.pro'); await W(A,700); await B.click('.lvrole.con'); await W(B,700); await W(C,2500)
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,1200)
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,900)
    await T.click('.lvr-chip[data-v=close]'); await W(T,900)
    await A.set_viewport_size({'width':390,'height':844}); await A.emulate_media(color_scheme='dark'); await W(A,1500)
    await A.evaluate('render()'); await W(A,600)
    bar=await A.locator('.tmrbar').bounding_box()
    ok('타이머 띠 한 줄(높이 56px 이하)', bar and bar['height']<=56, bar)
    lab=await A.locator('.tmrbar .tmr-l').inner_text()
    ok('‘남은 시간’ 글자는 숨김', '남은 시간' not in lab, lab)
    ok('소리 버튼 아이콘만(글자 숨김)', not await A.locator('.tmrbar .tmr-bt').first.is_visible() and await A.locator('.tmrbar [data-a=tmr-snd]').get_attribute('aria-label') is not None)
    ph=await A.locator('#lv-in').get_attribute('placeholder')
    ok('휴대폰 안내 글 짧게', ph=='우리 팀 주장 정리하기', ph)
    fit=await A.evaluate("""(()=>{const t=document.getElementById('lv-in'); const c=document.createElement('span'); const cs=getComputedStyle(t); c.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;font:'+cs.font; c.textContent=t.placeholder; document.body.appendChild(c); const w=c.offsetWidth; c.remove(); return [w, t.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight)]})()""")
    ok('안내 글이 한 줄에 들어감', fit[0]<=fit[1], fit)
    cnt=await A.locator('#lv-cnt').bounding_box(); ta=await A.locator('#lv-in').bounding_box()
    ok('글자 수는 입력칸 안쪽', cnt['x']>=ta['x'] and cnt['x']+cnt['width']<=ta['x']+ta['width']+1, (cnt,ta))
    await A.evaluate('document.getElementById("lv-in").scrollIntoView({block:"center"})'); await W(A,300)
    await A.screenshot(path='/tmp/claude-0/scr/phone_dark.png')
    await A.evaluate('window.scrollTo(0,0)'); await W(A,200); await A.screenshot(path='/tmp/claude-0/scr/phone_top.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS', fails)
asyncio.run(main())