\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
\set S2 '{"sub":"00000000-0000-0000-0000-0000000000b2","is_anonymous":true}'
\set S3 '{"sub":"00000000-0000-0000-0000-0000000000c3","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','가','AAA111'),('22222222-2222-2222-2222-222222222222','10401','나','AAA222'),('33333333-3333-3333-3333-333333333333','10501','다','AAA333');
insert into docs(col,id,data) values ('courses','c1','{"title":"사회","members":["11111111-1111-1111-1111-111111111111","22222222-2222-2222-2222-222222222222"],"groups":[{"id":"g3","name":"1-3","members":["11111111-1111-1111-1111-111111111111"]},{"id":"g4","name":"1-4","members":["22222222-2222-2222-2222-222222222222"]}]}'),
  ('rooms','r1','{"title":"그룹활동","courseId":"c1","status":"open","assign":{"g3":{"status":"open"},"g4":{"status":"ready","startAt":1}}}'),('rooms','r0','{"title":"과목없음","status":"open"}');
commit;
begin; set local role authenticated; select _as(:'S1'); select claim_student('10301','가','AAA111'); select push_save('https://push/s1','k1','a1'); commit;
begin; set local role authenticated; select _as(:'S2'); select claim_student('10401','나','AAA222'); select push_save('https://push/s2','k2','a2'); commit;
begin; set local role authenticated; select _as(:'S3'); select claim_student('10501','다','AAA333'); select push_save('https://push/s3','k3','a3'); commit;
begin; set local role authenticated; select _as(:'TA');
select 'course all', string_agg(endpoint, ',' order by endpoint) from push_targets_for('c1');
select 'group g3', string_agg(endpoint, ',' order by endpoint) from push_targets_groups('c1', array['g3']);
select 'group g3+g4', string_agg(endpoint, ',' order by endpoint) from push_targets_groups('c1', array['g3','g4']);
select 'no course', count(*) from push_targets_for('nope');
select 'sched r0 (no course)', push_schedule('r0','',(extract(epoch from now())*1000 + 600000)::bigint,'t','b');
select 'sched r1 g4', push_schedule('r1','g4',(extract(epoch from now())*1000 + 600000)::bigint,'🆕 새 활동','사회 · 그룹활동');
select 'sched r1 past', push_schedule('r1','g3',(extract(epoch from now())*1000 - 1000)::bigint,'t','b');
commit;
begin; set local role authenticated; select _as(:'S1'); select 'student sched', push_schedule('r1','g4',(extract(epoch from now())*1000 + 600000)::bigint,'t','b'); select 'student read jobs'; select count(*) from push_jobs; rollback;
begin; set local role authenticated; select _as(:'TA'); select 'teacher take'; select push_due_take(10); rollback;
-- 시각이 된 것으로 바꾸고 서버 역할로 꺼내기
update push_jobs set send_at = now() - interval '1 minute';
begin; set local role service_role; select 'due', push_due_take(10); select 'due again', push_due_take(10); commit;
-- 마감한 활동은 보내지 않음
update push_jobs set sent_at = null; update docs set data = jsonb_set(data,'{status}','"closed"') where col='rooms' and id='r1';
begin; set local role service_role; select 'closed room', push_due_take(10); commit;
