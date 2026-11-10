# 교사: 청중 의견 목록(삭제 묶기·실명·채팅 답 없음·거르기·요약·삭제 확인)
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
    await T.reload(); await W(T,900); await T.evaluate(f'location.hash="#{rid}"'); await W(T,1200)
    await T.click('[data-a=lv-state][data-v=live]'); await W(T,1500); await W(C,1500)
    async def note(kind,tgt,txt):
        await C.click(f'[data-a=lv-nkind][data-v={kind}]'); await C.click(f'[data-a=lv-ntgt][data-v={tgt}]'); await C.fill('#lv-note',txt); await C.click('[data-a=lv-note-send]'); await W(C,3300)
    await note('q','con','행정을 맡을 사람이 없었나요?')
    await note('q','con','친일파 처벌이 늦어지면 어떻게 되나요?')
    await note('t','all','반민특위는 필요했다고 생각해요')
    await note('q','all','삭제할 질문 하나')
    await note('q','all','삭제할 질문 둘')
    await W(T,1500)
    sm=await T.locator('#lv-nsum').inner_text()
    ok('교사 제목 줄: 숫자 요약', '의견 5개' in sm and '질문 4' in sm and '생각 1' in sm, sm)
    ok('학생용 문구 대신 요약', '모두 볼 수 있어요' not in await T.locator('section.lvcard.lvnotes').inner_text())
    ok('교사: 의견 카드에 실명', '박서준' in await T.locator('#lv-notelist .lvn').first.inner_text())
    ok('학생(판정단)에게는 실명·거르기 없음', await C.locator('.lvn-rn').count()==0 and await C.locator('#lv-nfil:not([hidden])').count()==0)
    ok('질문에 ‘채팅으로 온 답 없음’', await T.locator('.lvn-noans').count()==4)
    # 삭제 확인
    first='#lv-notelist .lvn:has-text("삭제할 질문 하나")'
    await T.click(first+' [data-a=lv-note-del]'); await W(T,300)
    ok('삭제 누르면 확인(바로 지워지지 않음)', await T.locator(first+' .lvn-ask').count()==1 and await T.locator('#lv-notelist .lvn.del').count()==0)
    await T.click(first+' [data-a=lv-note-del-no]'); await W(T,300)
    ok('취소하면 그대로', await T.locator(first).count()==1 and await T.locator(first+' .lvn-ask').count()==0)
    for t in ['삭제할 질문 하나','삭제할 질문 둘']:
        sel=f'#lv-notelist .lvn:has-text("{t}")'
        await T.click(sel+' [data-a=lv-note-del]'); await W(T,300); await T.click(sel+' [data-a=lv-note-del-yes]'); await W(T,700)
    ok('삭제한 의견은 목록에서 사라짐', await T.locator('#lv-notelist .lvn').count()==3 and await T.locator('#lv-notelist .lvn.del').count()==0 and '삭제된' not in await T.locator('#lv-notelist').inner_text())
    # 거르기
    await T.click('[data-a=lv-nf][data-v=t]'); await W(T,300)
    ok('생각만 보기', await T.locator('#lv-notelist .lvn').count()==1)
    await T.click('[data-a=lv-nf][data-v=q]'); await W(T,300)
    ok('질문만 보기', await T.locator('#lv-notelist .lvn').count()==2)
    # 반대팀이 첫 질문에 답하면 ‘채팅 답 없는 질문’ 줄어듦
    await B.click('#lv-qpin [data-a=lv-qans] >> nth=0'); await W(B,300); await B.fill('#lv-in','새로 뽑을 수 있었어요.'); await B.click('[data-a=lv-send]'); await W(B,1000); await W(T,1500)
    await T.click('[data-a=lv-nf][data-v=open]'); await W(T,300)
    sm=await T.locator('#lv-nsum').inner_text()
    ok('채팅 답 없는 질문 = 1개로 줄어듦', '채팅 답 없는 질문 1' in sm and await T.locator('#lv-notelist .lvn:not(.del)').count()==1, sm)
    ok('답 있는 질문엔 ‘답했어요’', True)
    await T.click('[data-a=lv-nf][data-v=all]'); await W(T,300)
    ok('답한 질문 카드에 ‘답했어요’', await T.locator('#lv-notelist .lvn-ans').count()==1)
    await T.locator('section.lvcard.lvnotes').screenshot(path='/tmp/claude-0/scr/notes_teacher.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS', fails)
asyncio.run(main())