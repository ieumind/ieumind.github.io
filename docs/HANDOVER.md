# 생각이음 · 개발 인수인계 문서

> 작성 시점: 2026-10-11 (한국 시각 저녁). 이 시점에 **main = `f2fc591`**(PR #15까지 병합 완료)이다.
> 아래 내용은 이 시점의 저장소 코드, 실제 Supabase 서버 상태, 지금까지의 대화를 근거로 적었다.
> “확인 못 함”이라고 적은 것은 실제로 검증하지 못한 것이다.

---

## 1. 프로젝트 개요

### 1-1. 서비스 목적
- **생각이음**은 중·고등학교 교사용 “생각 수업” 웹앱이다.
- 학생은 다음 순서로 활동한다.
  1. 내 생각을 쓴다.
  2. 우리 반 게시판에서 친구 생각을 만난다.
  3. 다시 생각을 고쳐 쓴다.
- 교사는 활동을 만들고, 학생의 생각 흐름과 참여 현황을 확인하고, 피드백한다.
- 만든 사람: 이태형 선생님(한백고). 화면 맨 아래에 “제작 : 이태형T(한백고)”가 표시된다.
- 공개 주소: <https://ieumind.github.io/> (2026-10-12 이전: `taeneuu.github.io/thinklink/` → 새 주소로 넘겨 주는 저장소만 남김)
  - 교사 로그인: `#teacher`
  - 체험 모드: `?demo=1`

### 1-2. 핵심 기능
**교사**
- **로그인과 가입**
  - 구글 로그인(Supabase Auth, Google OAuth, PKCE).
  - 구글로 로그인한 누구나 교사가 된다(teacher_checkin). 관리자는 교사를 막을 수 있다.
- **과목 대시보드**: 과목 카드에 공지, 진행 중 활동 수, 오늘 들어온 응답 수, 수강 학생 수를 보여 준다.
- **오늘 요약 타일**: 과목 · 진행 중 · 곧 마감 · 오늘 응답. 타일을 누르면 해당 활동만 걸러 보여 준다.
- **수강 학생**: 과목마다 학급별(학번 10301 → 1-3) 또는 한 명씩 고른다.
  - 서버 RLS로 막는다. 수강 학생에게만 과목·활동·글·댓글·알림이 간다.
- **과목 공지**: 최대 2개. 학생 앱 푸시 알림을 함께 보낼 수 있다.
- **활동 만들기**: 활동 유형과 깊이·고급 설정은 1-3 항목 참조.
- **🪄 AI 질문 추천**: 토론·질문 활동에서 키워드를 넣으면 Gemini가 논제·질문을 제안한다. 교사 본인의 Google AI Studio 키를 쓴다.
- **활동 관리 카드**: 📊 결과 보기 · 🔗 링크 · 👀 학생 화면 · ⋯(수정·복제·마감·보관·삭제).
- **결과 보기**: 학생별 사고 과정, 검색·필터, 피드백(개인·반 전체), 수업에서 함께 보기(발표 모드), CSV 내보내기.
- **그룹 배포**: 과목 안의 그룹(반·학교)마다 활동을 열고 닫고, 시작·마감 시각을 정한다.
- **학습 나눔(오늘의 필기)**: 미제출·조회만 함 필터, 조회 기록, 재제출 요청, 한 줄 메모에 교사 질문(`noteCfg.memoQ`). 복제는 활동 위쪽 ‘복제’ 버튼 하나만 쓴다.
- **👥 학생 코드**:
  - 나이스에서 복사한 “학번 이름”을 붙여 넣으면 개인 코드가 만들어진다. “학교 학번 이름” 형식도 된다.
  - 코드 쪽지를 인쇄할 수 있다.
- **👩‍🏫 교사 관리**(관리자만): 교사 목록 보기·막기, 💬 오류·건의 목록 확인·처리.

**학생**
- **로그인**: 학번 · 이름 · 개인 코드로 처음 한 번만 확인한다. 익명 인증 + `claim_student` 방식이다.
- **과목 대시보드**
  - “📚 내 과목” 카드와 “✏️ 해야 할 활동” 목록을 보여 준다.
  - 과목 화면에는 공지와 활동 카드가 있다.
  - 카드 라벨을 바꿀 수 있다: 게시일 / 마감 / 차시 / 단원.
- **우리 반 게시판**(패들렛 형식)
  - 내 생각을 게시하기 전에는 친구 글이 블러 처리된다(`reveal: "after"`).
  - 친구 글마다 ❤️ 하트와 💬 댓글을 달 수 있다.
- **푸시 알림**(Web Push): 새 활동과 공지를 알린다. 아이폰은 iOS 16.4 이상에서 홈 화면에 설치한 앱으로만 받는다.
- **📲 앱으로 설치 안내**: PWA.
- **📒 내 생각 기록**: 로그인 뒤에만 보인다.

**공통**
- 라이트/다크 테마 토글(☀️/🌙).
- 체험 모드: 로그인 없이 예시 반으로 쓴다. 저장되지 않는다. 🧭 둘러보기 9단계 튜토리얼이 있다.
- 소개 화면(교사 첫 화면)에 “생각 스케치 · AI 가상 인물 대화” 강조 박스가 있다.
- 화면 맨 아래 💬 오류·건의하기.

### 1-3. 활동 유형 (`TEMPLATES`, index.html 1064행 부근)
| 키 | 이름 | 비고 |
|---|---|---|
| `debate2` | 토론 (두 입장) | 🪄 AI 추천 대상. 추천에서 두 입장 이름도 채움 |
| `debateN` | 토론 (여러 입장) | 🪄 AI 추천 대상 |
| `inquiry` | 질문 활동 · 깊이 생각하기 | 질문 유형(사실적·개념적·논쟁적), 🪄 대상 |
| `relay` | 질문 활동 · 질문이음 | 🪄 대상(탐구 주제 추천) |
| `essay` | 논술 | |
| `reflect` | 감상·성찰 | |
| `sketch` | 생각 스케치 · 키워드 지도(가지치기) | 깊이: 빠르게·기본만 |
| `draw` | 생각 스케치 · 손으로 그리기 | 깊이: 빠르게·기본만 |
| `notes` | 📸 오늘의 필기 | 사진 1~12장(기본 3), Storage `notes` |
| `chat` | 🎭 가상 인물 대화 | Cloudflare Workers AI, 깊이: 빠르게·기본만 |
| `predict` | 예측과 확인 | 예전 유형(호환용) |

- 활동 목적 선택(`GOALS`): 토론 / 질문 활동 / 논술 / 감상·성찰 / 생각 스케치 / 오늘의 필기 / 가상 인물 대화.
- 고급 설정은 정리돼 있다.
  - 묶음 선택 3개(`data-combo`: start / react / end).
  - 체크 3개: 근거를 탄탄하게(evidence) / 교사 피드백 / 익명.
  - 설정을 바꿔도 패널이 닫히지 않는다(`details[data-keep]`, `S.advOpen`).

### 1-4. 사용 기술과 전체 구조
- **프런트엔드**: 빌드 도구 없는 단일 `index.html`(약 5,960줄). 바닐라 JS + CSS.
  - 외부 스크립트: supabase-js(CDN), QR 코드(qrcodejs, 필요할 때만).
- **호스팅**: GitHub Pages. 저장소 `ieumind/ieumind.github.io`(조직 사이트, 예전 `taeneuu/thinklink`)의 main 루트를 그대로 배포한다.
- **백엔드**: Supabase. 프로젝트 ref `zgwahesadlejacmxojfg`, 서울 리전.
  - Postgres(RLS) + Auth(Google, Anonymous) + Realtime + Storage + Edge Functions(Deno).
- **AI**
  - 학생 가상 인물 대화: Cloudflare Workers AI(`@cf/qwen/qwen3-30b-a3b-fp8`). Edge Function `chat`이 중계한다.
  - 교사 질문 추천: Google Gemini API. Edge Function `suggest`가 교사 본인 키로 호출한다.
- **푸시**: Web Push(VAPID). Edge Function `notify` + `sw.js`. 암호화는 WebCrypto로 직접 구현했다(RFC 8291/8292, npm 미사용).
- **실행 모드** (`S.mode`)
  1. `"supa"`: GitHub Pages + Supabase. 실제 운영 모드.
  2. `"local"`: 미리보기 또는 체험(`?demo=1` → `S.demo = true`). 저장되지 않는다.
  3. `"db"`: Claude 아티팩트 저장소(예전 호환). 지금은 거의 쓰지 않는다.

---

## 2. 현재 구현 상태

### 2-1. 완성·병합된 기능 (PR 순서)
| PR | 내용 |
|---|---|
| #1~#9 | Supabase 이전, 교사 간 데이터 격리, 학생 코드, 게시판 블러, 모바일 UI, 오늘의 필기, 테마, 설치 안내, 교사 자유 가입+관리자 막기, 소개 화면·체험 모드, 개인정보처리방침(privacy.html)·이용약관(terms.html), 학교 칸(공동교육과정) 등 |
| #10 | 학생 카드 라벨(게시일·마감·차시·단원), 체험 예시(최초의 인류 그리기, 아이히만 대화), 깊이·필기 사진 수 조정 |
| #11 | 가상 인물 대화를 Cloudflare Workers AI로 연결 |
| #12 | 고급 설정 정리, 패널이 닫히지 않게 |
| #13 | 과목 대시보드(학생), 과목 공지, Web Push 알림, 푸터·오류·건의하기 |
| #14 | 교사 대시보드 개편(인사·요약 타일·과목 카드), 체험 둘러보기 9단계, 🪄 AI 질문 추천(Gemini), 소개 화면 강조 박스, 예시 문구 교체(콜럼버스 토론, 일제 강점기 질문, 질문 유형 예시 3개) |
| #15 | 과목 수강 학생(학급별·개인별) + 서버 RLS, 과목별 알림(`push_targets_for`), 그룹 자동 지정, 게시판 ❤️·💬, 학생 코드 입력 화면 새 디자인, 로그인 전 “내 생각 기록” 숨김, 교사 화면 가시성 개선(타일 클릭, 카드 버튼 정리, 과목 색 띠, 마감 가까운 순), 새 과목 예시 문구 |

### 2-2. 최근 수정 사항 (PR #15, 커밋 `efef438`)
- **과목 수강 학생**
  - 저장 위치: `courses` 문서의 `data.members = [학생 uuid, …]`.
  - `members`가 없는 예전 과목과 과목에 넣지 않은 활동은 모든 학생에게 보인다(하위 호환).
  - 새 과목은 supa 모드에서 `members: []`로 만들어지고, 바로 학생 고르기 창(`memOpen`)이 열린다.
- **서버 RLS** (실서버 적용 완료)
  - 함수 추가: `course_for_me`, `room_for_me`. `room_open_to_peers`는 수강 여부까지 확인하도록 바꿨다.
  - `docs_read` / `docs_insert` / `docs_update` 정책을 갱신했다.
  - `chat_begin`도 수강 여부를 확인한다.
- **알림 대상**: `push_targets_for(p_course)` 추가. `notify` v2는 body에 `course`가 오면 그 과목 수강 학생에게만 보낸다.
- **❤️ 하트 저장 구조**
  - `replies` 컬렉션에 `kind: "heart"`, `on: true/false`로 저장한다.
  - 문서 id는 `"h-" + postId + "-" + heartKey(이름)`이고, 학생·글마다 하나다.
  - `repliesOf()`는 heart를 빼고 돌려준다. 그래서 기존 댓글 수와 통계에는 영향이 없다.
- **💬 댓글**: 게시판에서 펼친 글(`readCard`, `pickable:false`)에 `wallActs` + `commentForm`을 보여 준다. 기존 `save-comment` 액션을 그대로 쓴다.
- **그룹 기억**: `groupKey(cid)`로 학생별로 저장한다. 예전 키 `nonjae.group.<cid>`도 읽는다.
  - 자동 지정(`autoGroup`): 그룹 이름이 학급(`1-3`, `1학년 3반`)이나 학교와 같으면 지정된다.

### 2-3. 정상 작동 여부
| 항목 | 상태 |
|---|---|
| 교사 구글 로그인, 학생 코드 로그인 | 사용자 실사용으로 확인됨 |
| 교사 간 데이터 격리 | 로컬 Postgres RLS 테스트 + 실서버 적용 |
| 과목 수강 RLS | 로컬 Postgres에서 시나리오 검증(`dev/sql/mem_test.sql`). 비수강생은 과목·활동·글이 안 보이고, 글쓰기는 거부되고, `chat_begin`은 denied. 추가하면 보임. 실서버 적용 완료 |
| 화면 흐름 전체 | Playwright + 가짜 Supabase(`dev/tests/mock.js`)로 검증, 오류 없음 |
| **Web Push 실제 기기 수신** | **확인 못 함**(실기기 테스트 없음). 암호화·서명은 Node로 복호화·검증함 |
| **Gemini `suggest` 실제 호출** | **확인 못 함**. 작업 환경에서 외부 접속(supabase.co, googleapis)이 프록시로 막혀 있었다. 키 넣고 “저장하고 확인”으로 첫 검증 필요 |
| Cloudflare AI 대화 | 사용자가 Secrets 등록 절차를 진행함. 이 작업 환경에서 실제 응답을 직접 확인하지는 못함 |
| 실서버 기존 과목 | “한국사2 온라인 공동교육과정 A반” 1개(그룹 `1-3`), `members` 없음. 수강 학생을 고르기 전까지 **모든 학생에게 보인다** |

### 2-4. 추가 수정 (PR #16, 2026-10-11 밤)
- **과목 만들기·수정 창 하나에서** ① 과목 정보 ② 수강 학생(학급 칩·검색·개별 체크) ③ 그룹(학생으로 짓기: 학생 줄 오른쪽에서 그룹 고르기, ‘학급별로 나누기’)을 한 번에 정한다. 예전 ‘수강 학생’ 별도 창(`members` 모달)은 없앴고, `mem-open`은 과목 수정 창(학생 칸)으로 연결된다.
  - 저장: `courses.members = [학생 id]`, `courses.groups[].members = [학생 id]`. 학생 명단을 못 불러온 상태에서는 기존 members를 지우지 않는다.
- **학생 그룹 = 선생님이 정한 그룹**: 그룹에 학생이 들어 있으면(`groupByTeacher`) 학생이 그룹을 고르지 않는다. 학생 기기는 로그인 때 `my_student_ids()` RPC(새로 추가, 실서버 적용)로 내 학생 번호를 받아 `S.mySids`에 둔다. 어느 그룹에도 없으면 `myGroup()`이 `"_none"`을 돌려주어 그룹 배포 활동이 보이지 않는다.
- **결과 화면 미참여/미제출 기준**: `courseRoster(r, gid)` — 과목에 수강 학생이 정해져 있으면 그 학생(그룹 보기면 그 그룹, 일부 그룹에만 배포한 활동이면 그 그룹들)만 기준으로 센다. 수강 학생을 안 정한 과목·과목 없는 활동은 예전과 같다.
- **깊이 = 생각이음 흐름**: ① 생각(quick) / ② 생각 → 만남(normal, 새로 만들 때 `change:false`) / ③ 생각 → 만남 → 변화(deep). 칩·규칙 표시는 저장된 기능으로 계산하는 `depthLabel(r)`을 쓴다(예전 활동도 실제 단계대로 표시). `DEPTHS[*].features`(예전 활동의 기본값)는 바꾸지 않았다.
- 과목 이름 고딕 굵게, 과목 머리 한 줄 정리(👥 학생 n명 · 🔗 과목 링크 · QR · ✏️ 과목 수정), 📢 공지는 기본 접힘 + ‘🔔 알림도 보내기’ 토글을 ‘공지 올리기’ 옆에, 활동 카드 아래 관리 줄(✏️ 수정 · 📑 복제 · ⏹ 마감 · 🗄 보관 · 🗑 삭제, 클래스 `mctools` — 활동 검색 칸 `mtools`와 다름), 활동 결과 화면 버튼 아이콘 통일 + 🗄 보관, 그룹 없는 과목·과목 없는 활동에서는 ‘그룹 배포’ 칸을 숨김.
- 테스트: `dev/tests/t36.py`(과목 창·그룹·깊이·결과 기준). 예전 `t35.py`는 지웠다.

### 2-5. 추가 수정 (PR #18, 2026-10-12)
- **AI 키 저장이 ‘확인하는 중…’에서 멈춘 문제**: 원인은 PR #17 병합 직후 브라우저가 옛 화면(rpc `.catch` 오류 버전)을 쓰고 있었던 것(서버 기록상 ai_key_set 요청이 아예 오지 않음). 그래도 다시 멈추지 않게 `invokeSafe()`(시간 제한) + `try/finally`로 버튼을 항상 되돌린다. `suggest` v2: 모델마다 20초, 전체 40초 제한.
- **새 활동 화면 정리**: ③ 깊이 카드 = 번호·이름·한 줄 설명·시간만(중복 칩 제거). 선택 표시는 저장될 기능으로 계산(`stg`). 학생 미리보기는 💭 생각 / 👀 만남 / 🔄 변화로 묶어 보여 줌(`STAGE_OF`). ④는 ‘누구와, 언제까지’(과목·그룹·마감 한 카드).
- **⚙️ 세부 설정 = 단계별**: 💭 생각(작성 방법 칩 6개 `TOOL_PICK`, ③일 때만 ‘처음 생각 먼저 남기기’, 근거를 탄탄하게, 최소 글자 수) / 👀 만남(게시판 공개 `REVEAL_L`, ② 이상에서 반응 방법 3가지) / 🔄 변화(③일 때만 마무리 3가지) / 그 밖에(피드백·익명). ‘예측하고 비교하기’ 선택지는 없앴다(예전 활동의 predict 기능은 그대로 동작). 작성 방법 목록에서 반론–재반론·생각의 변화·예측–이유는 뺐다(예전 활동은 그대로).
- 테스트: `t38.py`(새 활동 화면). 예전 `t28.py`는 지웠다.

### 2-6. 추가 수정 (PR #19, 2026-10-12)
- **🔄 새 버전 알림 (배포 규칙!)**: `index.html`의 `APP_VERSION`과 저장소 루트 `version.json`의 `v`를 **배포할 때마다 같은 새 값으로 올린다**. 옛 화면을 쓰는 브라우저는 아래쪽에 ‘새로고침’ 띠가 뜨고, 누르면 주소에 `?v=새값`을 붙여 새로 받는다(GitHub Pages 10분 캐시 대응). 지금 값: `2026-10-12c`.
- **오류·건의 보내기**: 서버 기록상 요청이 한 번도 오지 않음 → 옛 화면(`.catch` 오류) 때문으로 판단. 추가로 모달을 다시 그려도 쓰던 글이 남게(`renderModal`에서 `fb-body` 보존), ‘보내는 중…’ 표시.
- **논술(essay) 깊이 버튼**: 논술은 기본 공개가 ‘선생님만 보기’라 ②③을 눌러도 1단계로 계산돼 눌리지 않았다 → `applyDepth`에서 ②③이면 게시판을 ‘내 글 올린 뒤 열림’으로, ①이면 활동 기본값으로. 미리보기에서 선생님 피드백 단계는 따로 표시(`STAGE_OF.feedback = -1`).
- **패들렛 쪽지**: `padHead`(동그란 이름표·이름·상대 시간) + `padText`(첫 칸이 짧으면 굵은 제목) + ❤️/💬 줄 + ‘＋ 댓글 추가’. 쪽지 색은 글 id로 정하는 옅은 6색(`--pad0~5`, 다크 모드 따로). 펼친 글의 댓글 칸은 한 줄 입력(`.pad-cmt`).
- **교사 ‘학생 생각’ 카드**: 상태 색 띠(완료 초록/진행 노랑), 굵은 첫 줄+본문, ❤️·💬·피드백 수, 마지막 피드백 한 줄, **💬 바로 피드백**(빠른 문구 칩 `QUICK_FB` + 보내기, 상세로 들어가지 않고), 📽 발표 토글, ‘사고 과정 →’.
- 테스트: `t41.py`.

### 2-7. 추가 수정 (PR #20, 2026-10-12)
- 오늘의 필기 안내는 빈칸 + 회색 예시(`NOTES_PROMPT`). 비워 두고 만들면 그 문장으로 저장. 예전에 자동으로 채워진 문장은 지움.
- 질문 활동 방식 카드에 `modeWho` 배지: 깊이 생각하기 = 👩‍🏫 선생님 질문 → 🧑‍🎓 학생 답, 질문이음 = 🧑‍🎓 학생 질문 → 🧑‍🎓 친구 답.
- 세부 설정 간격을 줄임(`.adv-sec`).
- 접힌 공지 줄에 공지 2개를 나란히(①·② 번호).
- `lnk()`: 글 속 http/https 주소를 링크로(공지, 활동 질문·소개·자료, 선생님 피드백·반 전체 피드백). 학생 글·댓글은 링크로 바꾸지 않는다.
- 테스트: `t42.py`.

### 2-8. 추가 수정 (PR #21, 2026-10-12)
- 교사 화면 상단에도 📲 앱으로 설치 버튼(설치된 앱에서는 숨김).
- 체험(demo): '최초의 인류…'·'아이히만에게 묻다'를 새 과목 `c-demo2` "2학년 세계사"에 배정.
- 튜토리얼에 3단계 추가: ‘결과 보기’ → ‘학생 생각’ → 결과물 카드(`.scards`). `TOUR[i].on = {a, id|v}` 단계는 실제 버튼을 누르면 `act()` 앞부분에서 다음 단계로 넘어간다.
- '+ 새 과목' 카드 문구에서 "예: 1학년 통합과학" 삭제.
- 친구 생각 읽기(read 단계)를 댓글로 일원화: '이 생각을 고를래요/한마디 남기기' 대신 카드의 댓글(`save-comment`). 첫 댓글이 read 단계를 끝낸다(`readAt`, `meet.diffPostId`). 반박·읽기 미션이 있으면 댓글 뒤 '다 읽었어요'를 눌러야 넘어간다.
- 토론: 포스트잇 색 = 입장 색(`wallTone`이 `--s1..s4-soft`), 입장 칸은 흰 바탕 + 입장 색 윗줄.
- `srcBox(r)`: 📚 자료 상자 기본 열림(`data-keep="src-"+id`, 여닫기 기억), 글씨·여백 키움, 링크 자동, 사진 격자.
- 자료 사진 최대 10장(`room.ctxImgs`): 실서비스는 Storage 공개 버킷 `materials`(교사만 자기 uid 폴더에 올림·지움, 5MB, jpeg/png/webp)에 올리고 공개 주소 저장, 체험·로컬은 dataURL. setup.sql에 반영, 서버에는 마이그레이션 `materials_bucket`으로 적용됨. ※ 공개 주소라 주소를 아는 사람은 볼 수 있음 → 학생 개인정보 사진은 넣지 않도록 안내.
- `APP_VERSION`/`version.json` = `2026-10-12d`.
- 테스트: `t43.py`.

### 2-9. 추가 수정 (PR #22, 2026-10-12)
- 체험 공지: 1학년 한국사 = 광복 1945 게임 링크, 2학년 세계사 = 컴퓨터실 공지.
- 체험 예시 교체: `park-modern` → `joseon-minbon`(조선 민본과 신분제, 깊이 생각하기·개념적), `park-relay` → `comfort-relay`(일본군 ‘위안부’ 문제 질문이음, 예시 질문 2개).
- ⏱ 수업 타이머: '과제/실시간' 모드를 나누지 않고, 선생님이 활동 화면(`tmrPanel`)에서 필요할 때 켜는 방식.
  - `room.timer = {dur, endsAt, left, at}`(진행: endsAt / 멈춤: left / 끝: endsAt 지남). 저장은 `setTimer` → rooms 문서 update(실시간으로 학생에게 전달). DB 변경 없음.
  - 버튼: 3·5·10·15·20분(+활동의 예상 시간), 직접 입력, +1분, 잠시 멈춤/이어서, 끝내기. 오늘의 필기는 과제라 패널 없음.
  - 학생: 활동 화면 맨 위 고정 띠(`tmrBarStudent`, 1분 남으면 빨강, 끝나면 "마무리해 주세요" 10분 표시), 첫 화면에 "⏱ 지금 수업 중" 바로가기(`.livebar`), 과목 안 카드에 남은 시간.
  - 📽 수업에서 함께 보기 화면 위쪽에도 남은 시간.
  - 1초 타이머는 `[data-tmr]` 숫자만 바꾸고, 상태가 바뀔 때만 `render()`.
  - 한계: 기기 시계 기준이라 시계가 크게 틀린 기기는 몇 초~분 차이가 날 수 있음(처음 시간보다 길게는 안 보이게 막음).
- `APP_VERSION`/`version.json` = `2026-10-12e`.
- 테스트: `t44.py`.

### 2-10. 추가 수정 (PR #23, 2026-10-12)
- 활동 만들기 ③ 카드 안에 ‘👀 학생은 이렇게 활동해요’를 넣어 한 상자로 합침.
- 깊이 버튼의 시간(예전 고정 문구 `DEPTHS.use`: 5~10분/한 차시/…)을 실제 예상 시간으로: 고른 깊이는 `estMinutes(preview)`, 나머지는 폼 복사본에 `applyDepth(k, g)`를 적용해 같은 식으로 계산(`applyDepth`가 폼을 인자로 받게 바꿈).
- 수업 정보 라벨 ‘연도·차시’ → ‘차시·연도’.
- `APP_VERSION`/`version.json` = `2026-10-12f`. 테스트: `t45.py`.

### 2-11. 추가 수정 (PR #24, 2026-10-12)
- 휴대폰(≤640px) 넘침 정리: 위쪽 버튼은 옆으로 밀지 않고 줄바꿈 + 짧은 이름(`.lt` 숨김), 과목 머리(`.chead`)·활동 머리(`.ahead`) 격자에 `minmax(0,1fr)`, 긴 칩은 말줄임, 활동 탭은 3칸 격자, 요약 숫자 3칸, 활동 관리 버튼은 격자.
- 휴대폰에서는 링크 복사와 QR을 `🔗 링크·QR` 하나로(`.pc-only`/`.m-only`). QR 창에 링크 복사 버튼이 있다.
- 활동 유형마다 질문 칸 이름·회색 예시(`PROMPT_LP`).
- ④의 과목 고르기·마감 칸 높이 44px로(`.form-grid > .q{align-content:start}`).
- 긴 과목 이름: `mq()` + `mqFit()`(render 뒤·창 크기 바뀔 때). 넘칠 때만 한 줄에서 좌우로 천천히 흐름, 움직임 줄이기 설정이면 말줄임.
- 📊 학생별 활동 현황(과목 포트폴리오, `coursePortfolio`): 과목 화면에서 접어 두고 펼칠 때만 계산(`details[data-lazy]`). 학생 × 활동 칸(✓ 완료 · … 하는 중 · · 아직 안 함), 칸 → 그 학생 사고 과정(`port-open`), 이름 → 학생 포트폴리오 창(`port-student`). 이미 불러온 글로만 계산(서버 요청 없음). 둘러보기에 단계 추가.
- `APP_VERSION`/`version.json` = `2026-10-12g`. 테스트: `t46.py`.

### 2-12. 추가 수정 (PR #25, 2026-10-12)
- 마키 속도 높임: `--mq-t = max(2.5, 넘친 px/70 + 1.6)초`, 멈춤 구간 12%.
- 👀 조회 기록(DB 추가, 비파괴): 표 `room_views(tid, room_id, student_id, first_at, last_at, n)` — RLS 켜고 아무 권한 없음.
  - `room_view(p_room)`: 학생이 활동을 열면(이름 확인 뒤 `viewRoomStudent` → `markViewed`) 페이지당 활동마다 한 번 호출. 수강 학생(room_for_me)만 남는다.
  - `room_viewers(p_room)`: 교사 본인 활동만. 교사 활동 화면에서 `viewersOf(r)`가 30초마다 새로 읽고, 학생 id → 명단 이름표로 바꾼다.
  - 화면: 요약 숫자 맨 앞 ‘👀 조회 n/전체’(참여한 학생 포함), 참여 현황 표 위 요약(조회·참여·조회만·안 들어옴), 학생 줄 상태 ‘👀 조회만 함’과 마지막 조회 시각. 체험은 `S.demoViews`.
  - setup.sql 반영, 서버에는 마이그레이션 `room_views`로 적용. 로컬 검사: `dev/sql/views_test.sql`.
  - 이 기능 이전에 연 기록은 없다(그때 글을 쓴 학생은 참여로 셈).
- `APP_VERSION`/`version.json` = `2026-10-12h`. 테스트: `t47.py`.

### 2-13. 추가 수정 (PR #26, 2026-10-12)
- 과목 카드는 처음에 3개만(`COURSE_SHOW`), ‘＋ 과목 n개 더 보기’/‘접기’(교사 `courses-more`·학생 `dash-more`, 이번 접속 동안만 기억).
  - 교사: 최근에 쓴 과목 순(`courseRecent`: 과목·활동 수정 시각·공지). ‘과목 없는 활동’과 ‘＋ 새 과목’ 카드는 늘 보임.
  - 학생: 할 일·새 활동이 있는 과목이 앞에.
- 과목 보관(`courses.data.archived`, `archivedAt`): 과목 수정 창의 ‘🗄 보관’, 보관한 과목 머리의 ‘보관 해제’(`course-archive`).
  - 교사: ‘내 과목’ 목록·요약 숫자·‘모든 활동’ 목록·활동 만들기의 과목 고르기에서 빠지고, ‘🗄 보관한 과목 n개’를 펼치면 보인다. 그 과목에 들어가면 활동이 그대로 보인다.
  - 학생: 대시보드·해야 할 활동에서 빠진다(화면에서만 숨김, 권한은 그대로 → 링크로 들어오면 열리고 ‘내 생각 기록’에도 남음).
  - 과목을 저장(수정)해도 보관 상태 유지.
- `APP_VERSION`/`version.json` = `2026-10-12i`. 테스트: `t48.py`.

### 2-14. 추가 수정 (PR #27, 2026-10-12) · 저장소를 `ieumind/ieumind.github.io`로 옮긴 뒤 첫 PR
- 저장소·주소 이전: `https://ieumind.github.io/`. `notify`의 VAPID subject를 새 주소로(배포 v3). 예전 주소는 개인 계정의 `taeneuu/thinklink` 저장소(넘겨 주기 index.html·404.html·sw.js)로 새 주소에 넘긴다.
- 👥 한 학생이 여러 선생님 과목 듣기: 상단 ‘＋ 과목 추가’(`join-open` → `joinHTML` → `join-save` = `claim_student`)로 다른 선생님이 준 개인 코드를 넣으면 이 기기에 그 선생님이 더 연결된다(student_sessions는 원래 (uid, tid)마다 한 줄). 성공하면 새로 불러오고 안내.
  - 선생님마다 명단 이름표가 다를 수 있다(학교 이름 등) → 새 함수 `my_students()` = [{tid, sid, name}] (setup.sql·서버 마이그레이션 `my_students`). `S.idents`, `S.myNames`.
  - 문서마다 선생님(tid)을 `DOC_TID`에 기억(`select id,data,tid`, 실시간도). 글·댓글·하트를 쓸 때 `meFor(roomId)` = 그 활동 선생님의 이름표, ‘내 글인가’는 `isMe(author)`.
  - 로컬 검사: `dev/sql/multi_teacher_test.sql`(이름표가 틀리면 RLS가 막는 것까지). 가짜 Supabase(mock.js)에 선생님 두 명(`?who=teacher2`, 문서·학생에 tid) 추가.
- 과목 정렬: 사용자 지정(기본)·오래된 순·최신순(`CSORTS`, 이 기기에 `nonjae.csort`). 사용자 지정에서 ‘↔ 순서 바꾸기’ → 카드를 끌어 놓기(PC) 또는 ◀ ▶(휴대폰은 ▲ ▼).
  - 교사: 과목 문서 `ord`(여러 기기에서 같은 순서, 과목 저장해도 유지). 학생: 이 기기의 `nonjae.corder`.
  - 앞서 넣은 ‘최근에 쓴 순’(교사)·‘할 일 있는 과목 먼저’(학생) 자동 정렬은 이 설정으로 바뀌었다.
- `APP_VERSION`/`version.json` = `2026-10-12j`. 테스트: `t49.py`.

### 2-15. 추가 수정 (PR #28, 2026-10-13)
- 🔔 알림은 과목이 있는 활동·공지만:
  - 활동 만들기의 ‘🔔 학생 알림’ 칸은 과목을 골랐을 때만 보인다(`roomPushOn`).
  - `notify` 함수(v4)는 course가 없으면 보내지 않는다(`no_course`).
  - 예전 `push_targets_for`는 없는 과목이면 모든 학생에게 보내던 것을 막았다(→ `course_push_targets`).
- 👥 그룹별 공개(추천: 활동은 하나, 그룹마다 공개 상태·시각 — 결과를 한곳에서 그룹별로 비교):
  - 활동 만들기 ④에 그룹마다 ‘바로 공개 / ⏰ 공개 예약(시각)’ + 그룹 마감(`gsm:/gsa:/gsd:<그룹>` 폼 값 → `assign[g] = {status:"ready", startAt}`).
  - 수정할 때 `formFromRoom`이 다시 채운다. 예전 ‘그룹 배포’ 카드(활동 화면 개요)도 그대로 쓸 수 있다.
- 그룹 알림:
  - 공개할 때 지금 열린 그룹 학생에게만(`notify`에 groups → `push_targets_groups`). 그룹에 학생 명단이 없으면(학생이 고르는 그룹) 과목 전체에 보낸다.
  - 개요 카드에서 ‘시작 전→진행 중’으로 바꾸면 그 그룹에 알림.
  - 활동에 `notify:false`면(만들 때 끔) 알림·예약 없음.
- ⏰ 예약 알림(서버, 비파괴 추가):
  - `push_jobs` 표: 활동·그룹마다 하나, RLS 켜고 권한 없음.
  - `push_schedule()`: 교사만, 과목 활동만, 120일 안. 시각이 지났거나 열린 그룹이면 예약을 지운다.
  - `push_due_take()`: service_role만. 마감·작성 중·보관 활동, 종료 그룹은 건너뜀.
  - pg_cron 작업 `push-due`가 1분마다, 때가 된 예약이 있을 때만 pg_net으로 `notify-due` 함수(verify_jwt 끔, `x-cron-key` = `app_secrets.cron_key` 확인)를 부른다.
  - 클라이언트 `schedSync(r)`가 저장·그룹 상태/시각 변경 때마다 맞춘다.
  - setup.sql에 반영(pg_cron/pg_net 없으면 건너뜀, `functions_url`은 직접 넣기). 서버에는 마이그레이션 `group_push_and_schedule`로 적용. 로컬 검사 `dev/sql/group_push_test.sql`.
- 주의: 그룹 공개는 지금처럼 화면에서 거르는 방식(같은 과목 학생은 서버 권한상 읽을 수는 있음).
- `APP_VERSION`/`version.json` = `2026-10-13a`. 테스트: `t50.py`(t29는 과목 없는 활동에 알림 칸이 없는지 확인으로 바꿈).

### 2-16. 추가 수정 (PR #29, 2026-10-13)
- 새 활동 화면 배치: 맨 위 ‘활동 이름·활동 소개’(번호 없음) → ① 활동 → ② 무엇에 대해(🎯 핵심 질문·자료) → ③ 🪜 단계별 질문(해당 활동만) → ④ 생각을 어디까지 → ⑤ 누구와·언제까지. 번호는 보이는 칸만 차례로(`N()`).
- 🪜 단계별 질문(`STEPQ_T` = 토론·깊이 생각하기·논술·감상·성찰·예측):
  - 질문 틀(주장과 근거·생각과 이유·자유롭게·비교하기·원인과 결과·자료 읽기)을 고르면 그 틀의 학생용 질문이 채워진다(`defQ`, `QDEF`). ‘✏️ 직접 만들기’로 처음부터 적을 수도 있다.
  - 질문 고치기·도움말·＋추가(8개까지)·▲▼·✕를 지원한다.
  - 저장: `fields[]`에 `q`(학생에게 보일 질문). 틀 그대로면 예전과 같은 칸(주장·근거 등), 고친 질문은 `q`를 붙이고 직접 만든 칸은 `q1…`.
  - 학생 화면 `sField`가 `x.q`를 먼저 쓰고, 직접 만든 질문이면 번호를 붙인다.
  - 세부 설정의 ‘생각 — 어떻게 쓸까요?’ 칩은 이 칸으로 옮겼다(해당 없는 활동은 그대로).
- 👩‍🏫 교사 이름:
  - 처음 구글로 로그인하면(메타데이터 `display_name` 없음) 이름 정하기 창이 뜬다(‘나중에’ 가능).
  - 인사말 옆 ‘✏️ 이름 바꾸기’로 언제든 바꾼다. 끝의 ‘선생님’은 떼고 저장한다.
  - 저장하면 `teacher_set_name`(teachers.name·name_set) + `auth.updateUser({data:{display_name}})` + 내 과목·활동의 `teacherName`을 바꾼다.
  - `teacher_checkin`은 name_set이면 구글 이름으로 덮어쓰지 않는다. setup.sql·서버 마이그레이션 `teacher_set_name`. 로컬 검사 `dev/sql/tname_test.sql`.
- `APP_VERSION`/`version.json` = `2026-10-13c`. 테스트: `t51.py`.

### 2-17. 추가 수정 (PR #30, 2026-10-13)
- 질문 유형(깊이 생각하기)은 선택 사항: ‘고르지 않음’이 기본(`TEMPLATES.inquiry.qtype = ""`), 고르지 않으면 `qtype:""`.
- 필수 칸에 빨간 `*`(`.req`): ① 활동, 핵심 질문(필기 제외), 입장, 대화 상대, 단계별 질문.
- 단계별 질문 틀을 6개로: 생각과 근거(claimEvidence; 예전 ‘생각과 이유’·‘자유롭게’를 합침) · 비교하기 · 원인과 결과 · 자료 분석(source, 과목 공통 말로) · 문제 해결(problem: issue·pcause·solution·assess, 새로 추가) · ✏️ 직접 만들기. 예전 활동의 feel/free 칸은 그대로 동작.
- ⑤ 과목은 칩으로 여러 개 고르기(`f.courseIds`, `courseSel`):
  - 새 활동을 공개하면 과목마다 같은 활동을 하나씩 만든다(결과는 과목별). 과목마다 알림·예약.
  - 수정은 한 과목만 고른다. 임시 저장은 `draftCourses`에 고른 과목을 기억했다가 공개할 때 나눈다.
- ‘그룹별 공개’는 과목마다 접는 칸(`gschedHTML`, 기본 접힘, 요약: n/전체 그룹 공개·예약 수).
- 수업 타이머:
  - 10초·30초·1분·3분·5분·10분·15분·20분 버튼(`TMR_CHIPS` 초 단위, `data-s`).
  - 직접 입력은 분+초, +30초·+1분.
- `APP_VERSION`/`version.json` = `2026-10-13d`. 테스트: `t52.py`(t44·t46·t48·t50은 새 화면에 맞게 고침).

### 2-18. 추가 수정 (PR #31, 2026-10-13)
- 📽 수업에서 함께 보기:
  - 학생은 ‘익명 n’(먼저 쓴 순서 번호)으로 구분한다.
  - ‘학생 생각’(발표 목록 없을 때)은 최근 생각부터 3개씩 ← → 로 넘긴다(`pagerHTML`, `S.pidx`).
  - 단계별 질문이 2개 이상이면(`presentQs`) 두 가지 보기가 생긴다.
    - ‘질문별로 보기’: 질문 1·2·3 탭, 한 질문에 대한 답 6개씩.
    - ‘학생별로 보기’: 한 화면에 2명/3명, 학생마다 질문 차례대로.
- 📸 ‘오늘의 필기’ → ‘학습 나눔’(필기·마인드맵·스키마 등). 내부 이름 notes는 그대로.
  - 기본은 선생님만 보기(`reveal:"teacher"`). 예전에 깊이(applyDepth)가 학습 나눔의 reveal을 ‘after’로 바꾸던 문제를 막았다(서버에 그렇게 저장된 학습 나눔은 없음을 확인).
  - 만들 때 ‘올린 학생끼리 서로 보기’와 ‘이름 없이’를 고를 수 있다. 활동 화면 위의 ‘선생님만 / 학생끼리 서로 보기’로 언제든 바꾼다(`note-share`).
  - 학생은 자기 사진을 올린 뒤 ‘📚 친구들의 학습 나눔’을 본다(`noteGallery`).
  - 서버: 보기 규칙만 하나 더했다(`notes_read_shared` + `note_can_read_shared`, 마이그레이션 `notes_read_shared`). 지우기 규칙은 그대로라 친구 사진을 지울 수 없다. 로컬 검사 `dev/sql/nshare_test.sql`.
- 볼 수 있는 범위가 열리면(활동 reveal: teacher → 그 밖) 학생 기기가 글(posts)을 처음부터 다시 받는다(`S.db.reload`, `REVEAL_SEEN`). 학습 나눔 말고도 ‘선생님만 보기’ 활동을 연 경우에 해당한다.
- `APP_VERSION`/`version.json` = `2026-10-13f`. 테스트: `t53.py`.

### 2-19. 추가 수정 (PR #32, 2026-10-13)
- 함께 보기: ‘학생별로 보기’ 한 화면 1·2·3명(`S.pper`). 위쪽 ‘👤 이름 보기 / 🙈 익명으로 보기’(`S.pnames`, 기본 익명)로 모든 보기에서 이름을 켜고 끈다.
- 활동 개요:
  - ‘💡 지금 수업에서 볼 것’ 초록 상자(`hintCard`)를 없앴다. 참여 숫자가 위 카드와 겹쳤기 때문이다. 다음 진행 제안 한 줄만 ‘참여와 완료’ 카드에 ‘👉 다음 진행 제안’으로 남긴다(`lessonHints`의 마지막 문장).
  - 논제·자료 아래에 ‘🪜 단계별 질문’ 상자(`.sqbox`, 도움말 포함)를 보여 준다. 깊이 생각하기·직접 만든 질문이면 머리말이 ‘🎯 핵심 질문’이다.
- 첫 화면 AI 가상 인물 대화 소개의 인물 예시를 ‘윤동주, 정조, 찰스 다윈, 존 롤스, 그레타 툰베리 등’으로.
- `APP_VERSION`/`version.json` = `2026-10-13g`. 테스트: `t54.py`.

---

### 2-20. 재제출 알림 · 학생 개별 안내 (PR #33, 2026-10-16)
- **재제출 요청 알림**: 학습 나눔에서 ‘↻ 재제출 요청’을 보내면 그 글을 쓴 학생 기기에만 알림. `notify`에 `{post}` → 서버 `push_targets_post(p_post)`가 글 주인(docs.owner)을 찾아 `push_targets_students`로.
- **📨 개별 안내**: 교사 화면 인사말 옆 ‘📨 개별 안내’(체험에서도), 과목 포트폴리오 학생 창의 ‘📨 이 학생에게 안내’.
  - 새 안내: 과목으로 좁히기·검색·학급 한 번에 고르기 → 제목(선택)·내용(필수, 1000자) → 🔔 휴대폰 알림도(기본 켬)
  - 보낸 안내: 읽음 n/전체, 학생마다 ✓ 읽은 시각/○ 아직, ‘🔔 안 읽은 학생에게 다시 알림’, ‘↩ 거두기’(학생 화면에서 사라짐)
  - 학생: 앱을 열 때(그리고 1분 넘게 다른 앱에 있다가 돌아올 때) 안 읽은 안내가 있으면 화면 가운데 큰 창(`inbox-pop`)으로 뜬다. 바깥 누르기·Esc로는 닫히지 않고 ‘확인했어요’를 눌러야 읽음(`msg_read`). 여러 개면 오래된 것부터 차례로. 홈에 ‘📨 선생님 안내 n개’ 줄 → 지난 안내 목록.
  - 체험: 이 기기에서만(`S.demoMsgs`/`S.demoInbox`). 보낸 안내는 ‘학생 화면 미리보기’에서 큰 창으로 보인다.
- 서버(적용 완료): 표 `student_msgs`(직접 읽기·쓰기 권한 없음, RLS 켬). 함수 `msg_send`(교사, 내 명단 학생만, 300명·1시간 30번), `msg_sent`, `msg_withdraw`(지우지 않고 `withdrawn_at` 표시 — 지우는 마이그레이션은 취소되므로), `my_msgs`(최근 90일 50개, 막힌 교사 제외), `msg_read`(내 것만), `push_targets_students`, `push_targets_post`. notify v5.
- 테스트: dev/tests/t55.py(실제 흐름), t56.py(체험·휴대폰), dev/sql/msg_test.sql(권한).

### 2-21. 수행평가 점수 안내 (PR #34, 2026-10-17)
- ‘📨 개별 안내’ → 새 안내에서 **💬 일반 안내 / 📊 수행평가 점수 안내** 고르기.
  - 점수 안내: 받는 학생 고르기 → 점수 표(평가 이름 고치기·추가·빼기, 8개까지) → 제목 → 안내 멘트(`{학생명}`·`{점수}` 자리에 학생마다 채움, 기본 멘트는 선생님 요청 문구, 고친 멘트는 이 기기에 기억) → 미리보기 → 예/아니오 질문 2개(문구 고칠 수 있음).
  - 📋 엑셀에서 붙여 넣기: ‘학번 이름 점수…’ 줄(첫 줄이 ‘학번 이름 평가명…’이면 평가 이름도). 붙여 넣은 학생은 자동 선택, 명단에 없는 학생은 알려 준다.
  - 점수가 빈 학생이 있으면 보내지 않는다. 휴대폰 알림에는 점수를 넣지 않는다(잠금 화면 노출 방지).
- 학생: 큰 창에 자기 점수 안내 + 질문마다 예/아니오 → ‘답 보내기’(모두 골라야 눌림). 답하기 전까지는 앱을 열 때마다 다시 뜬다(‘확인 대기’). 답은 한 번만(서버가 막음). 지난 안내 목록에서 고른 답이 보인다.
- 교사 ‘보낸 안내’: ‘응답 n/전체 · 이의 n’, 학생별 예/아니오·응답일시 표(이의 제기한 줄 강조, 학생별 보낸 내용), **⬇ 응답 엑셀로 받기** → CSV(BOM, 엑셀에서 열림): 학교명/학번/이름/질문1/질문2/응답일시(답하지 않은 학생은 ‘미응답’), ‘답하지 않은 n명에게 다시 알림’.
- 파일 저장 `saveFile()`: claude 다운로드 → 브라우저 내려받기(a[download]) → 안 되면 복사 창. 기존 활동 ‘결과 내보내기(CSV)’도 이제 GitHub 버전에서 파일로 바로 받아진다.
- 서버(적용 완료): `student_msgs`에 kind·ask·answers·answered_at 열 추가. `msg_send_each(p_title, p_items[{sid, body}], p_ask)`(교사, 내 명단 학생만), `msg_answer(p_id, p_answers[boolean])`(본인·한 번·질문 수와 같아야), `msg_sent`·`my_msgs`가 종류·질문·응답을 함께 돌려준다.
- 테스트: t57(실제 흐름·엑셀 파일 내용), t58(체험·휴대폰), dev/sql/msg_test.sql 뒷부분.

### 2-22. 아이콘을 Tabler Icons로 통일 (PR #35, 2026-10-17)
- UI의 이모지 아이콘을 모두 **Tabler Icons(outline, v3.49.0, MIT)** 한 세트로 바꿨다. 화면 글·디자인·동작은 그대로.
- 방식: 외부 파일을 불러오지 않고 **쓰는 아이콘만 index.html 안에 SVG로** 넣는다(약 140개, 25KB) → 로딩 실패·깜빡임 없음.
  - `ic(이름, 크기, 이름표)` → `<svg class="ti">`. 크기 `"sm"` 16px(작은 보조·칩·작은 버튼) · `"md"` 20px(기본) · `"lg"` 24px(기능 카드 대표). 선 굵기 1.8, 색은 글자색(currentColor).
  - 이름표가 없으면 `aria-hidden`(버튼 글자가 뜻을 전한다). 아이콘만 있는 버튼은 버튼에 `aria-label`을 둔다(기존대로).
  - CSS에서 그리는 표시(체크 상자 ✓, 진행 표시, 흐름 화살표)는 `var(--ti-이름)` 마스크로 같은 Tabler 아이콘을 쓴다.
  - **아이콘을 새로 쓰면** `python3 dev/icons/build_icons.py [tabler-icons 저장소 경로]`를 한 번 돌린다. ic("이름")·`icon:/ic:/i:/ti:/mark:` 값·`data-ti`·`/*TI:LIST*/` 목록·`var(--ti-…)`에서 이름을 모아 `/*TI:BEGIN*/…/*TI:END*/`, `/*TIC:BEGIN*/…/*TIC:END*/`를 채운다. 저장소에 없는 이름이면 멈춘다. (저장소: `git clone --depth 1 https://github.com/tabler/tabler-icons`)
  - 없는 이름을 ic()에 넘기면 콘솔에 `[icon] 없는 아이콘` 경고 → 테스트(mock.js)는 이것을 오류로 잡는다.
- 자료 구조: TEMPLATES `icon/modeIcon`, GOALS `icon`, STEP `ic`, QTYPES `mark`, homeState `i`, cardLabel `{i,t}`, ASG·학생 상태·생각 변화 `ic`, RELAY_REACT `ic`, 투어 `ti` 는 이제 **아이콘 이름**이다. 과목 아이콘은 `courseIcon(c, 크기)`(HTML) / `courseIcName(c)`.
- 남겨 둔 것: 학생·교사가 쓴 내용과 체험용 예시 글 속 이모지, 문장 안의 흐름 화살표(“처음 생각 → 친구 생각”), 알림(toast) 글은 이모지만 뺐다.
- 테스트: dev/tests/t59.py — PC·390px에서 교사·학생·창 화면 120여 곳을 돌며 남은 이모지, 아이콘 크기(16/20/24)·선 굵기(1.8), 넘침, 없는 아이콘을 확인.

### 2-23. 가상 인물 대화 AI 개선 (PR #36, 2026-10-18)
- 진단: 기존 모델 `@cf/qwen/qwen3-30b-a3b-fp8`(실제 3B만 움직임)은 답이 막연하고 어색했다. 같은 질문으로 Cloudflare 모델 8개를 비교해 보니, **자료 없이 “구체적으로” 말하게 하면 큰 모델도 단체·문서를 지어낸다**(gpt-oss-120b가 ‘민주통일준비위원회 회의록’ 등 창작). 중국어·일본어 섞임(qwen·llama), 반복(mistral)도 있었다.
- 해결 = **모델 교체 + 근거 자료 + 지시문 개선**
  - 모델: 기본 `@cf/openai/gpt-oss-120b`(reasoning low, OpenAI 호환 `/ai/v1/chat/completions`). 실패·무료량 소진 시 `@cf/qwen/qwen3-30b-a3b-fp8`로 한 번 더(`CF_MODEL`·`CF_FALLBACK` Secrets로 바꿀 수 있음).
  - 근거: 활동 만들기에 **‘AI용 인물 자료’**(persona.facts, 4000자) 칸. 학생 화면에는 안 보인다. `chat_begin`이 함께 돌려준다. **Gemini로 초안 만들기**(suggest `op:"persona"`, 선생님 키, 인물 이름·장면·소개만 보냄) → 선생님이 확인·수정.
  - 지시문: 장면 시점의 인물로 말하기(뒤의 일은 모름), 자료에 없는 이름·날짜·단체·문서 만들지 않기, 앞말 반복 금지, 300자 안팎, 한국어만. 되묻기는 서버가 **세 번째 질문마다만** 지시.
- 비용(Workers AI 가격표 2026-10): gpt-oss-120b 한 번 오가기 ≈ 58뉴런 → 하루 무료 10,000뉴런으로 약 170번. 넘으면 자동으로 qwen(≈22뉴런)으로 넘어간다. (Workers 유료 플랜이면 넘는 만큼 1,000뉴런당 $0.011)
- 검증: 임시 함수 `chat-eval`(cron 키로만 실행)로 실제 모델 응답을 비교했고, 끝난 뒤 410만 돌려주는 빈 함수로 닫았다(지울 도구가 없어 남아 있음 — 대시보드에서 지워도 됨).
- 테스트: dev/tests/t60.py(인물 자료 칸·Gemini 초안·저장·체험).

### 2-24. 인물 대화 생동감 · Beta 표시 · 첫 화면 예시 복구 (PR #37, 2026-10-18)
- 첫 화면 ‘생각이음만의 활동’ 예시: 대화 예시 칸이 높이 128px 고정 + `overflow:hidden`이라 좁은 화면·큰 글씨에서 말풍선이 잘렸다 → `.chatart`는 높이 자동(최소 128px)·줄바꿈 허용. 생각 지도 그림은 선이 글자를 지나지 않게 다시 그림(viewBox 240×120).
- ‘새 활동’의 가상 인물 대화 카드에 작은 **Beta** 표시(GOALS의 `beta:true` → `<span class="beta">`).
- 인물 대화 지시문(chat `rules()`)을 ‘인물 본인으로 살아 있게’로 다시 씀: “기록에 따르면” 같은 남의 말투 금지, 성격·감정·말버릇을 드러내기, 무례하면 기질대로 언짢아하거나 발끈하기(욕설·조롱 없이), 오해에 맞설 때도 자료의 사실은 부인하지 않기, temperature 0.8.
- 정체 밝히기: 학생이 **진지하게 물을 때만** 한 문장으로 “AI가 연기하는 가상의 ○○”라고 밝힌다. 모델이 ‘AI’라는 낱말만 보고 습관처럼 정체를 밝히는 문제 → 서버가 학생의 마지막 말을 가볍게 분류(`turnHint`: MOCK 놀림 / WHO 진지한 정체 질문 / OFF 수업과 무관·규칙 무시 요구 / RUDE 무례)해서 **그 차례에만** 지시를 덧붙인다. 놀림 차례에는 모델이 “나는 기계가 아니라 사람이오”처럼 사실이 아닌 말을 덧붙이곤 해서 그런 문장만 빼고 보낸다(`scrubMock`).
- suggest `op:"persona"`: 인물 자료 초안에 **[성격과 기질]** 묶음 추가(6묶음, 1,800자 안팎), [말투]·[관계]를 더 구체적으로. 기존 활동은 ‘Gemini로 초안 만들기’를 다시 누르면 성격 자료가 들어간다.
- 검증: 임시 `chat-eval`(cron 키로만 실행, 끝난 뒤 410 빈 함수로 되돌림)로 여운형(자료 있음)·찰스 다윈(자료 없음) 대화를 실제 gpt-oss-120b로 돌려 확인 — 친일 오해에 “허, 젊은이가 말이 지나치군!”, 놀림에 정체를 밝히지 않음, 진지한 질문에만 밝힘, 노래 가사 요구는 인물 말투로 거절. 분류 정규식은 오탐 사례(“왜 그 규칙을 무시하셨어요?”, “인공지능이 발달하면…”, “왜 친일파를 처벌하지 않았나요?”)까지 node로 확인.
- 한계: 분류는 낱말 규칙이라 새로운 표현의 놀림은 못 잡을 수 있다(그때는 기본 지시문만 적용). 모델 특성상 답이 가끔 350자를 넘는다.

## 3. 파일 및 코드 구조

### 3-1. 저장소 파일
| 파일 | 역할 |
|---|---|
| `index.html` | 앱 전체(HTML+CSS+JS, 약 5,960줄) |
| `sw.js` | 서비스 워커: push 수신 → 알림 표시, 알림 클릭 → 해당 주소(`#활동id` / `#c:과목id`)로 이동. 캐시는 하지 않음 |
| `manifest.webmanifest`, `icons/*` | PWA 설치 |
| `privacy.html`, `terms.html` | 개인정보처리방침·이용약관(구글 OAuth 브랜딩용으로도 사용) |
| `README.md` | 설치·운영 안내(Supabase 설정, Cloudflare, VAPID, Gemini 등) |
| `supabase/setup.sql` | DB 전체 설정. **두 번 실행해도 되게** 작성(로컬 Postgres로 확인). 새 설치 시 이 파일 하나로 구성 |
| `supabase/functions/chat/index.ts` | 가상 인물 대화 중계(Cloudflare). `chat_begin` RPC로 권한·횟수 확인, 서버가 시스템 프롬프트 생성, `<think>` 제거 |
| `supabase/functions/notify/index.ts` | Web Push 발송(v2). `push_targets` / `push_targets_for` → 암호화 → 발송. 404/410이면 `push_drop` |
| `supabase/functions/suggest/index.ts` | Gemini 질문 추천(v1). `ai_key_status`로 교사 확인 → service role로 `teacher_ai` 키 조회 → 모델 순서대로 시도 |
| `.github/workflows/keepalive.yml` | 사흘마다 Supabase에 접속해 무료 프로젝트 정지 방지(저장소 Secrets `SUPABASE_URL`, `SUPABASE_ANON_KEY` 필요) |
| `dev/tests/*` | Playwright 테스트 + 가짜 Supabase(`mock.js`) + 페이지 빌더(`build_pages.py`) |
| `dev/sql/*` | 로컬 Postgres 테스트용 auth/storage 스텁과 수강 RLS 시나리오 |
| `docs/HANDOVER.md` | 이 문서 |

### 3-2. index.html 내부 구조
주석 섹션 번호를 기준으로 했다. 행 번호는 대략이다.

| 섹션 / 위치 | 내용 |
|---|---|
| 0. (≈953) | `SUPABASE_URL`, `SUPABASE_ANON_KEY`(공개 키). **service_role 키는 절대 넣지 않음** |
| 1. 상수 (≈960) | `TOOLS`, `DEPTHS`, `TEMPLATES`, `QTYPES`, `GOALS`, `SAMPLE_ROOMS`, `IS_DEMO`, `demoData()` |
| 2. 상태와 유틸 (≈1303) | 전역 상태 `S`, `TEACHER_ACTS`(학생이 부르면 막는 교사 전용 액션 목록), 과목·그룹 헬퍼(`courseOf`, `groupsOf`, `myGroup`, `classOf`, `autoGroup`, `forMe`) |
| 3. 방 설정 해석 (≈1487) | `phasesOf`, `stepsOf`, `featuresOf` 등 |
| 4. 입력 상태 (≈1624) | `F(key)` = `S.form[key]`, `data-form`/`data-k`로 자동 저장(기기 임시 저장) |
| 5. 저장소 (≈1679) | `write(dbFn, localFn)`, `sub()`(실시간 구독), `dataChanged()`, `applyHash()`(`#활동id`, `#c:과목id`, `#teacher`) |
| 6. 렌더 공통 (≈1823) | `render()` → `renderTop()` + 화면 + `renderModal()` + `afterRender()` |
| 7. 홈 (≈1901) | 학생: `viewHomeStudent` → `viewDashList` / `viewDash`, 푸시 바(`pushBarHTML`), 새 글 표시(SEEN) |
| 8~9. 방(학생) | `viewRoomStudent`, `roomBoard`, `wallHTML`, `wallCard`, `readCard`, `wallActs`(❤️·💬), `commentForm` |
| 📸 (≈2170) | 오늘의 필기 학생·교사 화면, Storage 업로드·서명 URL |
| (≈2350) | 🧭 체험 둘러보기 `TOUR`, `tourGo` / `tourPlace` / `tourEnd` |
| (≈2393) | 🔔 Web Push 클라이언트 `VAPID_PUBLIC`, `pushOn`, `pushSync`, `notifyStudents`, `notifyNewRoom`, hashchange 리스너 |
| 10. 방(교사) (≈3246~) | `viewRoomTeacher`, 그룹 배포, 학생 생각 살펴보기 |
| (≈3552~) | Supabase 연결 `SB`, `initSupa`, `supaDB` 어댑터(collection/doc/onSnapshot 흉내), 교사 로그인·소개 화면 `viewWelcome` + `welcomeSpotlight`, 교사 관리 `tadminHTML` / `fbAdminHTML`, 학생 코드 `rosterModalHTML` / `parseRoster` |
| (≈4068~) | 교사 대시보드 `teacherTop`(요약 타일), `courseCards`, 수강 학생 `memOpen` / `membersHTML` / `memRefresh` / `memLine`, `courseHead`, `noticePanel` / `noticesOf` |
| 10-1. (≈4434) | 활동 관리 `manageCard`, `manageFiltered`(`MSORTS`에 `due` 추가됨), `viewManage` |
| (≈4525) | `renderModal()`: 모달 종류 qr / text / del / course / members / ai / feedback / tadmin / install / racts 등 |
| (≈4909) | 🪄 AI 추천 `AI_SUG_T`, `aiSugHTML`, `DEMO_SUG`, `aiSuggest`, `aiSetupHTML`(AI Studio 5단계 안내) |
| 12. 새 활동 만들기 (≈4971) | `viewCreate`, `roomFromForm`, `roomMeta` |
| 13. 이벤트 (≈5099~) | 클릭은 `data-a` 위임 → `act(a, b)`. input/change/keydown 리스너 |

**핵심 패턴**
- 모든 화면은 `render()`로 통째로 다시 그린다.
- 버튼은 `data-a="액션"` + `data-id` / `data-v`. `act()`의 `switch`에 `case`를 추가하는 방식이다.
- 교사 전용 액션은 `TEACHER_ACTS`에도 넣어야 학생이 호출할 때 막힌다.
- 입력 중에는 `dataChanged()`가 다시 그리지 않는다. 그래서 입력 칸 포커스가 유지된다.

### 3-3. GitHub 연동
- **저장소**: `ieumind/ieumind.github.io` (예전 `taeneuu/thinklink`에서 옮김). 기본 브랜치 `main` → GitHub Pages.
- **작업 브랜치**: `supabase-version`.
  - 작업 → 커밋 → push → PR(`supabase-version` → `main`) → **사용자가 Merge**.
- **커밋 작성자**: `git -c user.name="taeneuu" -c user.email="taeneuu@users.noreply.github.com" commit …`
- **커밋 메시지 끝**:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: <세션 링크>
  ```
- **PR 열기**: `gh pr create`는 GraphQL 오류가 난다. 대신 아래처럼 연다.
  ```
  gh api repos/ieumind/ieumind.github.io/pulls -f title=… -f head=supabase-version -f base=main -F body=@파일
  ```
  - PR 본문 끝: `🤖 Generated with [Claude Code](https://claude.com/claude-code)` + 세션 링크.

### 3-4. Supabase (실서버 상태)
- **표 (public)**

  | 표 | 내용 |
  |---|---|
  | `docs` | 모든 앱 데이터. PK (`col`, `id`, `tid`). `data` jsonb, `owner`, `room_id` |
  | `teachers` | `email`, `admin`, `blocked` 등 |
  | `students` | `id`, `tid`, `school`, `number`, `name`, `code` |
  | `student_sessions` | `uid`, `tid`, `student_id` |
  | `chat_usage` | AI 대화 횟수 |
  | `push_subs` | 푸시 구독 |
  | `notify_log` | 시간당 30회 제한용 |
  | `feedback` | 오류·건의 |
  | `app_secrets` | VAPID 키. anon/authenticated 권한 없음 |
  | `teacher_ai` | 교사별 Gemini 키. anon/authenticated 권한 없음 |

  `docs.col` 종류: `rooms`, `posts`, `replies`, `treplies`(교사 피드백), `courses`, `config`, `tnotes`, `ttemplates`.
- **주요 함수**

  | 분류 | 함수 |
  |---|---|
  | 신원·권한 | `whoami`, `claim_student`, `teacher_checkin`, `is_teacher`, `is_admin`, `tid_active`, `is_my_teacher`, `my_student`, `my_student_name`, `my_student_id` |
  | 볼 수 있는지 판단 | `room_open_to_peers`, `course_for_me`, `room_for_me` |
  | 데이터 처리 | `doc_merge`, `docs_stamp`(트리거), `note_can_read`, `note_can_write`, `chat_begin` |
  | 푸시 | `push_save`, `push_forget`, `push_targets`, `push_targets_for`, `push_drop` |
  | 오류·건의 | `feedback_send` |
  | 관리자 | `admin_list_teachers`, `admin_set_blocked`, `admin_list_feedback`, `admin_feedback_done` |
  | AI 키 | `ai_key_set`, `ai_key_status` |

  `zz_old_*`(예전 overload를 이름만 바꿔 둔 것, 아래 6장 참조).
- **Edge Functions** (모두 `verify_jwt: true`)

  | 함수 | 버전 | 필요한 것 |
  |---|---|---|
  | `chat` | v2 | Secrets `CF_ACCOUNT_ID`, `CF_API_TOKEN`(선택 `CF_MODEL`) |
  | `notify` | v2 | `app_secrets`의 `vapid_public` / `vapid_private` |
  | `suggest` | v1 | 교사가 앱에서 넣은 Gemini 키(`teacher_ai`) |
- **Storage**: 비공개 버킷 `notes`. 경로는 `{활동id}/{학생id}/{시각}-{쪽}.jpg`. 서명 URL 유효시간 6시간.
- **Auth**: Google provider(교사), Anonymous sign-in(학생).

### 3-5. 외부 서비스·키 위치
| 대상 | 위치 |
|---|---|
| Supabase anon 키 | `index.html`(공개해도 됨) |
| service_role 키 | Edge Function 환경에만. **코드·저장소에 절대 없음** |
| VAPID 공개 키 | `index.html`의 `VAPID_PUBLIC` |
| VAPID 비밀 키 | `app_secrets` 표에만. **문서·코드·대화에 다시 적지 말 것** |
| Cloudflare 키 | Supabase Edge Function Secrets(사용자가 직접 입력) |
| Gemini 키 | 교사마다 앱 ⚙️ AI 연결 설정 → `teacher_ai` 표 |
| Google OAuth 클라이언트 | Google Cloud 콘솔(사용자 관리). 브랜딩에 privacy.html / terms.html 주소 사용 |

---

## 4. 미완료 작업 / 앞으로 할 일

**최근 변경 (2026-10-20d): 배너 그림 교체 · 날짜 줄 · 캐릭터 설정 카드 hover 오류**
- 홈 배너 SVG를 `img/banner.webp`(2048×768, 37KB) 이미지로 교체. 글(THINKING WORKSPACE·생각을 연결하는 수업)은 왼쪽에 그대로, 그림은 오른쪽(`.wb-art`, 왼쪽 가장자리는 마스크로 흐리게). 휴대폰(≤700px)에서는 글 아래에 그림. 그림이 밝아서 배너 색은 라이트·다크 모두 고정(밝은 바탕+진한 글).
- 인사말 위에 작은 글씨 ‘오늘은 N월 N일 X요일’.
- **버그 원인**: ‘캐릭터 설정’ 카드가 `class="card ccard"` 였는데, `.ccard`는 예전 버튼형 카드용 규칙(`all:unset; cursor:pointer; :hover{border-color:var(--fg)}`)이라 마우스·터치 때 테두리가 바뀌고(다크에서는 흰색) 포인터 커서가 됐다. 클래스를 `cset-card`로 바꾸고 쓰이지 않던 `.ccard` 규칙을 지웠다.
- 상단 막대·서식 글상자 단추가 `var(--ink)`(테마와 무관한 진한 청록)를 써서 다크 모드에서 안 보이던 것을 `var(--fg)`로 고쳤다.

**최근 변경 (2026-10-20c): 서식 글상자 · 임시저장 표시 · 교사 첫 화면 정리**
- `index.html`만 바뀜(DB 변경 없음). `ta(key,k,{rich:true})` 가 서식 글상자(`.rte`, `contenteditable`)를 그린다. `question()`(학생 답 칸 전부), 고쳐 쓰기·근거 칸, 교사 ‘자료’(`#c-context`)에 쓴다. 한 줄 메모·피드백·채팅·교사용 메모 등은 그대로 일반 칸.
- 저장 모양: 서식이 없으면 예전과 같은 일반 글. 서식이 있으면 `\u2063 … \u2064` 로 감싼 글 안에 `<b><i><u><s>` 만(그 밖의 `< > &` 는 `&lt; &gt; &amp;`). 목록은 `- ` / `1. ` 줄로 저장.
- 보여 줄 때: `MutationObserver` 가 화면에 들어온 글 조각(텍스트 노드)에서 `\u2063…\u2064` 를 찾아 `rtFrag()` 로 요소를 직접 만들어 바꾼다(HTML 문자열을 쓰지 않아 XSS 불가, https 링크는 자동 링크). 그래서 화면 코드는 그대로 `esc()` 만 쓰면 된다. **서식 글을 일반 글로 써야 하는 곳(글자 수·AI·CSV·비교)은 `rtPlain()` 을 쓴다** — 지금은 `cnt`, 채팅 자료(`chatRules`), CSV 저장에 적용. `lnk()` 는 서식 글이면 링크 변환을 건너뛴다.
- 임시저장: 쓰는 대로 0.5초 뒤 이 기기에 자동 저장(`saveFormsSoon`, 예전부터 있던 것)을 글상자 아래에 ‘자동 저장됨 · 시각’으로 보여 주고, ‘임시저장’ 버튼(`rte-save`)은 바로 저장한다. 창을 닫거나 숨길 때도 저장(`flushForms`). 다른 기기와는 이어지지 않는다(서버에 임시 글을 만들지 않음).
- 교사 첫 화면: 날짜·‘교사 화면’ 줄, 인사말 아래 ‘이름 바꾸기’, ‘지금 N개 활동이 열려 있어요’ 줄을 없앴다(이름 바꾸기는 상단 계정 메뉴). 상단 막대와 인사말 간격을 좁혔다.
- 아이콘 `list-numbers` 를 `TI_PATHS` 에 직접 넣었다(네트워크가 막혀 `build_icons.py` 를 못 돌렸음). 다음에 `build_icons.py` 를 돌리면 같은 내용으로 다시 만들어진다. 테스트: `dev/tests/t66.py`.

**최근 변경 (2026-10-20b): 상단 막대(알림 벨·계정 메뉴·탈퇴) + 홈 배너 그래픽**
- 교사 화면 위쪽 `#topbar`(`renderTopbar`): 알림 벨(활동별 ‘새 글’ 수, 기준 시각은 이 기기 `nonjae.bell.<uid>`, ‘모두 읽음’으로 갱신) · 계정 동그라미(구글 사진/첫 글자) 메뉴 = 이름 바꾸기(`tname-open`) · 로그아웃 · 탈퇴하기.
- 탈퇴: 확인 칸에 ‘탈퇴’ 입력 → `teacher_delete_me(p_dry:=true)`로 가능 여부(관리자는 불가) 확인 → Storage의 `notes/<roomId>/…`·`materials/<uid>/…`를 API로 삭제(`purgeMyFiles`) → `teacher_delete_me()`가 내 docs·학생·안내·구독·AI 키·teachers 행·auth.users를 삭제 → 로그아웃.
- **DB 변경**: `supabase/setup.sql` 맨 아래에 `teacher_delete_me` 추가(멱등, `create or replace`). Supabase SQL Editor에서 setup.sql(또는 그 블록)을 한 번 실행해야 탈퇴가 동작한다. 아직 없으면 앱이 ‘탈퇴 기능이 아직 서버에 설치되지 않았어요’라고 알린다.
- 홈 배너(`.wb-art`)를 지구본·책·지도 선 SVG로 교체. 테스트: `dev/tests/t65.py`(mock.js에 `teacher_delete_me`·Storage `list` 추가).

**최근 변경 (2026-10-19a): 교사 도구 — 학생 코드 과목·그룹 보기 · 학습 나눔 보강 · 미제출 알림**
- `index.html`만 바뀜(DB·서버 함수 변경 없음 — 새 필드는 기존 활동 문서 안의 `noteCfg.memoQ`뿐이고, 알림은 기존 `msg_send`·`notify`를 쓴다).
- 👥 학생 코드: 학생 명단 창에 ‘전체 학생 / 과목별 / 그룹별’ 선택칸(`#roster-view`, `S.rosterView`). 수강 학생을 정하지 않은 과목은 모든 학생이 보인다. ‘코드 쪽지 인쇄’는 지금 고른 과목·그룹 학생만 인쇄한다(`rosterPrintList`).
- 학습 나눔 교사 화면:
  - 조회 기록(`viewersOf`)을 가져와 ‘조회’ 숫자, ‘조회만 함’ 칩·필터, 카드의 조회 횟수·마지막 조회를 보인다. 명단이 없으면 조회한 학생 이름도 목록에 넣는다.
  - 한 줄 메모 질문: 만들기·수정 화면의 ‘한 줄 메모 질문’(`memoQ`, 120자). 학생 화면의 메모 칸 제목이 이 질문으로 바뀌고, 비우면 예전처럼 ‘한 줄 메모’. 답은 계속 선택이다. 교사 화면 위쪽에 질문이 보인다.
  - ‘다음 시간용으로 복제’·‘학생 명단’ 버튼과 `note-dup` 액션을 지웠다(위쪽 ‘복제’, 홈의 ‘학생 코드’와 겹침).
- 🔔 미제출 알림(모든 활동 유형): 학습 나눔 카드와 일반 활동 ‘참여 현황’ 표에 체크칸 + 알림 막대(`nudgeBar`). ‘미제출 N명 모두 고르기’(제출하지 않은 학생) 또는 한 명씩 고른 뒤 ‘알림 보내기’ → 개별 안내 창이 고른 학생·제목·내용(마감·링크 포함)을 채운 채로 열린다. 보내면 기존 개별 안내(읽음 확인·다시 알림 포함)와 같고, 휴대폰 알림을 누르면 그 활동으로 들어간다(`msgOpen(null,{url})` → `notify`의 `url`). 일반 활동의 ‘체크칸’은 모든 단계를 마치지 않은 학생에게 나오고, ‘미제출’은 글을 아직 제출하지 않은 학생이다. 학생 명단(학생 코드)에 없는 학생에게는 보낼 수 없고 안내한다. 실서비스·체험에서만 보인다.
- 테스트: `dev/tests/t64.py`(보기 선택칸·조회·질문·삭제·알림 전체/개별/일반 활동). `t20.py`는 `note-dup` 대신 위쪽 ‘복제’를 쓰도록 고쳤지만, 이 테스트는 이번 변경 전부터 학생 로그인 칸을 못 찾아 실패해 왔다(별개 문제).
- 알려진 예전 문제(이번 변경과 무관): 과목 학생 고르기에서 한 학급을 ‘일부만’ 고르면 존재하지 않는 아이콘 `circle-half-2`를 불러 `ICON missing`이 난다(`memChipsHTML`).

**최근 변경 (2026-10-18g): 가상 인물 대화 · AI 프롬프트 유형 6→4, 최대 대화 횟수 3·5·8·10 선택**
- `index.html`만 바뀜(DB·서버 함수 변경 없음 — `suggest`는 유형 이름만 받아서 재배포 불필요).
- 유형 통폐합: 설득+협상 → `persuade`(인물 설득·협상형), 개념 탐구+과학 자문 → `inquiry`(개념 탐구·문제 해결형). `ethics`·`expand`는 그대로. `pgSpec`의 협상·과학 항목은 지우고 설득·탐구 항목에 합쳤다(설득 단계 0~3, 문제 해결이면 관찰→가설→근거→결론).
- 예전에 저장한 활동 호환: `PG_TYPE_ALIAS`(negotiate→persuade, science→inquiry)와 `pgTypeOf()`로 열 때 합친 유형으로 보여 준다. DB는 건드리지 않는다.
- 최대 대화 횟수: 숫자 칸 → 선택 칸(3·5·8·10회), 기본 5회(`turnsOf`, `turnOpts`). 예전에 다른 값(예: 6·12회)으로 저장한 활동은 ‘N회 (이전 설정)’ 항목을 더해 저장해도 값이 바뀌지 않는다. 서버(`chat`)는 저장된 횟수를 그대로 쓴다.
- 테스트: `dev/tests/t63.py`에 유형 4개, 횟수 선택지·기본값, 예전 유형·횟수 호환, 4유형 모두 10개 항목 기본 틀을 추가. Gemini로 다듬는 실제 품질은 확인하지 못했다(테스트는 Gemini 흉내).

**최근 변경 (2026-10-18f): 가상 인물 대화 · 하루 무료량(Cloudflare 10,000뉴런) 아끼기**
- 문제: 18e의 시스템 지시문(캐릭터 카드·선생님 프롬프트·최근 16개 대화)이 길어 대화 한 번에 gpt-oss 기준 150~250뉴런이 들었다(하루 40~70번). 18일 낮에 실제로 ‘daily free allocation of 10,000 neurons’ 오류가 났다.
- 서버 `chat` (코드 변경은 이 함수 하나, DB·화면 변경 없음):
  - 모델 분담: 평소 `CF_LITE`(기본 `@cf/qwen/qwen3-30b-a3b-fp8`, 끝에 ` /no_think`), 마지막 차례·학생이 ‘끝낼게요’(`END_ASK`)라고 한 차례·고쳐 쓰기는 `CF_MODEL`(기본 gpt-oss-120b). 한쪽이 비거나 실패하면 다른 쪽으로 한 번 더. 가벼운 모델 답이 `clean()`(한글 있음, 가나·한자 3자 이상 없음)에 안 맞으면 큰 모델로 다시 만든다 — 예전 점검(아래 ‘모델’ 항목)에서 qwen은 막연하고 어색하며 중국어·일본어가 섞이기도 했기 때문.
  - 입력 줄이기: 최근 대화 16→8개(`KEEP`), 앞선 대화 요약은 1,800자(최근 쪽 우선), 선생님 프롬프트는 `slimGuide()`로 공백 정리 + 열 가지 제목이 있으면 평소 차례에서 [1. 활동 개요]·[9. 최종 피드백…] 제외(마지막 차례·마무리 요청에서는 전부), 규칙 문단 압축. 같은 활동에서 시스템 지시문 약 15% 감소(프롬프트가 길수록 더 줄어듦).
  - 학생이 ‘끝낼게요’ 등으로 먼저 마치자고 하면(`wrap`) 남은 횟수와 관계없이 그 차례에 최종 피드백까지 실행한다.
  - `ask()`가 사용 토큰을 서버 로그에 `chat <모델> in=… out=…`로 남긴다(글 내용 없음).
- 모델 분담·입력 줄이기는 **실제 모델로 확인하지 못했다**: 18일 낮에 무료량이 이미 바닥나 있었다(위 `raw` 오류). 다음 날 오전 9시(한국) 이후 임시 `chat-eval`(cron 키)로 qwen/gpt-oss 비교를 돌려 호칭 뒤바뀜·말투·토큰 수를 확인할 것. 이상하면 Secrets `CF_LITE`를 gpt-oss 주소로 두면 예전처럼 모두 큰 모델이다.
- 테스트: 단위(Node 스텁) 16개 통과 — 모델 선택, 마무리 요청, 고쳐 쓰기, 실패·이상한 답 전환, 제목 제외, 기억 길이.

**최근 변경 (2026-10-18e): 가상 인물 대화 · 캐릭터 채팅 구조로 다시 짬 + ‘전하’ 오류 수정**
- 오류: 고종 활동에서 AI가 학생을 ‘전하’라고 불렀다. 원인 ① 인물 소개 칸에 학생 과제(“고종에게 … 보고하세요”)가 들어가 AI가 자기를 보고하는 신하로 착각 ② 학생이 “전하”라고 부르자 따라 함 ③ 지시문에 ‘너/학생’ 구분이 없었음. 실제 gpt-oss-120b로 재현(예전 지시문은 한 번 뒤바뀌면 계속 뒤바뀜) → 새 지시문 11번 모두 정상.
- 서버 `chat`: 시스템 지시문을 `buildSystem()` 하나로 통일(예전 rules/guideRules 없앰). [누가 누구인가](너=캐릭터, 학생=persona.user, 호칭=persona.call, 캐릭터 호칭 금지·말끝 통일) → 캐릭터 소개 → [학생 과제·대화 주제 — ‘~하세요’는 학생에게 하는 말] → 시작 메시지 → 선생님 프롬프트(guide) → 캐릭터 자료(예전 facts) → 수업 자료 → 앞선 대화(16개보다 앞은 줄여 적음) → 진행 상황(n/max, 마지막 차례 마무리) → 연기·형식·안전 → [다시 확인].
  - `flipped()`: 왕 캐릭터(KINGS·소개의 왕/황제 등)가 ‘전하·폐하·마마·저하’로 학생을 부르거나, 캐릭터 이름+님/전하로 학생을 부르면 한 번 다시 쓰게 함(`[고쳐 쓰기]`, medium). 그래도 남으면 그 호칭만 학생 호칭으로 바꾼다(`fixCall`). 동사 ‘전하다’는 걸리지 않게 했다. 학생 호칭이 ‘전하’로 정해진 활동은 검사하지 않는다.
  - 시작 메시지(persona.greeting)는 서버가 대화 맨 앞 assistant로 붙인다. 화면은 대화 전체(최대 60개)를 보내고, 서버는 최근 16개 + 앞부분 요약.
  - gpt-oss 생각 깊이: 평소 `CF_EFFORT`(기본 low), 마지막 차례·고쳐 쓰기 `CF_EFFORT_HI`(기본 medium). 마지막 차례 max_tokens 2400.
- `chat_begin`이 `greeting`, `user_role`(persona.user), `call`도 돌려준다.
- 만들기 화면(가상 인물 대화): ② 캐릭터 설정(학생에게 보임: 이미지 `persona.img`(materials 보관함)·이름·소개·학생 역할 `user`·부르는 말 `call`·시작 메시지 `greeting`·추천 질문 `starters`·최대 대화 횟수) ③ 대화 주제와 자료 ④ AI 프롬프트(Gemini로 작성/직접 작성). 예전 ‘말투’·‘AI용 인물 자료’ 칸과 지시문 안의 인물·상황·횟수 칸은 없앴다(예전 facts가 있는 활동은 ‘프롬프트로 옮기기/지우기’ 안내).
- Gemini(`suggest` op:"guide")는 JSON으로 프롬프트 + 시작 메시지·학생 역할·부르는 말·추천 질문을 돌려준다. ‘적용하기’는 비어 있는 캐릭터 칸에만 넣는다.
- 학생 화면: 캐릭터 머리(이미지·이름·소개·나의 역할), 시작 메시지 말풍선, 추천 질문, “대화 n / N”.
- 테스트: `dev/tests/t63.py`(t60·t62 대신), `dev/sql/guide_test.sql`. 실제 모델 확인은 임시 `chat-eval`(cron 키)로 하고 410 빈 함수로 되돌렸다.

**최근 변경 (2026-10-18d): 가상 인물 대화 · AI 대화 지시문(프롬프트) 만들기**
- 생성 폼의 가상 인물 대화 칸에 ‘AI 대화 지시문’ 블록(`pguideHTML`)을 더했다. 탭 두 개: 항목별 설정으로 만들기 / 직접 작성.
- 항목: 활동 유형 6개(`PG_TYPES`), 교과·대상(필수), 인물·상황·학습 목표(필수), 최대 대화 횟수 3/5/8/10(기본 8), 학생 지원 방식(기본 단계별).
- `buildGuide(g)`: 유형마다 구조가 다른 10항목 지시문을 화면에서 만든다(대화 횟수에 맞춘 단계 계획 `pgPlan`, 교과별 정확성 `pgSubjRules`).
- Gemini 키가 있으면 `suggest` op:"guide"로 기본 지시문을 다듬는다. 10개 제목이 다 있어야 쓰고, 아니면 기본 지시문을 쓴다.
- ‘이 활동에 적용하기’ → `persona.guide`(최대 6,000자) + `persona.maxTurns`. 만든 항목은 `persona.gen`. 둘 다 없으면 persona 모양은 예전과 같다.
- 서버: `chat_begin`이 `guide`, `max_turns`를 더 돌려준다. `chat` 함수는 guide가 있을 때만 `guideRules`를 쓴다. 이때 대화 전체(최대 20개)를 보고, 화면이 보낸 `turn`으로 마지막 차례를 알아 종료·피드백을 실행한다(마지막 차례 max_tokens 2000). guide가 없으면 시스템 프롬프트가 예전과 바이트 단위로 같다(45개 경우 비교).
- 알아 둘 점: `persona.guide`는 `facts`처럼 활동 문서 안에 있어 화면에는 안 보이지만 학생 기기가 받는 데이터에는 들어 있다. 학생 첫 화면의 질문 예시 칩(CHAT_STARTERS)은 유형과 관계없이 예전 그대로다.
- 테스트: `dev/tests/t62.py`, `dev/sql/guide_test.sql`.

**최근 변경 (2026-10-18c): 과목 없는 활동의 임시 참가자(guest)**
- 과목 없는 활동 링크·QR로 들어오면 개인 코드 없이 이름·닉네임만 적고 참여한다. 과목 활동은 그대로 코드.
- 서버: `guest_sessions(uid, room_id, tid, nick, nick_key)` + `guest_join`/`my_guests`/`guest_owner`/`guest_can_read` 등. `docs_read/insert/update`, `docs_stamp`, `whoami`, `my_student_id`, `note_can_*`, `chat_begin`에 guest 분기 추가. 모두 setup.sql 맨 끝 근처 한 구역(idempotent). 익명 로그인 허용이 필요하다.
- 클라이언트: `guestGate`/`viewGuestGate`/`guestProbe`, act `guest-join/guest-skip/guest-code/guest-reset`, `S.guest`.
- 한계: 기기당 이름 하나, 다른 활동에서 쓴 이름이면 “새 이름으로 시작”, 초기화하면 이전 글 수정 권한을 잃음, guest는 푸시 없음, 교사 ‘미제출’ 명단에 guest는 안 나옴.
- 테스트: `dev/sql/guest_test.sql`(17단계), `dev/tests/t61.py`.

**진행 중인 작업은 없다**(PR #15까지 병합, 작업 트리 깨끗함). 아래는 확인·후속 과제다.

1. **사용자 쪽 확인 필요 (코드 변경 아님)**
   - 기존 과목 “한국사2 온라인 공동교육과정 A반”에서 👥 수강 학생 고르기 → 저장.
   - 실제 휴대폰에서 학생 “알림 받기”를 켜고, 교사가 공지를 올려 푸시가 오는지 확인.
   - ⚙️ AI 연결 설정에 Gemini 키를 넣고 “저장하고 확인” → 🪄 추천이 실제로 나오는지 확인.
     - 실패하면 `suggest` 로그(`query_logs`)로 모델 이름·응답 형식을 점검한다.
   - 가상 인물 대화가 실제로 답하는지 확인(Cloudflare Secrets).
2. **알려진 개선 후보 (요청받지 않음, 하지 말 것 — 요청 시에만)**
   - 교사 결과 화면에 ❤️ 수 표시.
   - 오늘의 필기 Storage 정책(`note_can_write`)에 수강 여부 확인 추가. 지금은 비수강생에게 활동 자체가 안 보이므로 실질 위험은 낮다.
   - `notify`의 VAPID subject가 `https://ieumind.github.io/`로 고정돼 있다. 다른 설치본은 수정 필요.
   - 체험 모드에서는 수강 학생 고르기를 체험할 수 없다(안내 문구만 표시).

---

## 5. 중요한 개발 원칙 (지금까지 합의)

1. **요청한 부분만 수정한다.** 기존 UI/UX 디자인과 문구를 임의로 바꾸지 않는다. 개선 제안은 말로 하고, 요청이 있을 때만 구현한다.
2. **사용자는 비개발자 교사다.** 답변은 한국어로, 쉬운 말로, 선생님이 할 일을 단계로 적는다.
3. **정확하지 않은 안심 문구를 쓰지 않는다.** 예: “관리자가 볼 수 없어 완전 안전” 같은 문구는 거절하고 사실대로 썼다(관리자 화면에 표시되지 않음 ≠ 기술적으로 접근 불가).
4. **비밀 키는 화면 코드나 저장소에 넣지 않는다.** service_role, Cloudflare, VAPID 비밀 키, Gemini 키 모두 해당한다.
   - 사용자에게 키를 대화창에 붙여 넣게 하지 않는다. Supabase Secrets나 앱 설정 칸에 직접 넣게 안내한다.
5. **기본 교사 이메일을 코드에 넣지 않는다.** 관리자는 setup.sql 마지막 주석의 insert로 등록한다.
6. **학생 대상 AI는 미성년자 사용이 허용되는 서비스로 한다.** Gemini 약관은 18세 미만 대상 앱을 제한하므로 학생 AI는 Cloudflare로 했다. Gemini는 교사 전용 기능(교사 본인 키)에만 쓴다.
7. **DB 변경은 비파괴적으로 한다.**
   - `create or replace`, `alter policy`, `create table if not exists`를 쓰고, `DROP`은 피한다.
   - `setup.sql`에도 같은 내용을 반영하고, 두 번 실행해도 되는지 로컬 Postgres로 확인한다.
8. **하위 호환을 지킨다.** 예전 데이터(`members` 없는 과목, `courseId` 없는 활동, 예전 그룹 키 등)는 예전처럼 동작해야 한다.
9. **매 작업 뒤 확인한다.** Playwright 테스트(가짜 Supabase)와 스크린샷(PC 1280px, 휴대폰 390px)으로 확인한 뒤 커밋 → PR → 사용자에게 Merge 안내.
10. **모바일 우선이다.** 390px에서 가로 스크롤이 생기면 안 된다.
11. **라이트/다크 둘 다 고려한다.** 색은 CSS 변수(`--accent`, `--s1~s4`, `--*-soft`, `--warn` 등)를 쓴다.

---

## 6. 주의 사항

### 6-1. 기존 기능에 영향을 줄 수 있는 부분
- **`docs_read` / `docs_insert` / `docs_update` 정책**: 학생 가시성 전체를 좌우한다.
  - 바꿀 때는 `dev/sql/mem_test.sql` 같은 시나리오를 로컬 Postgres로 먼저 돌린다.
  - 정책은 `alter policy`로만 바꾼다.
- **함수 overload 금지**
  - 같은 이름에 인자가 다른 함수를 새로 만들면 PostgREST가 HTTP 300(모호함)을 낸다. 예전에 `whoami`에서 실제로 났다.
  - 그래서 `push_targets_for`처럼 **새 이름**을 쓴다.
- **예전 함수 정리 금지**: `zz_old_*` 함수는 예전 overload를 이름만 바꿔 둔 것이다.
  - MCP `apply_migration`에서 DROP이 “cancelled”로 보였다가 실제로는 적용된 적이 있다.
  - 함부로 DROP하지 않는다.
- **Edge Function 배포**: MCP `deploy_edge_function`은 파일 내용 전체를 넘겨야 한다. 저장소 파일과 배포본을 항상 같게 유지한다.
- **`course-save`**: `set()`으로 문서 전체를 덮어쓴다. 새 필드를 추가하면 반드시 이전 값을 이어받게 한다.
  - 현재 이어받는 필드: `notices`, `members`, `teacherName`.
- **`repliesOf()`**: heart를 뺀 목록이다. heart가 필요하면 `heartsOf()`를 쓴다.
  - `S.replies`를 직접 `kind` 없이 세는 코드가 몇 군데 있다(활동 시간 계산 등). 영향은 작다.
- **`render()` 전체 다시 그리기**
  - 모달 안의 체크박스처럼 자주 바뀌는 곳은 부분 갱신(`memRefresh`)을 쓴다.
  - 입력 중 다시 그리기는 `dataChanged`가 막는다.
- **`TEACHER_ACTS`**: 교사 전용 새 액션은 여기에 추가해야 한다.
- **하트 문서 id 해시**: `heartKey(S.name)`를 이름 해시로 쓴다.
  - RLS에서 학생 글·댓글은 `data.author`가 `my_student_name(tid)`(“학교 학번 이름” 또는 “학번 이름”)과 같아야 저장된다.
- **로컬 저장 키 (`localStorage`)**

  | 키 | 용도 |
  |---|---|
  | `nonjae.theme` | 테마 |
  | `nonjae.seen` | 새 글 표시 |
  | `nonjae.pushhide` | 푸시 안내 숨김 |
  | `nonjae.tourdone` | 둘러보기 완료 |
  | `nonjae.hlabel` / `hsort` / `hsub` | 학생 카드 라벨·정렬 |
  | `nonjae.group.<cid>[.<해시>]` | 그룹 기억 |

### 6-2. 알려진 오류·한계
- **Web Push**
  - 실제 기기에서 테스트하지 않았다.
  - iOS는 홈 화면 설치 앱(16.4 이상)에서만 받는다.
  - 헤드리스 브라우저에서는 알림 권한이 `denied`로 보인다.
- **Gemini 모델 이름**: 바뀔 수 있다. `suggest/index.ts`의 `MODELS` 순서대로 시도하고, 404면 다음 모델로 넘어간다. 되는 모델은 `teacher_ai.model`에 기억한다.
- **작업 환경 네트워크 제한**
  - 셸에서 supabase.co, googleapis 같은 외부 사이트가 프록시 403으로 막힌다.
  - npm 레지스트리도 안 될 수 있다.
  - 서버 확인은 Supabase MCP 도구(`execute_sql`, `query_logs` 등)로 한다.
- **테스트 관련**
  - 예전 테스트 `t27`의 S3 부분은 새 탭에서 로그인 없이 진행해 실패한다(테스트 자체 문제, 앱 문제 아님).
  - 테스트들은 같은 브라우저 컨텍스트에서 `localStorage`를 공유한다. 그래서 그룹 기억처럼 기기별 값은 순서에 영향받을 수 있다.

### 6-3. 테스트 방법 (새 세션에서)
1. Playwright(Python)와 Chromium은 환경에 있다(`/opt/pw-browsers`).
2. 저장소 루트에서 아래를 실행한다. `/tmp/claude-0/smoke/p17~p26.html`, `pdemo.html`이 만들어진다.
   ```
   python3 dev/tests/build_pages.py
   ```
3. 테스트를 돌린다.
   ```
   python3 dev/tests/t35.py
   ```
   주요 테스트 묶음:

   | 테스트 | 확인하는 것 |
   |---|---|
   | `t35` | 수강 학생·하트·댓글·자동 그룹 |
   | `t29` | 과목 대시보드·공지·오류건의 |
   | `t32` | AI 추천 |
   | `t31` | 둘러보기 |
   | `t34` | 체험 AI |
   | `t30` | 체험 모드 |
   | `t20` | 오늘의 필기 |
   | `t26` | 카드 라벨 |
   | `t28` | 고급 설정 |

   스크린샷은 `/tmp/claude-0/smoke/mob/`에 저장된다.
4. `index.html`을 고친 뒤에는 **반드시 `build_pages.py`를 다시 실행**한다. 페이지는 복사본이다.
5. 문법 검사:
   ```
   node -e "const h=require('fs').readFileSync('index.html','utf8');[...h.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)].forEach(x=>new Function(x[1]))"
   ```
6. SQL 검사:
   - 로컬 Postgres를 만들고 `dev/sql/stub.sql` → `dev/sql/storstub.sql` → `supabase/setup.sql`(두 번) → `dev/sql/mem_test.sql` 순서로 실행한다.
   - 이전 세션의 Postgres는 `/var/tmp/pgt`(포트 5499)였다. 새 컨테이너에는 없으니 `initdb`부터 해야 한다.
7. 가짜 서버 `mock.js`는 `supabase.createClient`를 가짜로 바꾼다.
   - 주소에 `?who=teacher` 또는 `?who=anon`을 붙여 역할을 정한다.
   - 데이터는 `localStorage.__sbmock`에 저장된다.
   - RPC·Storage·Functions(`chat`/`notify`/`suggest`)를 흉내 낸다. 새 RPC를 만들면 `mock.js`에도 추가해야 한다.

---

## 7. 다음 작업 순서 (우선순위)

1. **새 세션 시작 점검 (코드 변경 없음)**
   - `git fetch && git checkout supabase-version && git pull`. main과 같은지 확인(`f2fc591` 이후).
   - `docs/HANDOVER.md`, `README.md`를 읽는다.
   - Supabase MCP로 상태를 확인한다: `list_edge_functions`(chat v2 / notify v2 / suggest v1), `get_advisors`(보안 경고).
   - `python3 dev/tests/build_pages.py` 후 `t35`, `t29`를 돌려 기준선을 확인한다.
2. **사용자 실사용 확인을 도울 것**: 수강 학생 저장, 실기기 푸시, Gemini 키 확인, AI 대화. 문제가 나오면 Edge Function 로그부터 확인한다.
3. **사용자의 새 요청 처리**: 5장 원칙을 지키며, 요청 범위만 고친다.
4. **매 작업 마무리**
   1. 테스트와 스크린샷을 확인한다.
   2. 필요하면 `setup.sql`, `README.md`, `privacy.html`을 갱신한다.
   3. 커밋(작성자·트레일러 규칙 지킴) → push → `gh api`로 PR을 연다.
   4. 한국어로 무엇이 바뀌었는지, 선생님이 할 일(Merge 등)을 짧게 안내한다.
