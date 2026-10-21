# 학생 화면 개편(상단 벨·계정, 배너, 바로가기, 지표 칸) + 오류·건의하기 왼쪽 막대 이동
import asyncio, re, json
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
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    # 교사: 왼쪽 막대 순서 = 앱으로 설치 → 오류·건의하기 → 로그아웃, 맨 아래 푸터에는 없음
    order=await T.eval_on_selector_all('#sideme [data-a]','e=>e.map(x=>x.dataset.a)')
    ok('교사 왼쪽 막대: 설치 → 오류·건의 → 로그아웃', order==['install-help','feedback-open','t-logout'], str(order))
    ok('푸터에 오류·건의하기 없음', await T.evaluate('!document.querySelector(".appfoot [data-a=feedback-open]")') and '제작' in await T.inner_text('.appfoot'))
    await T.click('#sideme [data-a=feedback-open]'); await W(T); ok('왼쪽 막대의 단추로 건의 창이 열림', await T.is_visible('#fb-body')); await T.keyboard.press('Escape'); await W(T)
    # 교사가 학생·과목·활동 만들기
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온'); await T.click('[data-a=roster-add]'); await W(T)
    studs=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']; code=studs[0]['code']; sid=[s['id'] for s in studs]
    await T.keyboard.press('Escape'); await W(T)
    await T.click('[data-a=course-new]'); await W(T); await T.fill('#course-title','1학년 한국사')
    await T.evaluate(f'(()=>{{const f=S.form.course; f.sel={json.dumps(sid)}; renderModal()}})()'); await W(T)
    await T.click('[data-a=course-save]'); await W(T,700)
    for t,pr in (('3·1 운동의 의미','3·1 운동이 주는 의미는?'),):
      await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=look]'); await W(T)
      if await T.query_selector('#c-title'): await T.fill('#c-title', t)
      await T.fill('#c-prompt', pr); await T.click('[data-a=create-save]'); await W(T,900); await T.evaluate('act("home",{dataset:{}})'); await W(T)
    # 학생
    S=await ctx.new_page(); S.on('pageerror',lambda e:errs.append('S:'+str(e)))
    await S.goto(U+'?who=anon'); await W(S,900)
    ok('코드 입력 화면에는 상단 막대 없음', not await S.is_visible('#topbar'))
    await S.fill('#f-num','10301'); await S.fill('#f-name','김가온'); await S.fill('#f-code',code); await S.click('[data-a=setname]'); await W(S,1500)
    ok('처음 코드로 들어온 학생에게 환영 창', '김가온님, 환영해요' in await S.inner_text('.welcome')); await S.click('.welcome [data-a=modal-close]'); await W(S,300)
    ok('학생 상단 막대(벨·계정)', await S.is_visible('#topbar [data-a=tb-bell]') and '김가온' in await S.inner_text('#topbar [data-a=tb-acct]'))
    ok('학생: 오늘 날짜 작은 글씨 + 인사말', '오늘은' in await S.inner_text('.shome-hi .eyebrow') and '김가온님, 안녕하세요' in await S.inner_text('.shome-hi h1'))
    ok('학생: 배너 이미지', await S.evaluate('(()=>{const i=document.querySelector(".wbanner img.wb-art"); return !!i && i.naturalWidth>0})()'))
    ok('학생: 바로가기 카드(이어서 하기·내 생각 기록·과목 추가)', await S.evaluate('[...document.querySelectorAll(".qgrid .qa b")].map(x=>x.textContent).join("|")')=='이어서 하기|내 생각 기록|과목 추가')
    tiles=await S.evaluate('[...document.querySelectorAll(".tstats.s3 .tstat")].map(x=>x.querySelector(".tl").textContent+":"+x.querySelector("b").textContent)')
    ok('학생: 지표 칸 3개(해야 할 1)', tiles==['해야 할 활동:1','하는 중:0','다 했어요:0'], str(tiles))
    ok('학생 왼쪽 막대에 오류·건의하기, 푸터에는 없음', await S.is_visible('#sideme [data-a=feedback-open]') and await S.evaluate('!document.querySelector(".appfoot [data-a=feedback-open]")'))
    # 벨: 새 활동은 처음 쓰는 기기에서는 ‘본 것’이므로 비어 있다 → 교사가 새 활동을 올리면 보인다
    await S.click('[data-a=tb-bell]:visible'); await W(S)
    ok('벨: 새 소식 없으면 안내', '없어요' in await S.inner_text('.tb-pop')); await S.keyboard.press('Escape'); await W(S)
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=look]'); await W(T)
    await T.fill('#c-title','새로 올린 활동') if await T.query_selector('#c-title') else None
    await T.fill('#c-prompt','새 질문입니다'); await T.click('[data-a=create-save]'); await W(T,900)
    await S.reload(); await W(S,1500)
    ok('새 활동이 오면 벨에 점', await S.evaluate('!!document.querySelector("#topbar .tb-dot")'))
    await S.click('[data-a=tb-bell]:visible'); await W(S)
    ok('벨 목록에 새 활동', '새로 올린 활동' in await S.inner_text('.tb-pop') and '새 활동' in await S.inner_text('.tb-pop'))
    await S.click('.tb-pop:visible [data-a=tb-bell-read]'); await W(S)
    ok('모두 읽음 → 점 사라짐', not await S.evaluate('!!document.querySelector("#topbar .tb-dot")'))
    # 계정 메뉴
    await S.click('[data-a=tb-acct]:visible'); t=await S.inner_text('.tb-pop')
    ok('계정 메뉴: 내 생각 기록·과목 추가·다른 학생으로', all(x in t for x in ['내 생각 기록','과목 추가','다른 학생으로']), t.replace('\n',' | '))
    await S.click('.tb-pop:visible [data-a=mine]'); await W(S); ok('내 생각 기록으로 이동', await S.evaluate('S.view')=='mine' and not await S.evaluate('!!document.querySelector(".tb-pop")'))
    # 과목 화면에도 지표 칸
    await S.evaluate('act("home",{dataset:{}})'); await W(S); await S.click('[data-a=dash]'); await W(S,500)
    ok('과목 화면에도 지표 칸', await S.evaluate('!!document.querySelector(".dhead") && !!document.querySelector(".tstats.s3")'))
    # 모바일
    await S.set_viewport_size({'width':390,'height':844}); await S.evaluate('act("dash-back",{dataset:{}})'); await W(S,500)
    ok('모바일: 가로 넘침 없음', await S.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    await S.screenshot(path='/tmp/claude-0/smoke/t67_m.png', full_page=True)
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
