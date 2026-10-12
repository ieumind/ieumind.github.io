\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
insert into teachers values ('b@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set TB '{"sub":"00000000-0000-0000-0000-00000000000b","email":"b@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','김가온','AAA111');
insert into docs(col,id,data) values ('courses','ca','{"title":"사회","members":["11111111-1111-1111-1111-111111111111"]}'),('rooms','ra','{"title":"A활동","courseId":"ca"}'); commit;
begin; set local role authenticated; select _as(:'TB');
insert into students(id,school,number,name,code) values ('22222222-2222-2222-2222-222222222222','한백고','10301','김가온','BBB222');
insert into docs(col,id,data) values ('courses','cb','{"title":"과학","members":["22222222-2222-2222-2222-222222222222"]}'),('rooms','rb','{"title":"B활동","courseId":"cb"}'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'claim A', claim_student('10301','김가온','AAA111'); select 'claim B', claim_student('10301','김가온','BBB222'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'my_students', my_students();
select 'sees', string_agg(col||':'||id, ',' order by col,id) from docs;
insert into docs(col,id,data) values ('posts','pa','{"roomId":"ra","author":"10301 김가온"}'); select 'post A ok';
insert into docs(col,id,data) values ('posts','pb','{"roomId":"rb","author":"한백고 10301 김가온"}'); select 'post B ok';
commit;
begin; set local role authenticated; select _as(:'S1');
insert into docs(col,id,data) values ('posts','pbad','{"roomId":"rb","author":"10301 김가온"}'); rollback;
