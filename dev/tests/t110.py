# 논술·감상성찰 각각의 특장점: 논술=글쓰기 가이드·근거 설명, 감상성찰=느낌 말·전후 비교(논술 도구 없음)
import asyncio, re
from playwright.async_api import async_playwright
U='file:///tmp/claude-0/smoke/p26.html'
fails=[]
def ok(n,c,x=''):
  print(('PASS ' if c else 'FAIL ')+n,x)
  if not c: fails.append(n)
JS='''(args)=>{const [tpl,d]=args;applyTemplate(tpl);applyDepth(d);const f=createForm();const r=roomFromForm(f);
  return {steps:stepsOf(r).map(k=>[k,stepMeta(r,k).s,stepMeta(r,k).title]),fields:effFields(r).map(x=>x.k+":"+sField(r,x).q),
          f:r.features, miss:missionsFor(r).filter(m=>r.features.readMission.includes(m.k)).map(m=>m.k+":"+m.q)}}'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1280,'height':900}); await ctx.route(re.compile(r'https://.*'), lambda r: r.abort())
    T=await ctx.new_page(); errs=[]; T.on('pageerror',lambda e:errs.append(str(e)))
    await T.goto(U+'?who=teacher'); await T.evaluate('localStorage.clear()'); await T.reload(); await T.wait_for_timeout(700)
    await T.evaluate('document.querySelector("[data-a=create]").click()'); await T.wait_for_timeout(500)
    R={d:await T.evaluate(JS,['reflect',d]) for d in ('quick','normal','deep')}
    for d,n in (('quick',2),('normal',3),('deep',5)): ok(f'감상·성찰 {d}: {n}단계', len(R[d]['steps'])==n, [x[1] for x in R[d]['steps']])
    ok('감상·성찰 ①: 단계 이름이 느낌의 말', [x[1] for x in R['quick']['steps']]==['내 느낌','그렇게 느낀 이유'])
    ok('감상·성찰 ③: 활동 전 → 느낌 → 이유 → 친구 느낌 → 달라진 점', [x[1] for x in R['deep']['steps']]==['활동 전 생각','내 느낌','그렇게 느낀 이유','친구 느낌 만나기','달라진 점'], [x[1] for x in R['deep']['steps']])
    ok('감상·성찰 ③: 근거 설명·근거 유형 없음', not R['deep']['f']['warrant'] and not R['deep']['f']['evidenceType'] and not any(x.startswith('warrant') for x in R['deep']['fields']), R['deep']['fields'])
    ok('감상·성찰 ③: ‘비슷한/다른 느낌’ 임무', [m.split(':')[0] for m in R['deep']['miss']]==['same','diff'] and '느낀' in R['deep']['miss'][0] and '느낀' in R['deep']['miss'][1], R['deep']['miss'])
    ok('감상·성찰 ②: 임무 없이 가볍게', R['normal']['miss']==[])
    ok('감상·성찰 이유 질문이 느낌의 말', 'reason:왜 그렇게 느꼈나요?' in R['deep']['fields'], R['deep']['fields'])
    E={d:await T.evaluate(JS,['essay',d]) for d in ('deep',)}
    ok('논술은 근거 설명 유지', E['deep']['f']['warrant'] and any(x.startswith('warrant') for x in E['deep']['fields']), E['deep']['fields'])
    ok('논술 임무는 기존(설득력 중심)', [m.split(':')[0] for m in E['deep']['miss']]==['new','best','diff'], E['deep']['miss'])
    # 논술 글쓰기 가이드: 짧게(탭 4개 중 한 칸만), 문장 시작을 넣으면 다음 칸, 점검은 글 칸 아래
    await T.set_viewport_size({'width':375,'height':800})
    await T.evaluate('S.egStep=0; document.getElementById("app").innerHTML=`<div class="card"><div class="q"><label>한 편의 글로 써 보세요</label>${essayGuideHTML("x-text","정리한 내용")}<textarea id="x-text" rows="8"></textarea>${essayCheckHTML()}</div></div>`')
    ok('가이드: 탭 4개(내 생각·이유·근거·다른 생각·마무리)', await T.evaluate('[...document.querySelectorAll(".wg-t")].map(x=>x.innerText.replace(/\\s+/g,""))')==['1내생각','2이유·근거','3다른생각','4마무리'])
    ok('가이드: 처음엔 한 칸만 보임', await T.evaluate('[...document.querySelectorAll(".wg-p")].filter(p=>!p.hidden).length')==1)
    gh=await T.evaluate('document.querySelector(".wguide").getBoundingClientRect().height'); ok('가이드 높이가 짧음(휴대폰 240px 이하)', gh<=240, gh)
    await T.click('.wg-p:not([hidden]) .starter'); await T.wait_for_timeout(150)
    ok('문장 시작을 넣으면 쓰기 칸에 들어감', await T.evaluate('document.getElementById("x-text").value')=='나는 ')
    ok('넣은 뒤 다음 칸(이유·근거)으로 넘어감', await T.evaluate('document.querySelector(".wg-t[aria-selected=true]").dataset.v')=='1' and await T.evaluate('S.egStep')==1)
    await T.click('.wg-t[data-v="3"]'); await T.wait_for_timeout(100)
    ok('탭을 눌러 원하는 칸으로', '마무리' in await T.locator('.wg-p:not([hidden])').inner_text())
    await T.click('.wg-load'); await T.wait_for_timeout(100)
    ok('정리한 내용 불러오기', '정리한 내용' in await T.evaluate('document.getElementById("x-text").value'))
    ok('점검 목록은 글 칸 아래', await T.evaluate('!!(document.getElementById("x-text").compareDocumentPosition(document.querySelector(".wg-check")) & Node.DOCUMENT_POSITION_FOLLOWING)') and await T.evaluate('!document.querySelector(".wguide .wg-check")'))
    await T.screenshot(path='/tmp/claude-0/scr/essay_guide2.png')
    ok('에러 없음', not errs, errs)
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
