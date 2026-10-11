# 생각이음 · GitHub + Supabase 설정 안내

생각하고, 만나고, 다시 생각하는 수업 플랫폼 **생각이음**을 GitHub Pages에 올려 반 전체가 함께 쓰기 위한 안내입니다.
처음 한 번 30~40분쯤 걸려요. 순서대로 따라 하시면 됩니다.

```
생각이음/
├─ index.html                       ← 앱 (맨 위 두 줄에 Supabase 주소·키를 넣어요)
├─ supabase/setup.sql               ← Supabase에 붙여 넣을 설정 (표·권한 규칙)
└─ .github/workflows/keepalive.yml  ← 방학 중에도 Supabase가 멈추지 않게 (선택)
```

## 어떻게 동작하나요

| 누구 | 들어오는 방법 | 할 수 있는 일 |
|---|---|---|
| 교사 | 주소 끝에 `#teacher` → 구글 로그인 (누구나 바로 자기 교사 공간) | 활동 만들기·관리, 학생 코드 발급, 결과·피드백 |
| 학생 | 활동 링크·QR → 처음 한 번 **학번·이름·개인 코드** | 자기 글 쓰기·고치기, 친구 생각 보기 |

- 학생은 로그인하지 않아요. 개인 코드는 학생에게 보이지 않고, 맞는 코드를 넣은 기기만 그 학생으로 글을 쓸 수 있어요.
- **교사끼리는 서로의 활동·학생 명단·학생 글을 볼 수 없어요.** 교사마다 자기 학생 명단과 코드를 따로 만들어요.
- 학생은 코드를 넣은 선생님 반의 활동만 봐요. 다른 선생님의 활동 링크로 들어오면 그 선생님이 준 코드를 한 번 더 넣어요.
- 권한은 Supabase 서버 규칙이 지켜요: 학생은 자기 글만 쓰고 고칠 수 있고, 활동·교사 메모·교사 피드백·학생 코드는 교사만 다뤄요. ‘선생님만 보기’ 활동의 학생 글은 다른 학생에게 아예 전달되지 않아요.

---

## 1. Supabase 프로젝트 만들기

1. <https://supabase.com> 에서 가입하고 **New project**를 눌러요.
2. 이름: `saenggak-ieum`(아무거나), **Database Password**: 아무 데나 적어 두세요(앱에는 안 써요).
3. **Region**: `Northeast Asia (Seoul)`을 고르면 빨라요. 무료(Free) 요금제로 만들면 됩니다.

## 2. 설정 SQL 실행

1. 왼쪽 메뉴 **SQL Editor** → **New query**.
2. `supabase/setup.sql` 파일 내용을 **통째로** 붙여 넣고 **Run**.
3. 아래에 `Success`가 보이면 끝. 여러 번 실행해도 괜찮아요.

## 3. 학생용 익명 접속 켜기

**Authentication → Sign In / Providers** (또는 Providers) 에서
**Allow anonymous sign-ins** 를 켜고 저장해요. (학생이 로그인 없이 들어오는 데 필요해요)

## 4. 교사용 구글 로그인 연결

구글 쪽에서 ‘로그인 버튼용 열쇠’를 만들어 Supabase에 넣는 과정이에요.

1. Supabase **Authentication → Sign In / Providers → Google** 을 열면 **Callback URL**
   (`https://xxxx.supabase.co/auth/v1/callback`)이 보여요. 복사해 두세요.
2. <https://console.cloud.google.com> → 위쪽에서 **새 프로젝트** 만들기.
3. **API 및 서비스 → OAuth 동의 화면**: 사용자 유형 **외부**, 앱 이름 `생각이음`, 지원 이메일·개발자 이메일에 본인 메일 → 저장.
   - 게시 상태가 ‘테스트’이면 **테스트 사용자**에 교사 구글 이메일을 추가하세요. (또는 ‘앱 게시’를 누르면 누구나 로그인 화면은 볼 수 있지만, 교사 권한은 7단계 명단에 있는 사람만 가져요)
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
   - 애플리케이션 유형: **웹 애플리케이션**
   - **승인된 리디렉션 URI**: 1번에서 복사한 Callback URL 붙여 넣기 → 만들기
5. 나온 **클라이언트 ID**와 **클라이언트 보안 비밀번호**를 Supabase Google 화면에 붙여 넣고 **Enable** → 저장.

## 5. 앱 주소 등록

GitHub Pages 주소가 `https://아이디.github.io/저장소이름/` 이라면,
Supabase **Authentication → URL Configuration** 에서

- **Site URL**: `https://아이디.github.io/저장소이름/`
- **Redirect URLs**: `https://아이디.github.io/저장소이름/**` 추가

(GitHub 주소를 아직 모르면 8단계를 먼저 하고 돌아와도 돼요.)

## 6. 앱에 Supabase 주소·키 넣기

Supabase **Project Settings → API (API Keys)** 에서

- **Project URL** (`https://xxxx.supabase.co`)
- **anon public** 키 (또는 **Publishable key**)

를 복사해서 `index.html` 맨 위(script 시작 부분)의 두 줄에 넣어요.

```js
const SUPABASE_URL = "https://xxxx.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOi...";   // anon public 키
```

> anon(공개) 키는 원래 웹페이지에 넣어 공개하는 키예요. 보호는 2단계의 규칙이 맡아요.
> **service_role(비밀) 키는 절대 넣지 마세요.**

## 7. 관리자(나) 등록 · 교사 가입

구글로 로그인하는 선생님은 **누구나 바로 자기 교사 공간**이 생겨요. (서로의 자료는 보이지 않아요)
나를 **관리자**로 등록해 두면, 교사 화면의 **👩‍🏫 교사 관리**에서 가입한 교사 목록(활동·학생·사진 용량)을 보고 문제가 있는 계정을 **막을** 수 있어요.

```sql
insert into public.teachers (email, admin) values ('me@school.kr', true) on conflict (email) do update set admin = true;
```

> 다른 선생님도 로그인하려면 Google Cloud의 **Google 인증 플랫폼 → 대상 → 앱 게시**를 해 두세요. (무료, 로고를 올리지 않으면 심사 없음)
> ‘테스트’ 상태로 두면 테스트 사용자로 추가한 계정만 로그인할 수 있어요.

## 8. GitHub에 올리기

1. 저장소에 이 폴더의 파일(`index.html`, `supabase/`, `.github/`, `README.md`)을 올려요.
2. 저장소 **Settings → Pages → Build and deployment**: Source `Deploy from a branch`, Branch `main` / `(root)` → Save.
3. 1~2분 뒤 `https://아이디.github.io/저장소이름/` 으로 열려요.

## 9. (권장) 방학 중 멈춤 방지

Supabase 무료 프로젝트는 **1주일 동안 아무도 안 쓰면 일시 정지**돼요.
`.github/workflows/keepalive.yml` 이 사흘마다 가볍게 접속해서 이를 막아요.

저장소 **Settings → Secrets and variables → Actions → New repository secret** 으로 두 개를 넣어요.

- `SUPABASE_URL` = Project URL
- `SUPABASE_ANON_KEY` = anon public 키

**Actions** 탭에서 `supabase-keepalive` → **Run workflow** 로 한 번 시험해 볼 수 있어요.
그래도 멈췄다면 Supabase 대시보드에서 **Restore** 를 누르면 다시 켜져요.

---

## 처음 수업 준비

1. `https://아이디.github.io/저장소이름/#teacher` 로 들어가 **구글 계정으로 로그인**.
2. **📋 내 수업 → 👥 학생 코드** → 나이스에서 복사한 `학번 이름`을 한 줄에 한 명씩 붙여 넣고 **추가하고 코드 만들기**.
3. **🖨 코드 쪽지 인쇄**로 잘라서 나눠 줘요. (코드를 잃어버리면 같은 화면에서 확인하거나 **새 코드**)
4. 활동을 만들고 **🔗 학생 링크 복사** 또는 **QR 코드**를 띄워요. (학생 링크 설정은 따로 하지 않아도 돼요)
5. 학생은 링크로 들어와 처음 한 번 **학번·이름·코드**를 넣으면, 그 기기에서는 다시 묻지 않아요.

## 알아 두면 좋은 점

- **AI 가상 인물 대화**는 Claude 안에서만 무료로 동작해요. GitHub 버전에서는 이 활동의 대화 단계에 ‘대화 없이 다음 단계로’가 보여요. (AI 연결은 Supabase Edge Function + Groq/유료 API로 따로 붙일 수 있어요)
- **학생 개인정보**: 학번·이름만 저장해요. 학교 개인정보 담당자에게 사용 사실을 알려 두세요.
- **백업**: 활동 설정 탭의 **⬇ 결과 내보내기(CSV)** 로 주기적으로 받아 두세요.
- **📸 오늘의 필기 사진**: 사진은 Supabase Storage(무료 1GB)의 비공개 보관함 `notes`에 저장돼요. 학생 기기에서 한 장에 0.2~0.4MB로 줄여 올리니 대략 3,000~5,000장까지 담겨요. 학기가 끝나면 지난 활동을 삭제하거나 Storage에서 정리해 주세요.
- **무료 한도**: 데이터 500MB, 월 전송량 5GB 정도. 글 위주 수업에는 넉넉하지만, ‘손으로 그리기’를 많이 쓰면 전송량이 늘어요.
- Claude 안의 예전 데이터는 자동으로 옮겨지지 않아요.

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 위쪽에 ‘미리보기 모드 · 연결 오류’ | 6단계 주소·키 오타, 3단계 익명 접속 켜기 |
| 학생이 코드를 넣어도 ‘맞지 않아요’ | 👥 학생 코드에서 학번·이름 철자 확인 (띄어쓰기는 무시해요) |
| 교사 로그인이 안 되는 다른 선생님 | Google 인증 플랫폼의 ‘앱 게시’ 또는 테스트 사용자 추가, 교사 관리에서 막힌 계정인지 |
| 구글 로그인 뒤 오류 화면 | 4단계 리디렉션 URI, 5단계 Redirect URLs |
| 다른 기기의 글이 바로 안 보임 | 2단계 SQL을 다시 실행(실시간 반영 켜기 포함), 새로고침 |
