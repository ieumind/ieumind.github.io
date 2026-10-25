# 유튜브 주소 → 영상 그림(누르면 재생) · 코드 쪽지 인쇄는 새 창이 아니라 같은 화면(돌아가기 가능)
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    ctx=await b.new_context(viewport={'width':390,'height':800}); await ctx.route(re.compile(r'https://.*'),lambda r:r.abort()); T=await ctx.new_page(); T.on('pageerror',lambda e:errs.append(str(e)))
    popups=[]; ctx.on('page',lambda pg: popups.append(pg))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(900)
    L=lambda t: T.evaluate('t=>lnk(t)', t)
    h=await L('영상 https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s 보세요')
    ok('watch 주소 → 그림 1개, 시작 90초', h.count('class="yt-play"')==1 and 'data-v="dQw4w9WgXcQ"' in h and 'data-s="90"' in h and 'class="autolink"' in h, h[:80])
    ok('youtu.be · shorts 도 알아봄', 'data-v="abcdefghijk"' in await L('https://youtu.be/abcdefghijk') and 'data-v="abcdefghijk"' in await L('https://youtube.com/shorts/abcdefghijk'))
    ok('같은 영상 두 번이면 하나만', (await L('https://youtu.be/abcdefghijk 그리고 https://youtu.be/abcdefghijk')).count('class="yt-play"')==1)
    ok('유튜브가 아니면 그림 없음', 'yt-play' not in await L('https://example.com/watch?v=abcdefghijk 와 https://youtube.com/@channel'))
    ok('서식 글에서도 붙음', 'yt-play' in await L('⁣<b>보세요</b> https://youtu.be/abcdefghijk⁤'))
    ok('글 속 HTML은 그대로 막힘', '<script' not in await L('<script>alert(1)</script> https://youtu.be/abcdefghijk'))
    # 누르면 재생 창
    await T.evaluate('h=>{const d=document.createElement("div");d.id="ytbox";d.innerHTML=h;document.body.prepend(d)}', await L('https://youtu.be/dQw4w9WgXcQ?t=5'))
    await T.click('#ytbox .yt-play'); await T.wait_for_timeout(300)
    src=await T.evaluate('document.querySelector("#modal iframe")?.src||""')
    ok('누르면 영상 창(개인정보 보호 주소, 5초부터)', src.startswith('https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ') and 'start=5' in src, src)
    await T.evaluate('document.querySelector("#modal iframe").dataset.keep="1"; render()'); await T.wait_for_timeout(200)
    ok('다시 그려도 재생 중인 영상은 그대로', await T.evaluate('document.querySelector("#modal iframe")?.dataset.keep')=='1')
    await T.click('#modal [data-a=modal-close]'); await T.wait_for_timeout(200); ok('닫으면 사라짐', not await T.query_selector('#modal iframe'))
    await T.evaluate('document.getElementById("ytbox").remove()')
    # 코드 인쇄
    await T.evaluate('act("roster-open",{dataset:{}})'); await T.wait_for_timeout(700)
    await T.evaluate('S.roster=[{id:"a",number:"10301",name:"김가온",code:"K7P2QM"},{id:"b",number:"10302",name:"나다은",code:"ABCD23"}]; renderModal()'); await T.wait_for_timeout(200)
    await T.click('[data-a=roster-print]'); await T.wait_for_timeout(400)
    ok('인쇄 미리보기가 같은 화면에 열림(새 창 없음)', await T.is_visible('.rp-sheet') and not popups and '김가온' in await T.inner_text('.rp-sheet') and 'K7P2QM' in await T.inner_text('.rp-sheet'))
    ok('휴대폰: 돌아가기 줄이 있음', await T.is_visible('.sheet-back'))
    await T.screenshot(path='/tmp/claude-0/smoke/t74_rp.png')
    await T.emulate_media(media='print'); await T.wait_for_timeout(200)
    vis=await T.evaluate('[...document.body.children].filter(e=>e.tagName!=="SCRIPT"&&getComputedStyle(e).display!=="none").map(e=>e.id||e.className)')
    ok('인쇄할 때는 쪽지 외에 아무것도 안 나옴', vis==['modal'] and not await T.is_visible('.rp-note') and await T.is_visible('.rp-sheet'), str(vis))
    await T.emulate_media(media='screen')
    await T.click('.sheet-back'); await T.wait_for_timeout(300)
    ok('돌아가기 → 학생 명단으로 복귀', await T.evaluate('S.modal?.type')=='roster' and not await T.query_selector('.rp-sheet'))
    ok('페이지 오류 없음', not [e for e in errs if 'circle-half-2' not in e], str(errs[:3]))
    await b.close()
  print('\nFAILED:',fails) if fails else print('\nALL PASS')
asyncio.run(main())
