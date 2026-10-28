# 수업 타이머: 끝나면 소리(띵동), 한 번만, 소리 끄기
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
HOOK='''window.__osc=0; window.__vib=0;
const AC=function(){ this.state="running"; this.currentTime=0; this.destination={}; this.resume=()=>{}; this.createGain=()=>({gain:{setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}}); this.createOscillator=()=>({frequency:{},connect(){},start(){window.__osc++},stop(){}}) };
window.AudioContext=AC; window.webkitAudioContext=AC; navigator.vibrate=()=>{window.__vib++;return true};'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    c=await b.new_context(viewport={'width':1100,'height':900}); await c.route(re.compile(r'https://.*'),lambda r:r.abort()); await c.add_init_script(HOOK)
    P=await c.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto(U+'?who=anon'); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(600)
    await P.evaluate('''(()=>{S.name="김가온";S.myNames=new Set(["김가온"]);S.rooms.push({id:"rt",title:"타이머 활동",year:"1학년",subject:"한국사",template:"debate2",stances:["찬성","반대"],status:"open",createdAt:Date.now(),timer:{dur:3000,endsAt:Date.now()+2500,left:null,at:Date.now()}});S.roomId="rt";S.view="room";render()})()''')
    await P.mouse.click(5,5)                                    # 화면을 한 번 건드려 소리 허락
    await P.wait_for_timeout(500)
    ok('진행 중에는 소리 없음', await P.evaluate('window.__osc')==0)
    ok('소리 켜짐 버튼 보임', await P.locator('.tmr-snd').count()>=1, await P.locator('.tmr-snd').first.inner_text() if await P.locator('.tmr-snd').count() else '')
    await P.wait_for_timeout(3500)
    o=await P.evaluate('window.__osc'); ok('끝나면 소리(띵동 x3 = 6음)', o==6, str(o))
    ok('진동도 한 번', await P.evaluate('window.__vib')==1)
    await P.wait_for_timeout(2500); ok('다시 울리지 않음', await P.evaluate('window.__osc')==6)
    # 끈 뒤에는 안 울림
    await P.evaluate('localStorage.setItem("nonjae.tmrsnd","off"); window.__osc=0; S.rooms[0].timer={dur:2000,endsAt:Date.now()+1500,left:null,at:Date.now()}; render()')
    await P.wait_for_timeout(3000); ok('소리 끔이면 안 울림', await P.evaluate('window.__osc')==0)
    # 오래 전에 끝난 타이머를 열어도 안 울림
    await P.evaluate('localStorage.removeItem("nonjae.tmrsnd"); S.rooms[0].timer={dur:2000,endsAt:Date.now()-60000,left:null,at:Date.now()-62000}; render()')
    await P.wait_for_timeout(2200); ok('지난 타이머는 안 울림', await P.evaluate('window.__osc')==0)
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
