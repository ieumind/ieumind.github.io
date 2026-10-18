# 🙋 과목 없는 활동: 학생 코드 없이 이름·닉네임만 넣고 참여 (임시 참가자)
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=300: pg.wait_for_timeout(ms)
    c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    ok=lambda name,cond: print(('PASS ' if cond else 'FAIL ')+name)
    T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    async def make_room(title):
      await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=look]'); await W(T)
      await T.fill('#c-title', title) if await T.query_selector('#c-title') else None
      await T.fill('#c-prompt', title+' 에 대한 내 생각은?'); 
      hint=await T.evaluate('document.querySelector(".cpick .cchip.none")?.getAttribute("aria-pressed")')
      await T.click('[data-a=create-save]'); await W(T,800)
      return await T.evaluate('S.roomId')
    # 교사: 과목이 없는 활동 만들기 (과목이 하나도 없으면 안내 문구가 보여야 한다)
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=look]'); await W(T)
    print('teacher hint:', (await T.evaluate('[...document.querySelectorAll("#app .hint")].map(x=>x.textContent).find(t=>t.includes("개인 코드 없이"))||null')))
    await T.click('[data-a=home]'); await W(T)
    r1=await make_room('첫 번째 활동'); r2=await make_room('두 번째 활동')
    docs=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs']
    print('rooms:', r1, r2, '| status/courseId:', docs['rooms/'+r1]['data'].get('status'), repr(docs['rooms/'+r1]['data'].get('courseId')))
    # 학생 1 (새 기기): 링크로 들어오면 이름·닉네임 입력 화면
    G1=await c.new_page(); G1.on('pageerror',lambda e:errs.append('G1:'+str(e)))
    await G1.goto(U+'?who=anon#'+r1); await W(G1,900)
    ok('G1 sees nickname gate', bool(await G1.query_selector('#g-nick')) and not await G1.query_selector('#f-code'))
    print('gate heading:', (await G1.inner_text('.gate-hero h1')))
    await G1.fill('#g-nick','10301 김가온'); await G1.press('#g-nick','Enter'); await W(G1,500)
    print('number rejected:', (await G1.inner_text('.gate-form .notice')))
    await G1.fill('#g-nick','   '); await G1.click('[data-a=guest-join]'); await W(G1,400)
    print('empty rejected:', (await G1.inner_text('.gate-form .notice')))
    await G1.fill('#g-nick','지우'); await G1.press('#g-nick','Enter'); await W(G1,1500)
    nm=await G1.evaluate('[S.name, S.guest, S.canWrite, S.view, S.roomId===%s]' % json.dumps(r1))
    ok('G1 entered room as 지우 (name, guest, canWrite, view, room)', nm==['지우',True,True,'room',True]); print('  ', nm)
    print('top bar:', (await G1.inner_text('#topr')).replace('\n',' | '), '| pushbar:', bool(await G1.query_selector('.pushbar')))
    # 글쓰기: 감상·성찰 — 첫 칸 쓰고 저장
    await G1.click('[data-a=to-stage]'); await W(G1,400)
    ta=await G1.query_selector_all('textarea[data-form]'); print('textareas:', len(ta), await G1.evaluate('[...document.querySelectorAll("#app button[data-a]")].map(e=>e.dataset.a).join(",")'))
    await ta[0].fill('지우의 첫 생각입니다. 충분히 길게 적어 봅니다. 여러 문장으로 씁니다.'); await W(G1,200)
    btn=await G1.query_selector('[data-a=save-write]'); 
    if btn: await btn.click(); await W(G1,700)
    posts=[x for x in (await G1.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs'].values() if x['col']=='posts']
    print('posts:', [(x['data']['author'], x.get('owner','')[:1]) for x in posts])
    ok('G1 post saved with nickname as author', any(x['data']['author']=='지우' for x in posts))
    # 다시 열면 묻지 않는다
    await G1.reload(); await W(G1,1200)
    ok('G1 reload: no gate, still 지우', await G1.evaluate('[S.name, S.guest, !!S.guestGate]')==['지우',True,False])
    # 학생 2: 같은 이름은 안 된다
    G2=await c.new_page(); G2.on('pageerror',lambda e:errs.append('G2:'+str(e)))
    await G2.goto(U+'?who=anon#'+r1); await W(G2,900)
    await G2.fill('#g-nick',' 지 우 '); await G2.click('[data-a=guest-join]'); await W(G2,500)
    print('dup rejected:', (await G2.inner_text('.gate-form .notice')))
    await G2.fill('#g-nick','하준'); await G2.click('[data-a=guest-join]'); await W(G2,1500)
    ok('G2 entered as 하준', await G2.evaluate('[S.name, S.guest, S.view]')==['하준',True,'room'])
    # 서로 모르는 활동: 학생 1이 참가하지 않은 활동은 안 보인다 (r2는 G1이 아직 안 들어옴)
    print('G1 rooms visible:', await G1.evaluate('S.rooms.map(r=>r.id)'), '(기대: r1만)')
    # 같은 기기에서 두 번째 활동 링크를 열면 같은 이름으로 바로 들어간다
    await G1.evaluate('location.hash = %s' % json.dumps('#'+r2)); await W(G1,1800)
    print('G1 after 2nd link:', await G1.evaluate('[S.name, S.rooms.map(r=>r.id).sort(), S.view, S.roomId]'))
    # 이 기기의 이름을 다른 친구가 이미 쓰고 있을 때
    G3=await c.new_page(); G3.on('pageerror',lambda e:errs.append('G3:'+str(e)))
    await G3.goto(U+'?who=anon#'+r2); await W(G3,900); await G3.fill('#g-nick','하준'); await G3.click('[data-a=guest-join]'); await W(G3,1500)
    ok('G3 joined room2 as 하준 (different room, ok)', await G3.evaluate('S.name')=='하준')
    await G3.evaluate('location.hash = %s' % json.dumps('#'+r1)); await W(G3,1800)
    print('G3 on room1 (하준 taken):', (await G3.inner_text('.gate-form')).replace('\n',' | ')[:140], '| reset btn:', bool(await G3.query_selector('[data-a=guest-reset]')))
    # 과목 활동(코드 필요) 링크는 예전처럼 코드 화면
    await T.evaluate('(()=>{ const D=JSON.parse(localStorage.getItem("__sbmock")); const r=JSON.parse(JSON.stringify(D.docs["rooms/%s"])); r.id="rcourse"; r.data.courseId="cX"; D.docs["rooms/rcourse"]=r; localStorage.setItem("__sbmock",JSON.stringify(D)) })()' % r1); 
    C=await c.new_page(); C.on('pageerror',lambda e:errs.append('C:'+str(e)))
    await C.goto(U+'?who=anon#rcourse'); await W(C,900)
    ok('course room still asks for personal code', bool(await C.query_selector('#f-code')) and not await C.query_selector('#g-nick'))
    # ‘코드로 들어가기’
    await G2.evaluate('localStorage.getItem("x")'); 
    N=await c.new_page(); N.on('pageerror',lambda e:errs.append('N:'+str(e))); await N.goto(U+'?who=anon#'+r1); await W(N,800); await N.click('[data-a=guest-code]'); await W(N,300)
    ok('guest-code shows the code form', bool(await N.query_selector('#f-code')))
    # 모바일에서 넘침 없음
    M=await c.new_page(); await M.set_viewport_size({'width':390,'height':844}); M.on('pageerror',lambda e:errs.append('M:'+str(e)))
    await M.goto(U+'?who=anon#'+r1); await W(M,900); print('mobile gate overflow:', await M.evaluate('document.documentElement.scrollWidth'), '(<=390)')
    await M.screenshot(path='/tmp/claude-0/smoke/mob/guest_gate.png')
    await G1.set_viewport_size({'width':390,'height':844}); await G1.evaluate('location.hash = %s' % json.dumps('#'+r1)); await W(G1,600); await G1.screenshot(path='/tmp/claude-0/smoke/mob/guest_room.png')
    # 다른 이름으로: 확인 창 → 새 이름
    await G1.click('[data-a=rename]'); await W(G1,300); print('switch modal:', (await G1.inner_text('#modal h3')))
    # 선생님: 참가자 글이 보인다
    await T.reload(); await W(T,900); print('teacher sees authors:', await T.evaluate('S.posts.map(p=>p.author)'))
    print('errors', errs); await b.close()
asyncio.run(main())
