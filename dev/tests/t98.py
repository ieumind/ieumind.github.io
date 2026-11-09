# 토론 예상 반론: 교사 설정(선택/꼭/끄기) · 학생 글쓰기 화면에 펼쳐서 · 상대 입장 이름으로 묻기 · counter로 저장 → 교사 칩·필터·생각 흐름
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def make(T, mode):
  W=lambda ms=400: T.wait_for_timeout(ms)
  await T.click('[data-a=create] >> nth=0'); await W(); await T.click('[data-a=goal][data-v=compare]'); await W()
  await T.click('[data-a=tpl][data-v=debate2]'); await W()
  await T.fill('#c-prompt','해방 직후 무엇을 먼저 해야 했을까?')
  await T.fill('#c-st0','친일 청산'); await T.fill('#c-st1','국가 체제 정비'); await W(200)
  await T.evaluate('document.querySelectorAll("details.cfold").forEach(d=>d.open=true)'); await W(200)
  has=await T.locator('#c-counter').count()
  if mode: await T.select_option('#c-counter', mode); await W(200)
  await T.click('[data-a=create-save]'); await W(900)
  return has, await T.evaluate('S.roomId'), await T.evaluate('room().features.counterMode')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(800)
    has, rid, cm = await make(T, 'req')
    ok('교사 설정에 예상 반론 선택', has==1); ok('꼭 쓰기 저장', cm=='req', cm)
    G=await c.new_page(); G.on('pageerror',lambda e:errs.append('G:'+str(e)))
    await G.goto(U+'?who=anon#'+rid); await G.wait_for_timeout(900)
    await G.fill('#g-nick','지우'); await G.press('#g-nick','Enter'); await G.wait_for_timeout(1400)
    if await G.locator('[data-a=to-stage]').count(): await G.click('[data-a=to-stage]'); await G.wait_for_timeout(500)
    ok('예상 반론 칸이 펼쳐져 보임', await G.locator('.cqbox').is_visible())
    ok('접힌 상자에 다른 관점 칸 없음', await G.evaluate('!document.querySelector("details.help textarea[data-k=_other], details.help [id$=-_other]")'))
    await G.click('input[name$="_stance"] >> nth=0', force=True) if await G.locator('input[name$="_stance"]').count() else None
    await G.evaluate('''(()=>{const k=Object.keys(S.form).find(k=>k.startsWith("write:")); S.form[k]._stance="친일 청산";})()''')
    await G.evaluate('render()'); await G.wait_for_timeout(300)
    await G.set_viewport_size({'width':390,'height':844}); await G.wait_for_timeout(200); await G.locator('.cqbox').screenshot(path='/tmp/claude-0/shots/t98_cq.png'); await G.set_viewport_size({'width':1280,'height':900})
    lb=await G.locator('.cqbox label').first.inner_text(); ok('상대 입장 이름으로 묻기', '국가 체제 정비' in lb, lb)
    key=await G.evaluate('Object.keys(S.form).find(k=>k.startsWith("write:"))')
    await G.evaluate(f'''(()=>{{const f=S.form["{key}"]; for(const x of effFields(room())) f[x.k]="나는 친일 청산이 먼저라고 생각한다. 독립운동가의 희생을 헛되게 하지 않기 위해서다. 정의로운 나라를 세우려면 과거를 바로잡아야 한다."; f._obj=""}})()''')
    await G.evaluate('render()'); await G.wait_for_timeout(200)
    await G.click('#wsubmit'); await G.wait_for_timeout(500)
    ok('꼭 쓰기: 비우면 못 보냄', not await G.evaluate('!!myPost(room())?.submittedAt'))
    await G.evaluate(f'''(()=>{{const f=S.form["{key}"]; f._obj="상대편은 나라가 혼란하면 청산도 못 한다고 반박할 것이다."; f._resp="그 말도 일리가 있지만 둘은 함께 할 수 있다."}})()''')
    await G.click('#wsubmit'); await G.wait_for_timeout(800)
    post=await G.evaluate('myPost(room())')
    ok('counter로 저장', bool(post and post.get('counter',{}).get('objection','').startswith('상대편은')) and post.get('submittedAt'), post and post.get('counter'))
    # teacher view
    await T.reload(); await T.wait_for_timeout(900)
    await T.evaluate(f'location.hash="#{rid}"'); await T.wait_for_timeout(800)
    await T.evaluate('S.ttab="students"; render()'); await T.wait_for_timeout(500)
    chips=await T.locator('article.tcard .tc-prog .pm').all_inner_texts()
    ok('교사 카드에 예상 반론 칩(완료)', any('예상 반론' in x for x in chips) and await T.locator('article.tcard .pm.on', has_text='예상 반론').count()==1, chips)
    ok('예상 반론 없음 필터', await T.locator('.mfilters button[data-v=nocounter]').count()==1)
    # legacy deeper.other shows as counter
    leg=await T.evaluate('''(()=>{const p={deeper:{other:"옛 다른 관점"}}; const c=counterOf(p); return c&&c.objection})()'''); ok('예전 다른 관점 글도 예상 반론으로', leg=='옛 다른 관점')
    # off mode: no box, folded _other back
    has, rid2, cm2 = await make(T, 'off'); ok('묻지 않기 저장', cm2=='off', cm2)
    st=await T.evaluate(f'''(()=>{{const r=S.rooms.find(x=>x.id==="{rid2}")||room(); return [counterMode(r), counterOn(r)]}})()'''); ok('끄기 모드', st==['off',False], st)
    # default opt for old debate room without setting
    d=await T.evaluate('counterMode({stances:["a","b"],template:"debate2",features:{}})'); ok('예전 토론 활동 기본은 선택', d=='opt', d)
    d=await T.evaluate('counterMode({stances:[],template:"reflect",features:{}})'); ok('입장 없는 활동은 끔', d=='off', d)
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
