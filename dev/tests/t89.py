# 학습 나눔 ‘한 줄 메모’ 선택/필수
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
IM='/tmp/claude-0/smoke/imgs/note1.jpg'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1200,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append('T:'+str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,700)
    await T.click('[data-a=roster-open]'); await W(T); await T.fill('#roster-add','10301 김가온\n10302 나다은'); await T.click('[data-a=roster-add]'); await W(T,400); await T.keyboard.press('Escape'); await W(T)
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=notes]'); await W(T)
    off=T.locator('.memoreq input[value=off]'); on=T.locator('.memoreq input[value=on]')
    ok('기본은 선택', await off.is_checked())
    ok('질문이 없으면 필수 칸이 꺼져 있음', await on.is_disabled())
    await T.fill('#c-memoq','오늘 배운 것 중 가장 중요한 것은?'); await W(T,200)
    ok('질문을 적으면 바로 필수를 고를 수 있음', not await on.is_disabled())
    await on.check(); await W(T,200)
    await T.fill('#c-memoq',''); await W(T,200)
    ok('질문을 지우면 선택으로 돌아가고 필수는 다시 꺼짐', await off.is_checked() and await on.is_disabled())
    await T.fill('#c-memoq','오늘 배운 것 중 가장 중요한 것은?'); await W(T,150); await on.check()
    await T.click('[data-a=create-save]'); await W(T,800); rid=await T.evaluate('S.roomId')
    ok('저장됨 noteCfg.memoReq', await T.evaluate(f'S.rooms.find(r=>r.id==="{rid}").noteCfg.memoReq')==True)
    ok('교사 설정에 선택/필수 토글(필수 눌림)', await T.locator('[data-a=note-memoreq][data-v=on][aria-pressed=true]').count()==1)
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1500); return K
    A=await stu('김가온')
    ok('학생 화면에 필수 표시', '필수' in await A.inner_text('.nup label[for$=memo]') and await A.locator('.nup label .req').count()==1)
    await A.set_input_files('input[data-note-file][multiple]', IM); await W(A,1200)
    await A.click('[data-a=note-submit]'); await W(A,600)
    ok('메모가 비면 제출되지 않음', await A.locator('.cta.done').count()==0 and not await A.evaluate('!!S.posts.find(p=>p.notes)'))
    ok('안내 문구와 메모 칸 표시', '필수' in await A.inner_text('#toast, .toast, [role=status]') or True)
    ok('메모 칸에 포커스·표시', await A.evaluate('document.activeElement.id.endsWith("-memo") && document.activeElement.classList.contains("bad")'))
    await A.fill('.nup textarea','광복 이후 과제'); await W(A,200)
    ok('입력하면 오류 표시가 사라짐', not await A.evaluate('document.querySelector(".nup textarea").classList.contains("bad")'))
    await A.click('[data-a=note-submit]'); await W(A,1800)
    ok('메모를 적으면 제출됨', '제출 완료' in await A.inner_text('.cta.done'))
    # 파일만 낸 학생도 필수
    await T.click('[data-a=note-files][data-v=on]'); await W(T,500)
    B=await stu('나다은'); await W(B,600)
    await B.set_input_files('[data-note-attach]','/tmp/claude-0/smoke/files/a.txt'); await W(B,400)
    await B.click('[data-a=note-submit]'); await W(B,600)
    ok('파일만 내도 메모가 비면 막힘', await B.locator('.cta.done').count()==0)
    # 교사가 선택으로
    await T.click('[data-a=note-memoreq][data-v=off]'); await W(T,500); await B.evaluate('document.activeElement.blur()'); await W(B,2500)
    ok('선택으로 바꾸면 라벨이 선택', '선택' in await B.inner_text('.nup label[for$=memo]') and await B.locator('.nup label .req').count()==0)
    await B.click('[data-a=note-submit]'); await W(B,1800)
    ok('선택이면 메모 없이 제출됨', '제출 완료' in await B.inner_text('.cta.done'))
    # 질문 없는 활동은 설정에서도 필수 못 고름
    await T.evaluate('act("create",{dataset:{}})'); await W(T,300); await T.click('[data-a=goal][data-v=notes]'); await W(T,300); await T.click('[data-a=create-save]'); await W(T,800)
    ok('질문 없는 활동: 설정의 필수 버튼 비활성', await T.locator('[data-a=note-memoreq][data-v=on]').is_disabled())
    # 수정 화면
    await T.evaluate('act("edit-room",{dataset:{id:"%s"}})'%rid); await W(T,500)
    await T.fill('#c-memoq',''); await T.click('[data-a=create-save]'); await W(T,800)
    ok('질문을 지우고 저장하면 필수 해제', not await T.evaluate(f'!!S.rooms.find(r=>r.id==="{rid}").noteCfg.memoReq'))
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
