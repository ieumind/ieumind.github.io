# 학습 나눔 파일 첨부: 기본 꺼짐 → 교사가 켜면 학생이 파일도 올리고, 교사·친구가 받아 볼 수 있다
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
IM='/tmp/claude-0/smoke/imgs/note1.jpg'; FD='/tmp/claude-0/smoke/files/'
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
    codes={s['name']:s['code'] for s in (await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']}
    await T.click('[data-a=create]'); await W(T); await T.click('[data-a=goal][data-v=notes]'); await W(T)
    ok('설정 기본값은 끔', await T.eval_on_selector('#c-nfiles','e=>e.value')=='', await T.eval_on_selector_all('#c-nfiles option','e=>e.map(x=>x.textContent)'))
    await T.click('[data-a=create-save]'); await W(T,700); rid=await T.evaluate('S.roomId')
    ok('저장된 활동 noteCfg.files 없음(끔)', not await T.evaluate(f'!!S.rooms.find(r=>r.id==="{rid}").noteCfg.files'))
    async def stu(nm):
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append('K:'+str(e))); await K.goto(U+'?who=anon#'+rid); await W(K,500)
      await K.fill('#g-nick',nm); await K.click('[data-a=guest-join]'); await W(K,1500); return K
    A=await stu('김가온')
    ok('끔: 학생에게 파일 첨부 버튼 없음', await A.locator('[data-note-attach]').count()==0)
    # 교사가 활동 화면에서 켠다
    ok('교사 화면에 파일 첨부 끔/켬 토글', await T.locator('[data-a=note-files]').count()==2)
    await T.click('[data-a=note-files][data-v=on]'); await W(T,600); await W(A,900)
    ok('켬: 학생에게 파일 첨부 버튼 생김(실시간)', await A.locator('[data-note-attach]').count()==1)
    ok('허용 확장자만 accept', '.pdf' in await A.get_attribute('[data-note-attach]','accept') and '.exe' not in await A.get_attribute('[data-note-attach]','accept'))
    # 거르기: exe, 11MB, 4개째
    await A.set_input_files('[data-note-attach]', FD+'evil.exe'); await W(A,300); ok('exe는 거절', await A.locator('.nfiles li').count()==0)
    await A.set_input_files('[data-note-attach]', FD+'big.pdf'); await W(A,300); ok('10MB 넘는 파일은 거절', await A.locator('.nfiles li').count()==0)
    await A.set_input_files('[data-note-attach]', [FD+'a.txt',FD+'b.txt',FD+'c.txt',FD+'d.txt']); await W(A,400); ok('최대 3개', await A.locator('.nfiles li').count()==3)
    await A.click('[data-a=nfile-rm][data-i="2"]'); await W(A,300); await A.click('[data-a=nfile-rm][data-i="1"]'); await W(A,300); ok('파일 빼기', await A.locator('.nfiles li').count()==1)
    await A.set_input_files('[data-note-attach]', FD+'report.pdf'); await W(A,300)
    ok('제출 버튼에 파일 수', '파일 2' in await A.inner_text('[data-a=note-submit]'), await A.inner_text('[data-a=note-submit]'))
    await A.click('[data-a=note-submit]'); await W(A,1800)
    ok('제출 완료(사진 없이 파일만)', '제출 완료' in await A.inner_text('.cta.done') and '파일 2개' in await A.inner_text('.cta.done'), await A.inner_text('.cta.done'))
    ok('학생 화면에 받기 링크', await A.locator('.nfiles a[download]').count()==2)
    href=await A.get_attribute('.nfiles a[download]','href'); ok('받기 주소가 있음', bool(href), str(href)[:40])
    # 교사 화면
    await T.evaluate('act("ttab",{dataset:{v:"students"}})'); await W(T,800)
    ok('교사 카드에 파일 표시', await T.locator('.ncard:has(.nfiles) .nfiles li').count()==2 and 'report.pdf' in await T.inner_text('.ncard:has(.nfiles)'), (await T.inner_text('.ncard:has(.nfiles)')).replace('\n',' | ')[:140])
    ok('사진 없으면 크게 보기 버튼 없음', await T.locator('.ncard:has(.nfiles) [data-a=note-view]').count()==0)
    # 서로 보기 + 친구
    B=await stu('나다은'); await B.set_input_files('input[data-note-file][multiple]', IM); await W(B,1200); await B.click('[data-a=note-submit]'); await W(B,1500)
    await T.click('[data-a=note-share][data-v=after]'); await W(T,600); await W(B,1000)
    ok('친구 화면에서 친구가 올린 파일이 보임', await B.locator('.ngal .nfiles li').count()==2, (await B.inner_text('.ngal')).replace('\n',' | ')[:140])
    ok('사진만 낸 학생 카드는 파일 목록 없음', '사진 1장' in await T.inner_text('.ncards'))
    # 끄면
    await T.click('[data-a=note-files][data-v=off]'); await W(T,600); await W(B,900)
    ok('끄면 다시 사진만(학생 버튼 사라짐, 낸 파일은 그대로 보임)', await A.locator('[data-note-attach]').count()==0 and await B.locator('.ngal .nfiles li').count()==2)
    # 수정 화면의 설정
    await T.evaluate('act("edit-room",{dataset:{id:"%s"}})'%rid); await W(T,500)
    ok('수정 화면에도 같은 설정(끔)', await T.eval_on_selector('#c-nfiles','e=>e.value')=='')
    await T.select_option('#c-nfiles','on'); await T.click('[data-a=create-save]'); await W(T,800)
    ok('수정 화면에서 켜면 저장됨', await T.evaluate(f'!!S.rooms.find(r=>r.id==="{rid}").noteCfg.files'))
    await A.screenshot(path='/tmp/claude-0/smoke/t82_student.png', full_page=True); await T.screenshot(path='/tmp/claude-0/smoke/t82_teacher.png')
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
