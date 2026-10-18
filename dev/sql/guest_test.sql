-- 임시 참가자(과목 없는 활동에 이름·닉네임만 넣고 참여) 권한 시나리오
-- 실행: stub.sql → storstub.sql → setup.sql(두 번) 뒤에  psql -d t -f dev/sql/guest_test.sql
-- 각 줄 앞의 ‘기대:’ 값과 실제 출력이 같아야 한다
\set QUIET 1
\pset tuples_only on
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set TB '{"sub":"00000000-0000-0000-0000-00000000000b","email":"b@x.kr","is_anonymous":false}'
\set G1 '{"sub":"00000000-0000-0000-0000-0000000000c1","is_anonymous":true}'
\set G2 '{"sub":"00000000-0000-0000-0000-0000000000c2","is_anonymous":true}'
\set G3 '{"sub":"00000000-0000-0000-0000-0000000000c3","is_anonymous":true}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'

-- 선생님 A: 코드 학생 1명, 과목 c1, 활동 여러 개 / 선생님 B: 과목 없는 활동 1개
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','김가온','AAA111');
insert into docs(col,id,data) values
 ('courses','c1','{"title":"통합과학","members":["11111111-1111-1111-1111-111111111111"]}'),
 ('rooms','r0','{"title":"과목 없는 활동","reveal":"after","status":"open"}'),
 ('rooms','r0b','{"title":"두 번째 과목 없는 활동","status":"open"}'),
 ('rooms','r0t','{"title":"선생님만 보기","reveal":"teacher","status":"open"}'),
 ('rooms','rc','{"title":"과목 활동","courseId":"c1","reveal":"after","status":"open"}'),
 ('rooms','rd','{"title":"작성 중","status":"draft"}'),
 ('rooms','ra','{"title":"보관","status":"archived"}'),
 ('rooms','rchat','{"title":"인물 대화","template":"chat","status":"open","persona":{"name":"여운형","maxTurns":2}}');
commit;
begin; set local role authenticated; select _as(:'TB');
insert into docs(col,id,data) values ('rooms','rb','{"title":"B 선생님 활동","status":"open"}');
commit;
begin; set local role authenticated; select _as(:'S1'); select claim_student('10301','김가온','AAA111') is not null; commit;

\echo == 1. whoami (기대: guest_room true / false / false / false / false)
begin; set local role authenticated; select _as(:'G1');
select 'r0 free', (whoami('r0')::jsonb ->> 'guest_room'), (whoami('r0')::jsonb ->> 'guest_title');
select 'rc course', (whoami('rc')::jsonb ->> 'guest_room');
select 'rd draft', (whoami('rd')::jsonb ->> 'guest_room');
select 'ra archived', (whoami('ra')::jsonb ->> 'guest_room');
select 'no ref', (whoami(null)::jsonb ->> 'guest_room');
commit;
begin; set local role authenticated; select _as(:'S1');
select 'S1 coded on r0 (기대: false)', (whoami('r0')::jsonb ->> 'guest_room');
select 'S1 guest_join (기대: student)', guest_join('r0','아무개')::jsonb ->> 'reason';
commit;
begin; set local role authenticated; select _as(:'TA');
select 'teacher guest_join (기대: denied)', guest_join('r0','선생')::jsonb ->> 'reason';
commit;

\echo == 2. 참가 (기대: denied denied denied ok)
begin; set local role authenticated; select _as(:'G1');
select 'join course room', guest_join('rc','철수')::jsonb ->> 'reason';
select 'join draft', guest_join('rd','철수')::jsonb ->> 'reason';
select 'join archived', guest_join('ra','철수')::jsonb ->> 'reason';
select 'join free', guest_join('r0','철수')::jsonb ->> 'ok';
select 'join again same room (기대: true 철수)', guest_join('r0','다른이름')::jsonb ->> 'ok', guest_join('r0','다른이름')::jsonb ->> 'name';
commit;

\echo == 3. 이름 규칙 (기대: taken number number reserved empty long ok)
begin; set local role authenticated; select _as(:'G2');
select 'dup name', guest_join('r0',' 철 수 ')::jsonb ->> 'reason';
select 'student-like', guest_join('r0','10301 김가온')::jsonb ->> 'reason';
select 'number only', guest_join('r0','12345')::jsonb ->> 'reason';
select 'reserved', guest_join('r0','선생님')::jsonb ->> 'reason';
select 'empty', guest_join('r0','   ')::jsonb ->> 'reason';
select 'long', guest_join('r0',repeat('가',21))::jsonb ->> 'reason';
select 'ok', guest_join('r0','민지')::jsonb ->> 'name';
commit;

\echo == 4. 이름은 기기마다 하나 (기대: 철수)
begin; set local role authenticated; select _as(:'G1');
select 'second room keeps nick', guest_join('r0b','영희')::jsonb ->> 'name';
select 'my_guests', json_array_length(my_guests());
select 'whoami nick', whoami('r0t')::jsonb ->> 'guest_nick', whoami('r0t')::jsonb ->> 'guest_room';
commit;

\echo == 5. 보이는 것 (기대 G1: r0,r0b / G2: r0 / G3: 없음)
begin; set local role authenticated; select _as(:'G1'); select 'G1 sees', string_agg(col||':'||id, ',' order by col,id) from docs; commit;
begin; set local role authenticated; select _as(:'G2'); select 'G2 sees', string_agg(col||':'||id, ',' order by col,id) from docs; commit;
begin; set local role authenticated; select _as(:'G3'); select 'G3 sees', coalesce(string_agg(col||':'||id, ',' order by col,id), '(none)') from docs; commit;

\echo == 6. 글쓰기 (기대: ok 한 번, 그다음 막힘 5번)
begin; set local role authenticated; select _as(:'G1');
insert into docs(col,id,data) values ('posts','p-r0-g1','{"roomId":"r0","author":"철수","status":"submitted","body":{"a":"철수 생각"}}'); select 'G1 post in r0 ok';
commit;
begin; set local role authenticated; select _as(:'G1');
insert into docs(col,id,data) values ('posts','p-bad1','{"roomId":"r0","author":"영수","status":"submitted"}');
rollback;
begin; set local role authenticated; select _as(:'G1');
insert into docs(col,id,data) values ('posts','p-bad2','{"roomId":"rc","author":"철수","status":"submitted"}');
rollback;
begin; set local role authenticated; select _as(:'G1');
insert into docs(col,id,data) values ('posts','p-bad3','{"roomId":"rb","author":"철수","status":"submitted"}');
rollback;
begin; set local role authenticated; select _as(:'G1');
insert into docs(col,id,data) values ('posts','p-bad4','{"roomId":"r0t","author":"철수","status":"submitted"}');
rollback;
begin; set local role authenticated; select _as(:'G3');
insert into docs(col,id,data) values ('posts','p-bad5','{"roomId":"r0","author":"익명","status":"submitted"}');
rollback;

\echo == 7. 친구 글 보기 (기대: G2는 G1 글 보임 1 / r0t는 선생님만 보기라 0)
begin; set local role authenticated; select _as(:'G2'); select 'G2 sees G1 post in open room', count(*) from docs where col = 'posts' and id = 'p-r0-g1'; commit;
begin; set local role authenticated; select _as(:'G2');
insert into docs(col,id,data) values ('posts','p-r0-g2','{"roomId":"r0","author":"민지","status":"submitted"}'); select 'G2 post ok';
commit;
begin; set local role authenticated; select _as(:'G1'); select 'G1 sees G2 post', count(*) from docs where col = 'posts' and id = 'p-r0-g2'; commit;
-- ‘선생님만 보기’ 활동: 두 사람이 모두 들어와 글을 쓰되 서로의 글은 보이지 않아야 한다
begin; set local role authenticated; select _as(:'G1'); select 'G1 join r0t', guest_join('r0t','철수')::jsonb ->> 'ok';
insert into docs(col,id,data) values ('posts','p-r0t-g1','{"roomId":"r0t","author":"철수","status":"submitted"}'); commit;
begin; set local role authenticated; select _as(:'G2'); select 'G2 join r0t', guest_join('r0t','민지')::jsonb ->> 'ok';
insert into docs(col,id,data) values ('posts','p-r0t-g2','{"roomId":"r0t","author":"민지","status":"submitted"}');
select 'G2 sees G1 post in teacher-only room (기대 0)', count(*) from docs where col = 'posts' and id = 'p-r0t-g1';
select 'G2 sees own post in teacher-only room (기대 1)', count(*) from docs where col = 'posts' and id = 'p-r0t-g2'; commit;

\echo == 8. 고치기·지우기 (기대: 1 0 0 0)
begin; set local role authenticated; select _as(:'G1');
with u as (update docs set data = data || '{"body":{"a":"고친 생각"}}' where col = 'posts' and id = 'p-r0-g1' returning 1) select 'G1 edits own', count(*) from u;
with u as (update docs set data = data || '{"body":{"a":"남이 고침"}}' where col = 'posts' and id = 'p-r0-g2' returning 1) select 'G1 edits G2', count(*) from u;
with d as (delete from docs where col = 'posts' and id = 'p-r0-g1' returning 1) select 'G1 deletes own', count(*) from d;
commit;
begin; set local role authenticated; select _as(:'G1');
update docs set data = jsonb_set(data, '{author}', '"민지"') where col = 'posts' and id = 'p-r0-g1'; select 'G1 renames author (기대: 오류로 막힘)';
rollback;
begin; set local role authenticated; select _as(:'G1');
with u as (update docs set data = jsonb_set(data, '{roomId}', '"rb"') where col = 'posts' and id = 'p-r0-g1' returning 1) select 'G1 moves post to rb (기대 0 또는 오류)', count(*) from u;
rollback;

\echo == 9. 댓글·하트 (기대: ok ok / 막힘)
begin; set local role authenticated; select _as(:'G2');
insert into docs(col,id,data) values ('replies','x1','{"roomId":"r0","postId":"p-r0-g1","author":"민지","kind":"comment","text":"좋아요"}'); select 'G2 comment ok';
insert into docs(col,id,data) values ('replies','h-p-r0-g1-k','{"roomId":"r0","postId":"p-r0-g1","author":"민지","kind":"heart","on":true}'); select 'G2 heart ok';
commit;
begin; set local role authenticated; select _as(:'G2');
insert into docs(col,id,data) values ('replies','x2','{"roomId":"r0","postId":"p-r0-g1","author":"선생님","kind":"teacher","text":"가짜 피드백"}');
rollback;
begin; set local role authenticated; select _as(:'G1'); select 'G1 sees comment on own post (기대 2)', count(*) from docs where col = 'replies'; commit;

\echo == 10. 선생님 피드백 (기대: G1 2 / G2 1 / G3 0)
begin; set local role authenticated; select _as(:'TA');
insert into docs(col,id,data) values ('treplies','f1','{"roomId":"r0","postId":"p-r0-g1","author":"선생님","kind":"teacher","text":"철수에게"}'),
  ('treplies','f2','{"roomId":"r0","postId":"_class","author":"선생님","kind":"class","text":"모두에게"}');
commit;
begin; set local role authenticated; select _as(:'G1'); select 'G1 feedback', count(*) from docs where col = 'treplies'; commit;
begin; set local role authenticated; select _as(:'G2'); select 'G2 feedback', count(*) from docs where col = 'treplies'; commit;
begin; set local role authenticated; select _as(:'G3'); select 'G3 feedback', count(*) from docs where col = 'treplies'; commit;

\echo == 11. 선생님 시점 (기대: A는 r0 글 2개 보임 / B는 A 자료 0)
begin; set local role authenticated; select _as(:'TA'); select 'TA sees guest posts in r0', count(*) from docs where col = 'posts' and room_id = 'r0'; select 'owner is guest uid', owner from docs where id = 'p-r0-g1'; commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB sees A data', count(*) from docs where id <> 'rb'; commit;

\echo == 12. 코드 학생은 그대로 (기대: 예전처럼 과목·활동이 보이고, 코드 학생 이름표가 아닌 글쓴이는 막힘)
begin; set local role authenticated; select _as(:'S1'); select 'S1 sees', string_agg(col||':'||id, ',' order by col,id) from docs where col in ('courses','rooms'); commit;
begin; set local role authenticated; select _as(:'S1');
insert into docs(col,id,data) values ('posts','p-s1','{"roomId":"rc","author":"10301 김가온","status":"submitted"}'); select 'S1 post ok';
commit;
begin; set local role authenticated; select _as(:'S1');
insert into docs(col,id,data) values ('posts','p-s1x','{"roomId":"rc","author":"철수","status":"submitted"}');
rollback;

\echo == 13. 인물 대화 (기대: G1 ok / G3 denied)
begin; set local role authenticated; select _as(:'G1'); select 'G1 join rchat', guest_join('rchat','철수')::jsonb ->> 'ok';
select 'G1 chat', chat_begin('rchat')::jsonb ->> 'ok'; commit;
begin; set local role authenticated; select _as(:'G3'); select 'G3 chat', chat_begin('rchat')::jsonb ->> 'reason'; commit;

\echo == 14. 학습 나눔 폴더 (기대: G1 uid / G3 null / 쓰기 true false)
begin; set local role authenticated; select _as(:'G1');
select 'my_student_id', my_student_id('r0');
select 'note_can_write own folder', note_can_write('r0/00000000-0000-0000-0000-0000000000c1/1.jpg');
select 'note_can_write other folder', note_can_write('r0/00000000-0000-0000-0000-0000000000c2/1.jpg');
commit;
begin; set local role authenticated; select _as(:'G3'); select 'G3 my_student_id', coalesce(my_student_id('r0')::text, 'null'); commit;

\echo == 15. 선생님이 막히면 참가자도 못 본다 (기대: 0)
reset role; insert into teachers(email, uid, blocked) values ('a@x.kr', '00000000-0000-0000-0000-00000000000a', true) on conflict (email) do update set blocked = true, uid = excluded.uid;
begin; set local role authenticated; select _as(:'G1'); select 'blocked teacher: G1 sees', count(*) from docs; commit;
reset role; update teachers set blocked = false where email = 'a@x.kr';

\echo == 16. 과목이 생기면 참가자는 더 못 본다 (기대: 0)
begin; set local role authenticated; select _as(:'TA'); update docs set data = data || '{"courseId":"c1"}' where col = 'rooms' and id = 'r0b'; commit;
begin; set local role authenticated; select _as(:'G1'); select 'room moved to a course: G1 sees r0b', count(*) from docs where col = 'rooms' and id = 'r0b'; commit;
begin; set local role authenticated; select _as(:'TA'); update docs set data = data - 'courseId' where col = 'rooms' and id = 'r0b'; commit;

\echo == 17. upsert(INSERT … ON CONFLICT) 로 남의 글을 덮어쓸 수 없다 (기대: G1 글 수정 ok / G2 거부)
begin; set local role authenticated; select _as(:'G1'); select 'G1 join r0c', guest_join('r0','철수')::jsonb ->> 'ok';
insert into docs(col,id,data) values ('posts','p-up','{"roomId":"r0","author":"철수","status":"submitted","text":"1"}');
insert into docs(col,id,data) values ('posts','p-up','{"roomId":"r0","author":"철수","status":"submitted","text":"2"}') on conflict (col,id,tid) do update set data = excluded.data;
select 'G1 upsert own', data->>'text' from docs where id = 'p-up'; commit;
begin; set local role authenticated; select _as(:'G2'); select 'G2 join r0', guest_join('r0','영희')::jsonb ->> 'ok';
insert into docs(col,id,data) values ('posts','p-up','{"roomId":"r0","author":"영희","status":"submitted","text":"hack"}') on conflict (col,id,tid) do update set data = excluded.data;
rollback;
reset role; select 'p-up after attack', data->>'text' from docs where id = 'p-up';
