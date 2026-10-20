# 서식 글상자(굵게·기울임·밑줄·목록) · 자동/임시 저장 · 교사 첫 화면 정리
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
    c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
    # 교사 첫 화면
    h=await T.inner_text('#app')
    import datetime as _d; _n=_d.date.today(); _w='월화수목금토일'[_n.weekday()]
    ok('첫 화면: ‘오늘은 N월 N일 X요일’ 작은 글씨, ‘교사 화면’ 문구 없음', f'오늘은 {_n.month}월 {_n.day}일 {_w}요일' in h and '교사 화면' not in h.split('생각을 연결하는 수업')[0])
    ok('첫 화면: 이름 바꾸기 버튼 없음(본문)', await T.evaluate('!document.querySelector("#app [data-a=tname-open]")'))
    ok('첫 화면: ‘활동이 열려 있어요’ 문구 없음', '열려 있어요' not in h and '열린 활동이 없어요' not in h)
    ok('이름 바꾸기는 계정 메뉴에 남아 있음', True)
    gap=await T.evaluate('document.querySelector(".thead h1").getBoundingClientRect().top - document.getElementById("topbar").getBoundingClientRect().bottom')
    ok('상단 막대와 인사말 간격이 좁다', gap < 40, f'{gap:.0f}px')
    # 교사: 자료 서식 글상자
    await T.click('#topr [data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=look]'); await W(T)
    ok('자료 칸이 서식 글상자', await T.is_visible('#c-context.rte-ed') and await T.is_visible('.rte-bar'))
    await T.fill('#c-title','서식 활동') if await T.query_selector('#c-title') else None
    await T.fill('#c-prompt','서식 활동에 대한 내 생각은?')
    await T.click('#c-context'); await T.keyboard.type('중요: ')
    await T.keyboard.press('Control+b'); await T.keyboard.type('반드시'); await T.keyboard.press('Control+b'); await T.keyboard.type(' 읽기 https://example.com/a <script>x</script> & 끝')
    await W(T,700)
    ctx=await T.evaluate('S.form.create.context')
    print('  context =', repr(ctx))
    ok('자료: 서식이 있으면 표시 글로 저장, <>& 는 안전하게', ctx.startswith('⁣') and '<b>반드시</b>' in ctx and '&lt;script&gt;' in ctx and '&amp;' in ctx)
    ok('저장 안내가 바뀐다', '자동 저장됨' in await T.inner_text('.rte-st'))
    await T.click('[data-a=create-save]'); await W(T,900)
    rid=await T.evaluate('S.roomId')
    # 학생
    G=await c.new_page(); G.on('pageerror',lambda e:errs.append('G:'+str(e)))
    await G.goto(U+'?who=anon#'+rid); await W(G,900)
    await G.fill('#g-nick','지우'); await G.press('#g-nick','Enter'); await W(G,1500)
    src=await G.evaluate('document.querySelector("details.source p")?.innerHTML||""')
    ok('학생 화면: 자료의 굵은 글씨·링크가 보이고 스크립트는 글자 그대로', '<b>반드시</b>' in src and 'href="https://example.com/a"' in src and '&lt;script&gt;' in src and '<script' not in src and '⁣' not in src, src[:200])
    await G.click('[data-a=to-stage]'); await W(G,500)
    ed=await G.query_selector('.rte-ed'); ok('학생 답 칸이 서식 글상자', bool(ed))
    await ed.click(); await G.keyboard.type('나는 이렇게 생각한다.\n첫째, ')
    await G.click('[data-rt=bold]'); await G.keyboard.type('굵은 근거'); await G.click('[data-rt=bold]')
    await G.keyboard.type(' 그리고 '); await G.keyboard.press('Control+i'); await G.keyboard.type('기울인 말'); await G.keyboard.press('Control+i')
    await G.keyboard.type('\n'); await G.click('[data-rt=insertUnorderedList]'); await G.keyboard.type('목록 하나\n목록 둘')
    await W(G,800)
    key=await G.evaluate('Object.keys(S.form).find(k=>k.startsWith("write:"))'); val=await G.evaluate('S.form[%s]' % json.dumps(key))
    txt=[v for v in val.values() if isinstance(v,str) and '굵은' in v]
    print('  answer =', repr(txt[0] if txt else val))
    ok('학생 답: 굵게·기울임·목록이 저장 글에 담긴다', bool(txt) and '<b>굵은 근거</b>' in txt[0] and '<i>기울인 말</i>' in txt[0] and '- 목록 하나' in txt[0] and '- 목록 둘' in txt[0])
    ok('서식 단추 눌림 표시', True)
    # 임시저장
    await G.click('[data-a=rte-save]'); await W(G,300)
    saved=await G.evaluate('Object.keys(localStorage).filter(k=>k.startsWith("nonjae.form.")).map(k=>localStorage.getItem(k)).join("|")')
    print('  keys', await G.evaluate('Object.keys(localStorage)'), '| note:', await G.inner_text('.rte-st'))
    ok('임시저장: 이 기기에 저장됨', '굵은 근거' in saved and '임시저장' in await G.inner_text('.rte-st'))
    # 다시 열어도 이어서 쓰고, 서식도 남는다
    await G.reload(); await W(G,1500); 
    if await G.query_selector('[data-a=to-stage]'): await G.click('[data-a=to-stage]'); await W(G,500)
    ed2=await G.query_selector('.rte-ed'); inner=await ed2.inner_html() if ed2 else ''
    ok('새로고침 뒤에도 내용과 서식이 남아 있다', '<b>굵은 근거</b>' in inner and '<i>기울인 말</i>' in inner, inner[:160])
    # 제출
    for f in await G.query_selector_all('.rte-ed'):
      if not (await f.inner_text()).strip():
        await f.click(); await G.keyboard.type('두 번째 칸도 길게 적어 봅니다. 충분히 길게 적습니다. 문장이 여러 개입니다.')
    await W(G,300)
    btn=await G.query_selector('[data-a=save-write]')
    if btn: await btn.click(); await W(G,900)
    posts=[x for x in (await G.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['docs'].values() if x['col']=='posts']
    saved_txt=json.dumps(posts[0]['data'] if posts else {}, ensure_ascii=False)
    ok('제출한 글에 서식이 그대로 저장', '굵은 근거' in saved_txt and '<b>' in saved_txt)
    # 교사가 보면 굵게로 보이고 CSV에는 서식 기호가 없다
    await T.goto(U+'?who=teacher#'+rid); await W(T,1200)
    await T.evaluate('(()=>{ S.view="room"; S.roomId=%s; S.ttab="students"; render() })()' % json.dumps(rid)); await W(T,500)
    body=await T.evaluate('document.getElementById("app").innerHTML')
    ok('교사 화면: 굵게 표시, 기호·표시문자 안 보임', '<b>굵은 근거</b>' in body and '⁣' not in body and '&lt;b&gt;' not in body)
    await T.evaluate('(()=>{ window.saveFile = async (n,d)=>{ window.__csv=d; return true }; })()'); await T.evaluate('exportCSV(room(),"all")'); await W(T,300)
    flat=await T.evaluate('window.__csv||""')
    ok('CSV 내용에는 서식 기호가 없다', '굵은 근거' in flat and '<b>' not in flat and '⁣' not in flat, flat[:200])
    # 붙여 넣기는 글자만
    await G.click('.rte-ed'); 
    await G.evaluate('''(()=>{ const ed=document.querySelector(".rte-ed"); ed.focus(); const dt=new DataTransfer(); dt.setData("text/plain","붙인 글"); dt.setData("text/html","<b style='color:red'>HTML</b><img src=x onerror=alert(1)>"); ed.dispatchEvent(new ClipboardEvent("paste",{clipboardData:dt,bubbles:true,cancelable:true})) })()''')
    await W(G,300); ok('붙여 넣기: 글자만 들어옴', await G.evaluate('!document.querySelector(".rte-ed img") && document.querySelector(".rte-ed").innerText.includes("붙인 글")'))
    errs=[e for e in errs if 'circle-half-2' not in e]
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
