# 개발용 파일 (앱 동작과 무관)

- `tests/` — Playwright(Python) 화면 테스트. 먼저 `python3 dev/tests/build_pages.py`로 테스트 페이지를 만든 뒤 `python3 dev/tests/t35.py` 처럼 실행.
  `mock.js`는 가짜 Supabase(주소 뒤 `?who=teacher` / `?who=anon`).
- `sql/` — 로컬 Postgres에서 `supabase/setup.sql`을 시험할 때 쓰는 auth·storage 흉내(`stub.sql`, `storstub.sql`)와 과목 수강 RLS 시나리오(`mem_test.sql`).

자세한 내용은 `docs/HANDOVER.md` 6-3 참고.
