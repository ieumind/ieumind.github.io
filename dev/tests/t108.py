# 과목 없는 활동은 링크 전용: 로그인한 학생 목록에는 안 뜨고, 링크로 연 뒤에는 보인다
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
TITLE='링크전용테스트논제'
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
    await T.click('[data-a=create]'); await T.wait_for_timeout(300); await T.click('[data-a=goal][data-v=compare]'); await T.wait_for_timeout(300); await T.click('[data-a=tpl][data-v=live]'); await T.wait_for_timeout(300)
    await T.fill('#c-prompt',TITLE); await T.click('[data-a=create-save]'); await T.wait_for_timeout(1000); rid=await T.evaluate('S.roomId')
    st=await T.evaluate('(()=>{const r=S.rooms.find(x=>x.id===S.roomId);return [r.courseId||"", statusOf(r)]})()'); print('방',st)
    # 모의 서버는 익명 사용자에게 방을 안 주므로, 학생 신분(Auth.teacher=false) 페이지에 방 데이터를 직접 넣어 화면·판정 로직을 검사한다
    room=await T.evaluate(f'JSON.stringify(S.rooms.find(x=>x.id==="{rid}"))')
    K=await ctx.new_page(); await K.goto(U+'?who=anon'); await K.wait_for_timeout(1000)
    ok('학생 신분임', await K.evaluate('Auth.teacher')==False)
    await K.evaluate('localStorage.removeItem("ieum_linkrooms")')
    await K.evaluate(f'S.rooms=[JSON.parse({room!r})]; S.name="학생"; S.view="home"; render()'); await K.wait_for_timeout(500)
    q=f'(()=>{{const r=S.rooms.find(x=>x.id==="{rid}");return [!!visibleToStudents(r),linkOnlyHidden(r),listedToStudents(r)]}})()'
    info=await K.evaluate(q); print('링크 전',info)
    ok('링크 안 연 학생: 열려 있지만 목록에서는 제외', info==[True,True,False])
    ok('학생 홈 화면에 제목이 안 보임', TITLE not in await K.inner_text('body'))
    await K.evaluate(f'location.hash="#{rid}"; S.hashRoom="{rid}"; applyHash(); render()'); await K.wait_for_timeout(600)
    ok('링크로 열면 활동 화면이 열림', await K.evaluate('S.view')=='room' and await K.evaluate('S.roomId')==rid)
    ok('링크로 연 기록이 저장됨', rid in (await K.evaluate('localStorage.getItem("ieum_linkrooms")') or ''))
    await K.evaluate('S.view="home"; location.hash=""; render()'); await K.wait_for_timeout(500)
    info=await K.evaluate(q); print('링크 후',info)
    ok('한 번 연 뒤에는 목록에 보임', info==[True,False,True])
    ok('학생 홈 화면에 제목이 보임', TITLE in await K.inner_text('body'))
    ok('교사는 영향 없음', await T.evaluate(f'(()=>{{const r=S.rooms.find(x=>x.id==="{rid}");return !linkOnlyHidden(r)}})()'))
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
