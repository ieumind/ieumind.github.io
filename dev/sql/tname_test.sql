\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false,"user_metadata":{"full_name":"Google Name"}}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA'); select teacher_checkin(); commit;
select 'after checkin', name, name_set from teachers where email='a@x.kr';
begin; set local role authenticated; select _as(:'TA'); select 'set', teacher_set_name('  이태형   선생 '); select teacher_checkin(); commit;
select 'after set+checkin', name, name_set from teachers where email='a@x.kr';
begin; set local role authenticated; select _as(:'TA'); select 'empty', teacher_set_name('  '); commit;
begin; set local role authenticated; select _as(:'S1'); select 'student', teacher_set_name('해커'); commit;
select 'final', name from teachers where email='a@x.kr';
