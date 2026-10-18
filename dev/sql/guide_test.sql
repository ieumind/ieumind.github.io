-- 가상 인물 대화: chat_begin이 선생님 지시문(persona.guide)과 최대 질문 수를 돌려주는지
-- 실행: stub.sql → storstub.sql → setup.sql 뒤에  psql -d t -f dev/sql/guide_test.sql
-- 기대: with guide → guide·max_turns 5·greeting·user_role·call (img·starters는 서버에 필요 없어 안 돌려줌) / no guide → guide 빈 글(t), max_turns 8 / 6000자 넘는 지시문 → 6000자로 잘림
\set QUIET 1
\pset tuples_only on
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
insert into teachers(email, uid) values ('a@x.kr', '00000000-0000-0000-0000-00000000000a') on conflict (email) do nothing;
begin; set local role authenticated; select _as(:'TA');
insert into docs(col,id,data) values ('rooms','rg','{"title":"g","template":"chat","status":"open","prompt":"문을 열까?","persona":{"name":"흥선대원군","maxTurns":5,"guide":"[1. 활동 개요]\n- 테스트","greeting":"어서 오게.","user":"젊은 관리","call":"자네","img":"https://x/y.jpg","starters":["안녕하세요"]}}');
insert into docs(col,id,data) values ('rooms','rg0','{"title":"g0","template":"chat","status":"open","prompt":"q","persona":{"name":"고종"}}');
insert into docs(col,id,data) values ('rooms','rgl', jsonb_build_object('title','gl','template','chat','status','open','prompt','q','persona', jsonb_build_object('name','긴','guide', repeat('가', 7000))));
select 'with guide', (chat_begin('rg')::jsonb) - 'context' - 'facts' - 'prompt' - 'about' - 'remaining';
select 'no guide', (chat_begin('rg0')::jsonb) ->> 'guide' = '', chat_begin('rg0')::jsonb ->> 'max_turns';
select 'long guide length', char_length(chat_begin('rgl')::jsonb ->> 'guide');
rollback;
