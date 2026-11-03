# 과목 카드 색 + 교사용 학생별 생각 흐름 모음
import asyncio, re
from playwright.async_api import async_playwright
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
W=lambda P,t: P.wait_for_timeout(t)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for w,dark in ((1280,False),(390,False),(390,True)):
      ctx=await b.new_context(viewport={'width':w,'height':900}, color_scheme='dark' if dark else 'light'); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
      P=await ctx.new_page(); P.on('pageerror',lambda e:errs.append(str(e)))
      await P.goto('file:///tmp/claude-0/smoke/pdemo.html?demo=1'); await W(P,800)
      await P.evaluate('S.tour=null; act("mcourse",{dataset:{v:"c-demo"}})'); await W(P,500)
      r=await P.evaluate('''()=>{const h=document.querySelector(".chead"),c=getComputedStyle(h);return {bl:parseFloat(c.borderLeftWidth),bg:c.backgroundColor,ic:!!h.querySelector(".chead-ic"),scope:!!document.querySelector(".cscope .cport")}}''')
      ok(f'{w}{"d" if dark else ""} 과목 카드 색 띠 7px·배경 색조·아이콘 원', r['bl']>=7 and r['ic'] and r['scope'], str(r))
      ok(f'{w}{"d" if dark else ""} 배경이 일반 카드와 다름', await P.evaluate('getComputedStyle(document.querySelector(".chead")).backgroundColor!==getComputedStyle(document.querySelector(".cport")).backgroundColor'))
      await P.screenshot(path=f'/tmp/claude-0/chead_{w}{"d" if dark else ""}.png')
      if w==390 and not dark or w==1280:
        await P.click('.cport > summary'); await W(P,400)
        await P.click('.cport-t tbody tr:nth-child(2) [data-a=port-student]'); await W(P,500)
        ok(f'{w} 학생 화면으로 이동', await P.evaluate('S.view')=='stu' and await P.is_visible('.stuhead'))
        h1=await P.inner_text('.stuhead h1'); ok(f'{w} 제목에 학생 이름', '생각 흐름 모음' in h1, h1)
        txt=await P.inner_text('#app'); ok(f'{w} 교사 시점 표현(‘내가 든 이유’ 없음)', '내가 든 이유' not in txt and '나의 생각 흐름 보기' not in txt)
        for view in ('map','list'):
          await P.evaluate(f'act("mine-view",{{dataset:{{v:"{view}"}}}})'); await W(P,400)
          n=await P.evaluate('document.querySelectorAll(".mmap-n,.pcard").length'); ok(f'{w} {view} 보기에 활동 표시', n>=1, str(n))
        # 목록에서 펼친 내용 + 활동으로 이동 버튼
        await P.evaluate('act("mine-view",{dataset:{v:"list"}})'); await W(P,300)
        await P.evaluate('document.querySelector(".pcard").open=true'); ok(f'{w} 활동에서 보기 버튼', await P.evaluate('!!document.querySelector(".pcard [data-a=port-open]")'))
        # 이전/다음
        name1=h1
        await P.click('[data-a=stu-nav][data-d="1"]'); await W(P,400); name2=await P.inner_text('.stuhead h1'); ok(f'{w} 다음 학생으로 바뀜', name2!=name1, f'{name1} -> {name2}')
        await P.click('[data-a=stu-nav][data-d="-1"]'); await W(P,400); ok(f'{w} 이전 학생으로 돌아옴', await P.inner_text('.stuhead h1')==name1)
        ok(f'{w} 안내 버튼', await P.is_visible('.stuhead [data-a=msg-open]'))
        # 가로 넘침 없음
        ok(f'{w} 가로 넘침 없음', await P.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        await P.screenshot(path=f'/tmp/claude-0/stu_{w}.png')
        await P.click('[data-a=stu-close]'); await W(P,400); ok(f'{w} 닫으면 과목 화면', await P.evaluate('S.view==="home"&&S.mcourse==="c-demo"') and await P.is_visible('.chead'))
      await ctx.close()
    ok('페이지 오류 없음', not errs, str(errs[:2]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
