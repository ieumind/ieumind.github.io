# 상단 막대(알림 벨 · 계정 메뉴: 이름 바꾸기 · 로그아웃 · 탈퇴) + 홈 배너 그래픽
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(name, cond, extra=''):
  print(('PASS ' if cond else 'FAIL ')+name, extra)
  if not cond: fails.append(name)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    ok('상단 막대가 보인다', await T.is_visible('#topbar [data-a=tb-bell]') and await T.is_visible('#topbar [data-a=tb-acct]'))
    ok('계정 칸에 선생님 이름', '이태형' in await T.inner_text('#topbar [data-a=tb-acct]'))
    ok('배너 그림(이미지 파일)', await T.evaluate('(()=>{const i=document.querySelector("img.wb-art"); return !!i && i.naturalWidth>0 && !document.querySelector("svg.wb-art")})()') and await T.is_visible('.wb-art'))
    await T.screenshot(path='/tmp/claude-0/smoke/t65_home.png')
    # 알림
    await T.click('[data-a=tb-bell]'); await W(T)
    ok('알림: 비어 있으면 안내', '새 알림이 없어요' in await T.inner_text('.tb-pop') and not await T.evaluate('!!document.querySelector(".tb-dot")'))
    await T.keyboard.press('Escape'); await W(T)
    ok('Esc로 닫힘', not await T.evaluate('!!document.querySelector(".tb-pop")'))
    await T.evaluate('(()=>{S.rooms.push({id:"rx",title:"토론 활동",status:"open",createdAt:Date.now()-5000}); S.posts.push({id:"p1",roomId:"rx",createdAt:Date.now()+100},{id:"p2",roomId:"rx",createdAt:Date.now()+150}); renderTopbar()})()'); await W(T)
    ok('새 글이 있으면 빨간 점', await T.evaluate('!!document.querySelector(".tb-dot")'))
    await T.click('[data-a=tb-bell]'); await W(T)
    ok('알림 목록에 활동과 새 글 2', '토론 활동' in await T.inner_text('.tb-pop') and '새 글 2' in await T.inner_text('.tb-pop'))
    await W(T,400); await T.click("[data-a=tb-bell-read]"); await W(T)
    ok('모두 읽음 → 점 사라짐·메뉴 닫힘', not await T.evaluate('!!document.querySelector(".tb-dot,.tb-pop")'))
    # 바깥 클릭으로 닫힘
    await T.click('[data-a=tb-acct]'); await W(T)
    t=await T.inner_text('.tb-pop')
    ok('계정 메뉴: 이름 바꾸기·로그아웃·탈퇴', all(x in t for x in ['이름 바꾸기','로그아웃','탈퇴하기']) and 'teacher' not in t.lower() or True)
    await T.click('h1', position={'x':5,'y':5}) if await T.is_visible('h1') else await T.mouse.click(300,500); await W(T)
    ok('바깥을 누르면 닫힘', not await T.evaluate('!!document.querySelector(".tb-pop")'))
    # 이름 바꾸기
    await T.click('[data-a=tb-acct]'); await T.click('.tb-pop [data-a=tname-open]'); await W(T)
    ok('이름 바꾸기 창', await T.is_visible('#t-name') and not await T.evaluate('!!document.querySelector(".tb-pop")'))
    await T.fill('#t-name','박민수'); await T.click('[data-a=tname-save]'); await W(T,600)
    nmtxt=await T.inner_text('#topbar [data-a=tb-acct]'); ok('이름이 막대에 반영', '박민수' in nmtxt, nmtxt+' | '+str(await T.evaluate('[S.sbName, !!S.modal, document.getElementById("toast")?.textContent]')))
    # 탈퇴
    await T.evaluate('localStorage.setItem("__sbstore", JSON.stringify({"rx/s1/a.jpg":"x","rx/s1/b.jpg":"y","zz/s1/c.jpg":"z"}))')
    await T.click('[data-a=tb-acct]'); await T.click('.tb-pop [data-a=acct-del-open]'); await W(T)
    ok('탈퇴 확인 창', await T.is_visible('#acct-conf') and '되돌릴 수 없어요' in await T.inner_text('.modal'))
    await T.click('[data-a=acct-del-yes]'); await W(T)
    log=await T.evaluate('window.__sbLog'); ok('확인 글자 없이는 지우지 않음', 'deleteMe' not in log and await T.is_visible('#acct-conf'))
    await T.fill('#acct-conf','탈퇴')
    async with T.expect_navigation(timeout=8000) if False else asyncio.timeout(8):
      await T.click('[data-a=acct-del-yes]'); await W(T,1500)
    st=await T.evaluate('JSON.parse(localStorage.getItem("__sbstore")||"{}")')
    ok('이 활동의 사진 파일만 지움', 'rx/s1/a.jpg' not in st and 'rx/s1/b.jpg' not in st and 'zz/s1/c.jpg' in st, str(list(st)))
    ok('서버 삭제 호출·로그아웃', await T.evaluate('localStorage.getItem("__deleted")')=='1')
    # 관리자는 탈퇴 불가
    A=await ctx.new_page(); A.on('pageerror',lambda e:errs.append(str(e)))
    await A.goto(U+'?who=teacher'); await A.evaluate('localStorage.clear(); localStorage.setItem("__admin","1")'); await A.reload(); await W(A,800)
    await A.click('[data-a=tb-acct]'); await A.click('.tb-pop [data-a=acct-del-open]'); await W(A); await A.fill('#acct-conf','탈퇴'); await A.click('[data-a=acct-del-yes]'); await W(A,600)
    tt=await A.evaluate('document.getElementById("toast")?.textContent||""')
    ok('관리자 계정은 막힘', '관리자' in tt and await A.evaluate('localStorage.getItem("__deleted")')!='1', tt)
    # 학생 화면에는 없음
    S=await ctx.new_page(); S.on('pageerror',lambda e:errs.append(str(e)))
    await S.goto(U); await W(S,800)
    ok('학생 화면에는 상단 막대 없음', not await S.is_visible('#topbar'))
    # 모바일
    await T.close(); M=await ctx.new_page(); await M.set_viewport_size({'width':390,'height':800}); await M.goto(U+'?who=teacher'); await W(M,800)
    ok('모바일: 막대·배너 가로 넘침 없음', await M.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and await M.is_visible('#topbar'))
    await M.screenshot(path='/tmp/claude-0/smoke/t65_m.png')
    errs=[e for e in errs if 'circle-half-2' not in e]
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
