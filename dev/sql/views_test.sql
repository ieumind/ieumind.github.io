\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
insert into teachers values ('b@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set TB '{"sub":"00000000-0000-0000-0000-00000000000b","email":"b@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
\set S2 '{"sub":"00000000-0000-0000-0000-0000000000b2","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','김가온','AAA111'),('22222222-2222-2222-2222-222222222222','11005','나다은','AAA222');
insert into docs(col,id,data) values ('courses','c1','{"title":"통합과학","members":["11111111-1111-1111-1111-111111111111"]}'),('rooms','r1','{"title":"c1활동","courseId":"c1"}'),('rooms','r0','{"title":"과목없음"}');
commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 claim', claim_student('10301','김가온','AAA111'); commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 claim', claim_student('11005','나다은','AAA222'); commit;
begin; set local role authenticated; select _as(:'S1'); select room_view('r1'); select room_view('r1'); select room_view('r0'); select room_view('nope'); commit;
begin; set local role authenticated; select _as(:'S2'); select room_view('r1'); select room_view('r0'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 direct read', count(*) from room_views; rollback;
begin; set local role authenticated; select _as(:'S1'); select 'S1 viewers', count(*) from room_viewers('r1'); commit;
begin; set local role authenticated; select _as(:'TA'); select 'TA r1', string_agg(student_id::text||' n='||n, ',') from room_viewers('r1'); select 'TA r0', count(*) from room_viewers('r0'); commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB r1', count(*) from room_viewers('r1'); commit;
