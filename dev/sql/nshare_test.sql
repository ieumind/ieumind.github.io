\set QUIET 1
\pset tuples_only on
insert into teachers values ('a@x.kr') on conflict do nothing;
create or replace function public._as(claims jsonb) returns void language plpgsql as $$ begin perform set_config('request.jwt.claims', claims::text, true); end $$;
grant execute on function public._as(jsonb) to authenticated;
\set TA '{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@x.kr","is_anonymous":false}'
\set S1 '{"sub":"00000000-0000-0000-0000-0000000000a1","is_anonymous":true}'
\set S2 '{"sub":"00000000-0000-0000-0000-0000000000b2","is_anonymous":true}'
begin; set local role authenticated; select _as(:'TA');
insert into students(id,number,name,code) values ('11111111-1111-1111-1111-111111111111','10301','가','AAA111'),('22222222-2222-2222-2222-222222222222','10401','나','AAA222');
insert into docs(col,id,data) values ('rooms','rn','{"title":"학습 나눔","template":"notes","reveal":"teacher"}'); commit;
begin; set local role authenticated; select _as(:'S1'); select claim_student('10301','가','AAA111'); commit;
begin; set local role authenticated; select _as(:'S2'); select claim_student('10401','나','AAA222'); commit;
\set F1 'rn/11111111-1111-1111-1111-111111111111/a.jpg'
begin; set local role authenticated; select _as(:'S2'); select 'S2 read S1 (teacher only)', note_can_read(:'F1') or note_can_read_shared(:'F1'), 'del(note_can_read)', note_can_read(:'F1'); commit;
update docs set data = jsonb_set(data, '{reveal}', '"after"') where id='rn';
begin; set local role authenticated; select _as(:'S2'); select 'S2 read S1 (shared)', note_can_read(:'F1') or note_can_read_shared(:'F1'), 'del(note_can_read)', note_can_read(:'F1'); commit;
begin; set local role authenticated; select _as(:'S1'); select 'S1 own', note_can_read(:'F1') or note_can_read_shared(:'F1'), 'del(note_can_read)', note_can_read(:'F1'); commit;
begin; set local role authenticated; select _as(:'TA'); select 'teacher', note_can_read(:'F1') or note_can_read_shared(:'F1'), 'del(note_can_read)', note_can_read(:'F1'); commit;
select 'policies', policyname, cmd from pg_policies where policyname like 'notes_%' order by 2;
