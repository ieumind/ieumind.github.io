# 출석부 빠른 입력: 하루 칸(한 번에) · 키보드(방향키·1/2/3/0)
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]; W=lambda pg,ms=200: pg.wait_for_timeout(ms)
    for vw in (1280,390):
      ctx=await b.new_context(viewport={'width':vw,'height':900}); await ctx.route(re.compile(r'https://.*'),lambda r:r.abort())
      T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(f'{vw}:'+str(e)))
      await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await W(T,800)
      await T.evaluate('document.querySelector(".hello [data-a=modal-close]")?.click()')
      await T.click(('' if vw>700 else '#qbar ')+'[data-a=roster-open]'); await W(T)
      await T.fill('#roster-add','한백고 20136 안소은\n한백고 20137 김연아\n덕계고 20428 박하늘'); await T.click('[data-a=roster-add]'); await W(T,500); await T.keyboard.press('Escape')
      await T.evaluate('attOpen({cid:"", ym:"2026-10"}); render()'); await W(T,300)
      await T.select_option('#att-wd','1'); await T.click('[data-a=att-month-days]'); await W(T)
      m=lambda sel: T.eval_on_selector_all(sel,'e=>e.map(x=>x.dataset.m).join("")')
      row=lambda n: f'.att tbody tr:has(th b:text-is("{n}"))'
      D='2026-10-12'
      ok(f'{vw} Tab으로 들어올 첫 칸이 있음', await T.evaluate('document.querySelectorAll("#att-wrap .ac[tabindex=\\"0\\"]").length')==1)
      ok(f'{vw} 하루 칸이 날짜마다 있음', await T.evaluate('document.querySelectorAll(".att tbody tr:first-child .ad").length')==4)
      # 하루 칸: ○ → △ → × → 비움 → ○
      seq=[]
      for k in range(5):
        await T.click(f'{row("안소은")} .ad[data-d="{D}"]'); seq.append(await m(f'{row("안소은")} .ac:not(.ad)[data-d="{D}"]'))
      ok(f'{vw} 하루 칸을 누를 때마다 3교시가 함께 바뀜', seq==['○○○','△△△','×××','---','○○○'], str(seq))
      # 한 교시만 바꾸면 하루 칸은 ◐, 누르면 모두 ○
      await T.click(f'{row("안소은")} .ac:not(.ad)[data-d="{D}"][data-i="1"]'); await W(T,50)
      ok(f'{vw} 섞이면 하루 칸이 섞임', await T.inner_text(f'{row("안소은")} .ad[data-d="{D}"]')=='섞임')
      await T.click(f'{row("안소은")} .ad[data-d="{D}"]')
      ok(f'{vw} 섞인 날은 하루 칸이 모두 ○로', await m(f'{row("안소은")} .ac:not(.ad)[data-d="{D}"]')=='○○○')
      # 키보드: 박하늘(첫 줄) 하루 칸에서 2 → 아래로 내려가 3 → 아래 0
      await T.focus(f'{row("박하늘")} .ad[data-d="{D}"]')
      await T.keyboard.press('2'); await T.keyboard.press('3'); await T.keyboard.press('0'); await W(T,100)
      ok(f'{vw} 키보드 하루 칸: 2·3·0 한 줄씩 내려가며 입력', [await m(f'{row(n)} .ac:not(.ad)[data-d="{D}"]') for n in ('박하늘','안소은','김연아')]==['△△△','×××','---'], str([await m(f'{row(n)} .ac:not(.ad)[data-d="{D}"]') for n in ('박하늘','안소은','김연아')]))
      foc=await T.evaluate('document.activeElement?.dataset.sid && attRoster("").find(x=>x.id===document.activeElement.dataset.sid)?.name')
      ok(f'{vw} 초점이 마지막 줄에서 멈춤', foc=='김연아', str(foc))
      # 교시 칸: 위로 올라가 1교시에서 1(○) 누르면 오른쪽 2교시로 이동
      await T.focus(f'{row("김연아")} .ac:not(.ad)[data-d="{D}"][data-i="0"]'); await T.keyboard.press('1'); await T.keyboard.press('2'); await W(T,100)
      ok(f'{vw} 교시 칸: 누르면 오른쪽 교시로 넘어가며 입력', await m(f'{row("김연아")} .ac:not(.ad)[data-d="{D}"]')=='○△-', await m(f'{row("김연아")} .ac:not(.ad)[data-d="{D}"]'))
      await T.keyboard.press('3'); await W(T,100)   # 3교시 ×
      foc=await T.evaluate('document.activeElement.classList.contains("ad")+":"+document.activeElement.dataset.d')
      ok(f'{vw} 마지막 교시 다음은 다음 날 1교시로 건너뜀(하루 칸 건너뜀)', foc=='false:2026-10-19', foc)
      # 방향키
      await T.focus(f'{row("박하늘")} .ac:not(.ad)[data-d="{D}"][data-i="0"]'); await T.keyboard.press('ArrowDown'); await T.keyboard.press('ArrowDown'); await T.keyboard.press('ArrowRight')
      pos=await T.evaluate('(()=>{const e=document.activeElement;return attRoster("").find(x=>x.id===e.dataset.sid).name+":"+e.dataset.i})()')
      ok(f'{vw} 방향키: 아래 둘·오른쪽 하나', pos=='김연아:1', pos)
      await T.keyboard.press('Home'); ok(f'{vw} Home은 줄 맨 앞', await T.evaluate('document.activeElement.dataset.d')=='2026-10-05')
      await T.keyboard.press('Backspace'); await W(T,100)
      # Tab은 표 안에서 한 번만 멈춤 (roving tabindex)
      ok(f'{vw} 칸이 하나만 Tab 대상', await T.evaluate('document.querySelectorAll("#att-wrap .ac[tabindex=\\"0\\"]").length')==1)
      # 저장·합계 (하루 칸과 키보드 입력이 합계에 반영)
      await W(T,1500)
      saved=await T.evaluate('JSON.parse(localStorage.getItem("__sbmock")).docs["attend/all_2026-10"].data.marks')
      ok(f'{vw} 키보드 입력도 저장됨', any('△△△' in v.values() for v in saved.values()))
      await T.screenshot(path=f'/tmp/claude-0/smoke/t78_{vw}.png')
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
