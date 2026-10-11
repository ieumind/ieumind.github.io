\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
\set S2 '{"sub":"00000000-0000-0000-0000-0000000000b2","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','김가온','AAA111'),('22222222-2222-2222-2222-222222222222','11005','나다은','AAA222');
insert into docs(col,id,data) values ('courses','c1','{"title":"통합과학","members":["11111111-1111-1111-1111-111111111111"]}'),('courses','c0','{"title":"예전 과목"}'),
 ('rooms','r1','{"title":"c1활동","courseId":"c1","reveal":"after"}'),('rooms','r0','{"title":"과목없음"}'),('rooms','rc0','{"title":"예전과목활동","courseId":"c0"}');
commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 claim', claim_student('10301','김가온','AAA111');
insert into docs(col,id,data) values ('posts','p1','{"roomId":"r1","author":"10301 김가온","status":"submitted"}');
insert into docs(col,id,data) values ('replies','h1','{"roomId":"r1","postId":"p1","author":"10301 김가온","kind":"heart","on":true}');
commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 claim', claim_student('11005','나다은','AAA222'); commit;
begin; set local role authenticated; select _as(:'S1');
select 'S1 sees', string_agg(col||':'||id, ',' order by col,id) from docs; commit;
begin; set local role authenticated; select _as(:'S2');
select 'S2 sees', string_agg(col||':'||id, ',' order by col,id) from docs;
commit;
begin; set local role authenticated; select _as(:'S2');
insert into docs(col,id,data) values ('posts','p2','{"roomId":"r1","author":"11005 나다은"}');
rollback;
begin; set local role authenticated; select _as(:'S2');
insert into docs(col,id,data) values ('posts','p3','{"roomId":"r0","author":"11005 나다은"}'); select 'S2 post in r0 ok'; commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 chat r1', chat_begin('r1'); rollback;
-- teacher adds S2 to c1
begin; set local role authenticated; select _as(:'TA');
update docs set data = jsonb_set(data,'{members}','["11111111-1111-1111-1111-111111111111","22222222-2222-2222-2222-222222222222"]') where col='courses' and id='c1'; commit;
begin; set local role authenticated; select _as(:'S2'); select 'S2 sees after add', string_agg(col||':'||id, ',' order by col,id) from docs; commit;
begin; set local role authenticated; select _as(:'TA'); select 'T sees', count(*) from docs; commit;
