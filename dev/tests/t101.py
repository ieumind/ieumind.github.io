# 댓글·답 통합(2026-11-10k): 친구 글 아래 댓글 칸 하나 · ‘근거를 들어 답하기’면 이유 칸 필수 · 근거 댓글 표시 · 이유 없는 예전 ‘답’은 댓글로
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def make(T):
  W=lambda ms=400: T.wait_for_timeout(ms)
  await T.click('[data-a=create] >> nth=0'); await W(); await T.click('[data-a=goal][data-v=compare]'); await W()
  await T.click('[data-a=tpl][data-v=debate2]'); await W()
  await T.fill('#c-prompt','해방 직후 무엇을 먼저 해야 했을까?')
  await T.fill('#c-st0','친일 청산'); await T.fill('#c-st1','국가 체제 정비'); await W(200)
  await T.evaluate('document.querySelectorAll("details.cfold").forEach(d=>d.open=true)'); await W(200)
  await T.select_option('#c-react','rebut'); await W(300)
  await T.click('[data-a=create-save]'); await W(900)
  return await T.evaluate('S.roomId'), await T.evaluate('room().interact')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':1280,'height':900}); await c.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; T=await c.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(800)
    rid, inter = await make(T)
    ok('근거를 들어 답하기 설정 저장', inter=='rebuttal', inter)
    G=await c.new_page(); G.on('pageerror',lambda e:errs.append('G:'+str(e)))
    await G.goto(U+'?who=anon#'+rid); await G.wait_for_timeout(900)
    await G.fill('#g-nick','지우'); await G.press('#g-nick','Enter'); await G.wait_for_timeout(1400)
    if await G.locator('[data-a=to-stage]').count(): await G.click('[data-a=to-stage]'); await G.wait_for_timeout(500)
    key=await G.evaluate('Object.keys(S.form).find(k=>k.startsWith("write:"))')
    await G.evaluate(f'''(()=>{{const f=S.form["{key}"]; f._stance="친일 청산"; for(const x of effFields(room())) f[x.k]="나는 친일 청산이 먼저라고 생각한다. 독립운동가의 희생을 헛되게 하지 않기 위해서다. 정의로운 나라를 세우려면 과거를 바로잡아야 한다."}})()''')
    await G.evaluate('render()'); await G.wait_for_timeout(200)
    await G.click('#wsubmit'); await G.wait_for_timeout(900)
    ok('내 글 제출', await G.evaluate('!!myPost(room())?.submittedAt'))
    # 친구 글 하나를 넣고 ‘친구 생각 만나기’에서 연다
    await G.evaluate('''(()=>{const r=room(); S.posts.push({id:"fx1",roomId:r.id,author:"명문고 20627 유효정",stance:"국가 체제 정비",body:{claim:"나는 국가 체제 정비를 우선해야 했다고 생각한다.",reason:"해방 직후 나라가 혼란스러웠기 때문이다."},status:"submitted",submittedAt:Date.now(),createdAt:Date.now()}); S.work=r.id; S.openPost="fx1"; render()})()''')
    await G.wait_for_timeout(400)
    ok('친구 글 댓글 칸에 이유 칸', await G.locator('#comw-fx1').is_visible())
    ok('이유 필수 안내', await G.locator('.pc-hint').count()>=1)
    await G.locator('.pad-cmt').first.scroll_into_view_if_needed(); await G.locator('article.post.open').first.screenshot(path='/tmp/claude-0/shots/t101_box.png')
    await G.set_viewport_size({'width':390,'height':844}); await G.wait_for_timeout(200); await G.locator('.pad-cmt').first.scroll_into_view_if_needed(); await G.screenshot(path='/tmp/claude-0/shots/t101_m.png'); await G.set_viewport_size({'width':1280,'height':900})
    await G.fill('#com-fx1','혼란기에 안정도 중요하지만 청산도 같이 했어야 해'); await G.click('[data-a=save-comment][data-id=fx1]'); await G.wait_for_timeout(500)
    ok('이유 없으면 안 올라감', await G.evaluate('S.replies.filter(x=>x.postId==="fx1").length')==0)
    await G.fill('#comw-fx1','친일파가 다시 권력을 잡으면서 청산 기회가 사라졌기 때문이야'); await G.click('[data-a=save-comment][data-id=fx1]'); await G.wait_for_timeout(900)
    rp=await G.evaluate('S.replies.find(x=>x.postId==="fx1")')
    ok('근거 댓글로 저장(이유·게시판 표시)', bool(rp) and rp.get('kind')=='rebuttal' and rp.get('evidence','').startswith('친일파') and rp.get('via')=='board', rp)
    ok('친구 생각 만나기 완료', await G.evaluate('!!myPost(room()).readAt'))
    await G.evaluate('S.openPost="fx1"; S.work=null; render()'); await G.wait_for_timeout(300)
    h=await G.evaluate('replyHTML(room(), S.replies.find(x=>x.postId==="fx1"), postsOf(room().id))')
    ok('근거 표시 + 빨간 선 + 이유 칸', 'why-b' in h and 'reply rebut' in h and '이유' in h, h[:200])
    # 예전 ‘답’(이유 없음)은 그냥 댓글로
    old=await G.evaluate('replyHTML(room(), {kind:"rebuttal", author:"x", text:"국가 안정을 우선으로 생각하는게 좋다", evidence:"", createdAt:Date.now()}, [])')
    ok('이유 없는 예전 답은 댓글로', '>댓글<' in old and 'rebut' not in old and 'why-b' not in old, old[:160])
    # 내 글에는 이유 칸 없음, 이유가 필수가 아닌 활동은 ‘이유 붙이기’
    own=await G.evaluate('(()=>{const m=myPost(room()); return commentBox(room(), m, m)})()')
    ok('내 글 댓글 칸에는 이유 칸 없음', 'comw-' not in own and '이유 붙이기' not in own)
    free=await G.evaluate('(()=>{const r={...room(), interact:"comment"}; const f={id:"fx2",roomId:r.id,author:"다른 친구",body:{}}; return commentBox(r, f, myPost(room()))})()')
    ok('필수가 아니면 이유 붙이기(선택)', '이유 붙이기' in free and 'comw-' not in free)
    # 교사 화면도 ‘댓글’로
    T2=await c.new_page(); await T2.goto(U+'?who=teacher'); await T2.wait_for_timeout(700)
    th=await T2.evaluate('replyHTML({id:"z",stances:[]}, {kind:"rebuttal", author:"x", text:"t", evidence:"e", createdAt:Date.now()}, [])')
    ok('교사 화면도 댓글 · 근거', '>댓글 <i class="why-b">근거</i><' in th, th[:160])
    # 깊이 있게: 게시판 근거 댓글은 ‘친구 생각에 답하기’ 단계를 대신하지 않음
    d=await G.evaluate('''(()=>{const r={...room(), depth:"deep"}; const p=myPost(room()); const a=stepDone(r,p,"respond"); S.replies.push({id:"rr",roomId:r.id,postId:"fx1",author:p.author,kind:"rebuttal",text:"t",evidence:"e",differ:"d"}); const b2=stepDone(r,p,"respond"); return [a,b2]})()''')
    ok('깊이 있게: 게시판 근거 댓글로는 답하기 단계 미완료, 답하기 양식이면 완료', d==[False,True], d)
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails); raise SystemExit(1 if fails else 0)
asyncio.run(main())
