# 출석부: 날짜 넣기 · 칸 누르기(○→△→×→비움) · 사유 · 자동 저장 · 개별 안내(출석 현황)로 보내기 · 학생이 받기 · 엑셀
import asyncio, re, json
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=250: pg.wait_for_timeout(ms)
    for vw in (1280,390):
      ctx=await b.new_context(viewport={'width':vw,'height':900},accept_downloads=True); await ctx.route(re.compile(r'https://.*'),lambda r:r.abort())
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(f'{vw}:'+str(e)))
      await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
      await T.evaluate('document.querySelector(".hello [data-a=modal-close]")?.click()')
      # 명단 (학교 둘)
      await T.evaluate('act("roster-open", document.body)') if False else None
      if vw>700: await T.click('[data-a=roster-open]')
      else: await T.click('#qbar [data-a=roster-open]')
      await W(T); await T.fill('#roster-add','한백고 20136 안소은\n한백고 20137 김연아\n덕계고 20428 박하늘\n명문고 20627 유효정'); await T.click('[data-a=roster-add]'); await W(T,600); await T.keyboard.press('Escape'); await W(T)
      st=(await T.evaluate('JSON.parse(localStorage.getItem("__sbmock"))'))['students']; code={x['name']:x['code'] for x in st}
      # 출석부 열기
      if vw>700:
        ok(f'{vw} 좌측 메뉴에 출석부', await T.is_visible('#side [data-a=att-open]'))
        await T.click('#side [data-a=att-open]')
      else:
        await T.click('#qbar [data-a=msg-open]'); await W(T); await T.click('[data-a=msg-kind][data-v=attend]'); await W(T)
        ok(f'{vw} 개별 안내에 ‘출석 현황 안내’ 종류', await T.evaluate('MSGF().kind')=='attend')
        await T.click('[data-a=att-open][data-v=msg]')
      await W(T,500)
      ok(f'{vw} 출석부 창', await T.evaluate('S.modal?.type')=='attend' and '출석부' in await T.inner_text('#modal h3'))
      await T.fill('#att-ym','2026-10'); await W(T,300)
      await T.select_option('#att-wd','1'); await T.click('[data-a=att-month-days]'); await W(T,300)
      ok(f'{vw} 10월 월요일 4개', await T.evaluate('attGet("", "2026-10").dates.join()')=='2026-10-05,2026-10-12,2026-10-19,2026-10-26', await T.evaluate('attGet("", "2026-10").dates.join()'))
      ok(f'{vw} 학교·학번 순서', await T.eval_on_selector_all('.att tbody th b','e=>e.map(x=>x.textContent).join()')=='박하늘,유효정,안소은,김연아', await T.eval_on_selector_all('.att tbody th b','e=>e.map(x=>x.textContent).join()'))
      ok(f'{vw} 셀 12개씩(3교시×4일)', await T.evaluate('document.querySelectorAll(".att tbody tr:first-child .ac:not(.ad)").length')==12)
      await T.click('.att-hb[data-a=att-fill][data-v="2026-10-12"]'); await W(T,200)
      ok(f'{vw} 빈칸 ○', await T.evaluate('document.querySelectorAll(".att tbody .ac:not(.ad)[data-d=\\"2026-10-12\\"][data-m=\\"○\\"]").length')==12)
      # 안소은(둘째 줄) 10/12 1·2·3교시 → △
      row='.att tbody tr:has(th b:text-is("안소은"))'
      for i in range(3):
        await T.click(f'{row} .ac[data-d="2026-10-12"][data-i="{i}"]'); await W(T,60)
      ok(f'{vw} 한 번 누르면 △', await T.eval_on_selector_all(f'{row} .ac:not(.ad)[data-d="2026-10-12"]','e=>e.map(x=>x.dataset.m).join("")')=='△△△')
      ok(f'{vw} △ 사유 칸이 생김', await T.evaluate('document.querySelectorAll("#att-notes input").length')==1)
      await T.fill('#att-notes input','1차 정기시험 : 한백고등학교-13992(2026.9.18.)'); await W(T,200)
      # 연아 10/19 3교시 ×, 10/26 모두 ○ 후 2번 눌러 ×
      await T.click('.att-hb[data-a=att-fill][data-v="2026-10-19"]'); await T.click('.att-hb[data-a=att-fill][data-v="2026-10-26"]')
      r3='.att tbody tr:has(th b:text-is("김연아"))'
      for k in range(2): await T.click(f'{r3} .ac[data-d="2026-10-19"][data-i="2"]')
      ok(f'{vw} 두 번 누르면 ×', await T.eval_on_selector_all(f'{r3} .ac:not(.ad)[data-d="2026-10-19"]','e=>e.map(x=>x.dataset.m).join("")')=='○○×')
      for k in range(4): await T.click(f'{r3} .ac[data-d="2026-10-26"][data-i="0"]')
      ok(f'{vw} 네 번 누르면 도로 ○', await T.eval_on_selector_all(f'{r3} .ac:not(.ad)[data-d="2026-10-26"]','e=>e.map(x=>x.dataset.m).join("")')=='○○○')
      # 3번(연아) 마지막 줄 합계
      ok(f'{vw} 합계 칸', (await T.inner_text(f'{r3} [data-sum]')).replace('\n','')=='○8△0×1', await T.inner_text(f'{r3} [data-sum]'))
      # 날짜 지우기는 두 번 눌러야
      await T.click('.att-hb[data-a=att-deldate][data-v="2026-10-05"]'); await W(T,100)
      ok(f'{vw} 날짜 지우기 첫 클릭은 확인만', await T.evaluate('attGet("", "2026-10").dates.length')==4)
      await T.click('.att-hb[data-a=att-deldate][data-v="2026-10-05"]'); await W(T,200)
      ok(f'{vw} 두 번째 클릭에 지움', await T.evaluate('attGet("", "2026-10").dates.length')==3)
      # 저장 기다리기
      await W(T,1500)
      saved=await T.evaluate('JSON.parse(localStorage.getItem("__sbmock")).docs["attend/all_2026-10"]')
      ok(f'{vw} 서버(모의)에 저장', bool(saved) and len(saved['data']['dates'])==3, str(saved and saved['data']['dates']))
      ok(f'{vw} 저장 뒤 사본 정리', await T.evaluate('Object.keys(S.attDraft||{}).length')==0)
      # 새로고침 → 다시 열어도 그대로
      await T.reload(); await W(T,1000); await T.evaluate('document.querySelector(".hello [data-a=modal-close]")?.click()')
      await T.evaluate('attOpen({cid:"", ym:"2026-10"})'); await W(T,400)
      ok(f'{vw} 새로고침 뒤에도 기록', await T.evaluate('attGet("", "2026-10").marks && Object.keys(attGet("", "2026-10").marks).length')==4)
      ok(f'{vw} 사유도 그대로', '13992' in await T.input_value('#att-notes input'))
      # 엑셀
      async with T.expect_download() as dl: await T.click('[data-a=att-csv]')
      d=await dl.value; path=await d.path(); txt=open(path,encoding='utf-8-sig').read()
      ok(f'{vw} 엑셀 파일에 학생·기호·사유', '안소은' in txt and '△' in txt and '13992' in txt and txt.splitlines()[0].startswith('소속학교,학번,이름,10/12(월) 1교시'), txt.splitlines()[0][:60])
      # 이 달 출석 현황 안내 보내기
      await T.click('[data-a=att-send]'); await W(T,500)
      ok(f'{vw} 개별 안내 ‘출석 현황’으로 넘어옴', await T.evaluate('S.modal?.type+":"+MSGF().kind+":"+MSGF().at.ym')=='msg:attend:2026-10')
      ok(f'{vw} 기록 있는 4명이 미리 골라짐', await T.inner_text('#msg-count')=='4명', await T.inner_text('#msg-count'))
      prev=await T.inner_text('#at-prev'); print(prev)
      ok(f'{vw} 미리보기: 첫 학생(박하늘) 이름·월·합계', '박하늘 학생의 10월 출석 현황' in prev and '10월 합계: 출석 9교시 · 인정 0교시 · 결석 0교시' in prev, prev[:60])
      await T.screenshot(path=f'/tmp/claude-0/smoke/t77_msg{vw}.png')
      await T.click('[data-a=msg-send]'); await W(T,900)
      ok(f'{vw} 보냄', 'sent'==await T.evaluate('S.modal?.tab'), await T.evaluate('document.getElementById("toast")?.textContent'))
      ok(f'{vw} 보낸 안내에 ‘10월 출석 현황’', '10월 출석 현황' in await T.inner_text('.msent'))
      ok(f'{vw} 출석부에 ‘보냄’ 표시 저장', await T.evaluate('!!attGet("", "2026-10").sent'))
      # 학생(안소은)이 받는지
      K=await ctx.new_page(); K.on('pageerror',lambda e:errs.append(f'K{vw}:'+str(e)))
      await K.goto(U+'?who=anon'); await W(K,500)
      await K.fill('#f-num','20136'); await K.fill('#f-name','안소은'); await K.fill('#f-code',code['안소은']); await K.press('#f-code','Enter'); await W(K,1500)
      await K.evaluate('document.querySelector(".hello [data-a=modal-close]")?.click()'); await W(K,300)
      if await K.evaluate('S.modal?.type')!='inbox-pop': await K.reload(); await W(K,1500)
      big=await K.inner_text('.bigmsg') if await K.query_selector('.bigmsg') else ''
      ok(f'{vw} 학생 화면: 제목·인정 사유·예/아니오', '10월 출석 현황' in big and '인정: 1차 정기시험 : 한백고등학교-13992' in big and '△△△' in big and await K.evaluate('document.querySelectorAll(".askq").length')==2, big[:120].replace('\n',' | '))
      await K.screenshot(path=f'/tmp/claude-0/smoke/t77_stu{vw}.png')
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
