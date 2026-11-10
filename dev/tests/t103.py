# 실시간 토론 추가 기능(2026-11-10r~): 1 토론 단계 · 3 선생님 공지 · 6 연결 상태 (뒤 단계에서 2·4·5도 여기에)
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
    # 3) 공지: 대기실에서도 보인다
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,1200)
    await T.fill('#lv-tn','곧 토론을 시작해요. 닉네임을 확인하세요.'); await T.click('[data-a=lv-notice]'); await W(T,900); await W(C,1500)
    ok('대기실에도 선생님 공지', '곧 토론을 시작해요' in (await C.locator('.lvnotice').inner_text() if await C.locator('.lvnotice').count() else ''))
    # 1) 토론 단계
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,1500)
    ok('교사: 단계 칩 4개(자유·입론·반론·최종 변론)', await T.locator('.lvr-chip').count()==4)
    ok('교사: 처음엔 자유 토론, 다음은 입론', await T.locator('.lvr-chip.on').inner_text()=='자유 토론' and '입론' in await T.locator('.lvr-chip.next').inner_text())
    await T.click('.lvr-chip[data-v=open]'); await W(T,900); await W(A,1500)
    ok('타이머 3분 함께 시작', await T.evaluate('room().timer && room().timer.dur')==180000)
    hd=await A.locator('.lvhead2').inner_text()
    ok('학생 머리 카드: 입론 + 할 일', '입론' in hd and '주장과 근거를 밝혀요' in hd, hd.replace('\n',' | ')[:200])
    ok('학생: 단계 표시 3칸, 지금 단계 강조', await A.locator('.lvr-steps li').count()==3 and '입론' in await A.locator('.lvr-steps li.on').inner_text())
    ok('입력칸 안내가 단계에 맞게', '주장과 근거' in (await A.locator('#lv-in').get_attribute('placeholder')))
    await A.fill('#lv-in','반민특위는 꼭 필요했어요.'); await A.click('[data-a=lv-send]'); await W(A,800)
    await T.click('[data-a=lv-rtmr]'); await W(T,300)
    await T.click('.lvr-chip[data-v=rebut]'); await W(T,900); await W(A,1500)
    ok('타이머 끄면 단계만 바뀜', await T.evaluate('room().timer.dur')==180000 and await T.evaluate('room().live.round')=='rebut')
    dv=await A.locator('#lv-msgs .lvdiv').all_inner_texts()
    ok('채팅에 단계 구분선(입론 → 메시지 → 반론)', len(dv)==2 and '입론' in dv[0] and '반론' in dv[1], dv)
    order=await A.evaluate('[...document.querySelectorAll("#lv-msgs > li")].map(x=>x.classList.contains("lvdiv")?"D":"M").join("")')
    ok('구분선 순서', order=='DMD', order)
    ok('교사 채팅에도 구분선', await T.locator('#lv-msgs .lvdiv').count()==2)
    # 3) 공지 바꾸기·내리기
    await T.fill('#lv-tn','이제 반론 시간이에요.'); await T.click('[data-a=lv-notice]'); await W(T,800); await W(A,1500)
    ok('토론방 채팅 위 공지 바뀜', '이제 반론 시간이에요' in await A.locator('.lvnotice').inner_text())
    await T.click('[data-a=lv-notice-off]'); await W(T,800); await W(A,1500)
    ok('공지 내리기', await A.locator('.lvnotice').count()==0)
    # 6) 연결 상태
    await A.evaluate('window.dispatchEvent(new Event("offline"))'); await W(A,300)
    ok('끊기면 연결 띠', await A.locator('.lvconn').count()==1 and '연결이 끊겼어요' in await A.locator('.lvconn').inner_text())
    await A.evaluate('window.dispatchEvent(new Event("online"))'); await W(A,1200)
    ok('다시 연결되면 띠 사라지고 알림', await A.locator('.lvconn').count()==0 and '다시 연결됐어요' in await A.evaluate('document.body.innerText'))
    await A.set_viewport_size({'width':390,'height':844}); await W(A,300); await A.screenshot(path='/tmp/claude-0/shots/t103_A390.png', full_page=True)
    await T.screenshot(path='/tmp/claude-0/shots/t103_T.png', full_page=True)
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails); raise SystemExit(1 if fails else 0)
asyncio.run(main())
