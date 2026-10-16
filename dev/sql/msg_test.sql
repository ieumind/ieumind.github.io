\set QUIET 1
\pset tuples_only on
insert into teachers(email,uid,name) values ('a@x.kr','00000000-0000-0000-0000-00000000000a','이태형') on conflict (email) do update set uid=excluded.uid, name=excluded.name;
insert into teachers(email,uid) values ('b@x.kr','00000000-0000-0000-0000-00000000000b') on conflict (email) do update set uid=excluded.uid;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set TB '{"sub":"00000000-0000-0000-0000-00000000000b","email":"b@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
\set S2 '{"sub":"00000000-0000-0000-0000-0000000000b2","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','김가온','AAA111'),('22222222-2222-2222-2222-222222222222','11005','나다은','AAA222');
commit;
begin; set local role authenticated; select _as(:'TB');
insert into students(id,number,name,code) values ('33333333-3333-3333-3333-333333333333','20101','다른반','BBB333');
commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 claim', claim_student('10301','김가온','AAA111'); commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 claim', claim_student('11005','나다은','AAA222'); commit;
-- 교사 A: S1 + B반 학생(무시되어야)
begin; set local role authenticated; select _as(:'TA'); select 'send', msg_send(array['11111111-1111-1111-1111-111111111111','33333333-3333-3333-3333-333333333333']::uuid[], '준비물', '내일 색연필 가져오세요'); commit;
begin; set local role authenticated; select _as(:'TA'); select 'send2', msg_send(array['11111111-1111-1111-1111-111111111111','22222222-2222-2222-2222-222222222222']::uuid[], '', '수행평가 다시 확인'); commit;
begin; set local role authenticated; select _as(:'TA'); select 'empty', msg_send(array['11111111-1111-1111-1111-111111111111']::uuid[], 't', '  '); commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB to A student', msg_send(array['11111111-1111-1111-1111-111111111111']::uuid[], 't', 'hack'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'student send', msg_send(array['22222222-2222-2222-2222-222222222222']::uuid[], 't', 'hack'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 direct', count(*) from student_msgs; rollback;
begin; set local role authenticated; select _as(:'S1'); select 'S1 inbox', json_array_length(my_msgs()), (my_msgs()->0->>'teacher'), (my_msgs()->1->>'body'); commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 inbox', json_array_length(my_msgs()); commit;
-- S2가 S1의 안내를 읽음 처리 시도 → 안 돼야
begin; set local role authenticated; select _as(:'S2'); select msg_read(array[1,2,3,4,5]::bigint[]); commit;
select 'read after S2', count(*) filter (where read_at is not null) from student_msgs;
begin; set local role authenticated; select _as(:'S1'); select msg_read(array[(my_msgs()->0->>'id')::bigint]); commit;
select 'read after S1', count(*) filter (where read_at is not null) from student_msgs;
begin; set local role authenticated; select _as(:'TA'); select 'sent', json_array_length(msg_sent()), msg_sent()->0->>'body', json_array_length(msg_sent()->0->'rcpt'); commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB sent', json_array_length(msg_sent()); commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 sent', json_array_length(msg_sent()); commit;
-- 거두기: TB는 못 함, TA는 한 학생만
select batch as "B1" from student_msgs limit 1 \gset
begin; set local role authenticated; select _as(:'TB'); select 'TB withdraw', msg_withdraw(:'B1', null); commit;
begin; set local role authenticated; select _as(:'TA'); select 'TA withdraw one', msg_withdraw((msg_sent()->0->>'batch'), '22222222-2222-2222-2222-222222222222'); commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 inbox after', json_array_length(my_msgs()); commit;
-- 알림 대상
insert into push_subs values ('https://p/1','00000000-0000-0000-0000-0000000000a1','k','a'),('https://p/2','00000000-0000-0000-0000-0000000000b2','k','a') on conflict do nothing;
begin; set local role authenticated; select _as(:'TA'); select 'targets', string_agg(endpoint, ',') from push_targets_students(array['11111111-1111-1111-1111-111111111111']::uuid[]); commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB targets', count(*) from push_targets_students(array['11111111-1111-1111-1111-111111111111']::uuid[]); commit;
begin; set local role authenticated; select _as(:'S1'); select 'S targets', count(*) from push_targets_students(array['22222222-2222-2222-2222-222222222222']::uuid[]); commit;
-- 글 주인에게
begin; set local role authenticated; select _as(:'TA'); insert into docs(col,id,data) values ('rooms','r1','{"title":"x"}') on conflict do nothing; commit;
begin; set local role authenticated; select _as(:'S2'); insert into docs(col,id,data,tid) values ('posts','p2','{"roomId":"r1","author":"11005 나다은"}', '00000000-0000-0000-0000-00000000000a'); commit;
select 'p2 owner', owner from docs where id='p2';
begin; set local role authenticated; select _as(:'TA'); select 'post targets', string_agg(endpoint, ',') from push_targets_post('p2'); commit;
begin; set local role authenticated; select _as(:'TB'); select 'TB post targets', count(*) from push_targets_post('p2'); commit;
-- 막힌 선생님
update teachers set blocked = true where email='a@x.kr';
begin; set local role authenticated; select _as(:'S1'); select 'S1 inbox blocked', json_array_length(my_msgs()); commit;
update teachers set blocked = false where email='a@x.kr';
