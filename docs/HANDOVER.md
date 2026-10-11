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
- 공개 주소: <https://taeneuu.github.io/thinklink/>
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
- **오늘의 필기**: 미제출 필터, 재제출 요청, 다음 시간용 복제.
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
- **호스팅**: GitHub Pages. 저장소 `taeneuu/thinklink`의 main 루트를 그대로 배포한다.
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

---

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
- **저장소**: `taeneuu/thinklink`. 기본 브랜치 `main` → GitHub Pages.
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
  gh api repos/taeneuu/thinklink/pulls -f title=… -f head=supabase-version -f base=main -F body=@파일
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
   - `notify`의 VAPID subject가 `https://taeneuu.github.io/thinklink/`로 고정돼 있다. 다른 설치본은 수정 필요.
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
