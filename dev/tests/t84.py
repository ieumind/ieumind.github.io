# 타이머 종료 소리 실제 검증: 만들어진 WAV의 내용(주파수·크기·길이) + <audio>가 실제로 재생되는지 + 터치만으로도 깨어나는지 + 막히면 안내
import asyncio, re, struct, math
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
SET='''(()=>{S.name="김가온";S.myNames=new Set(["김가온"]);S.rooms=S.rooms.filter(r=>r.id!=="rt");S.rooms.push({id:"rt",title:"t",year:"1학년",template:"debate2",stances:["찬성","반대"],status:"open",createdAt:Date.now(),timer:{dur:3000,endsAt:Date.now()+2500,left:null,at:Date.now()}});S.roomId="rt";S.view="room";localStorage.setItem("ieum_linkrooms",'["rt"]');render()})()'''
LOG='''window.__plays=[];const _p=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.__plays.push({muted:this.muted,t:this.currentTime});return _p.apply(this,arguments)};'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--autoplay-policy=document-user-activation-required'])
    # 1) 터치만 있는 기기(아이폰처럼): tap → touchend/click으로 깨어나야 함
    ctx=await b.new_context(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort()); await ctx.add_init_script(LOG)
    P=await ctx.new_page(); errs=[]; P.on('pageerror',lambda e:errs.append(str(e)))
    await P.goto(U+'?who=anon'); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(600)
    await P.evaluate(SET); await P.wait_for_timeout(300)
    await P.tap('body', position={'x':10,'y':10}); await P.wait_for_timeout(400)
    ok('터치 후 오디오 준비됨(깨어남)', await P.evaluate('!!TMR_AU && TMR_AU.__unlocked===true'))
    await P.wait_for_timeout(3600)
    plays=await P.evaluate('window.__plays')
    ok('끝나면 소리 재생(소리 켠 채 play 1회)', [x for x in plays if not x['muted']].__len__()==1, str(plays))
    ok('재생이 실제로 진행됨(currentTime>0 또는 재생 중)', await P.evaluate('!TMR_AU.paused || TMR_AU.currentTime>0'))
    # WAV 내용 분석
    wav=await P.evaluate('''async()=>{const r=await fetch(TMR_URL);const b=new Uint8Array(await r.arrayBuffer());return Array.from(b)}''')
    raw=bytes(wav); sr=struct.unpack('<I',raw[24:28])[0]; n=(len(raw)-44)//2; s=struct.unpack('<%dh'%n, raw[44:44+n*2])
    peak=max(abs(x) for x in s)/32768; dur=n/sr
    ok('WAV 길이 약 2초', 1.9<dur<2.3, f'{dur:.2f}s')
    ok('WAV 소리 크기 충분(피크 0.2~0.99)', 0.2<peak<0.99, f'{peak:.2f}')
    ok('WAV 잘림(클리핑) 없음', max(abs(x) for x in s)<32767)
    def goertzel(f, a, b2):
      w=2*math.pi*f/sr; c=2*math.cos(w); s1=s2=0.0
      for x in s[a:b2]:
        s0=x+c*s1-s2; s2=s1; s1=s0
      return s1*s1+s2*s2-c*s1*s2
    a=int(0.05*sr); e=int(0.2*sr)
    ok('첫 음은 880Hz(띵)', goertzel(880,a,e) > 20*goertzel(1175,a,e))
    a2=int(0.30*sr); e2=int(0.45*sr)
    ok('둘째 음은 1175Hz(동)', goertzel(1175,a2,e2) > 5*goertzel(880,a2,e2))
    ok('세 번 반복(두 번째·세 번째 시작에도 소리)', max(abs(x) for x in s[int(.68*sr):int(.75*sr)])>8000 and max(abs(x) for x in s[int(1.33*sr):int(1.4*sr)])>8000)
    ok('무음 구간 없이 끝까지 감쇠(마지막은 거의 0)', max(abs(x) for x in s[-200:])<500)
    # 다시 안 울림
    await P.wait_for_timeout(2500); ok('다시 울리지 않음', len([x for x in await P.evaluate('window.__plays') if not x['muted']])==1)
    # 들어보기 버튼
    await P.evaluate(SET.replace('Date.now()+2500','Date.now()+90000')); await P.wait_for_timeout(500)
    await P.evaluate('window.__plays=[]'); await P.tap('[data-a=tmr-test]'); await P.wait_for_timeout(500)
    ok('들어보기 버튼 → 바로 소리', len([x for x in await P.evaluate('window.__plays') if not x['muted']])>=1)
    # 평소(타이머 없음/이미 끝난 타이머)엔 소리 준비·재생을 하지 않는다 (폰 음악 끊김 방지)
    await P.goto(U+'?who=anon'); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(600)
    await P.tap('body', position={'x':10,'y':10}); await P.wait_for_timeout(300)
    ok('타이머 없으면 오디오 준비 안 함', await P.evaluate('TMR_AU===null && TMR_AC===null'))
    await P.evaluate(SET.replace('Date.now()+2500','Date.now()-1500')); await P.wait_for_timeout(2500)
    ok('들어오자마자 이미 끝난 타이머는 울리지 않음', len(await P.evaluate('window.__plays'))==0)
    await ctx.close()
    # 2) 한 번도 안 건드린 기기: 소리 막히면 안내 문구
    ctx=await b.new_context(viewport={'width':390,'height':844}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    await ctx.add_init_script('HTMLMediaElement.prototype.play=function(){return Promise.reject(new DOMException("blocked","NotAllowedError"))};const AC=window.AudioContext;window.AudioContext=function(){const c=new AC();Object.defineProperty(c,"state",{get:()=>"suspended"});return c};')
    P=await ctx.new_page(); await P.goto(U+'?who=anon'); await P.evaluate('localStorage.clear()'); await P.reload(); await P.wait_for_timeout(600)
    await P.evaluate(SET); await P.wait_for_timeout(3700)
    ok('터치 없이 막히면 안내 문구가 뜸', '소리가 막혀' in await P.evaluate('document.body.innerText'), '')
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
