-- =====================================================================
-- 생각이음 · Supabase 설정 (SQL Editor에 통째로 붙여 넣고 Run)
-- 교사마다 자기 활동·학생 명단·학생 글만 봅니다 (교사끼리 서로 볼 수 없음).
-- 새 프로젝트에 처음 한 번 실행하세요. 다시 실행해도 괜찮아요.
-- =====================================================================

-- 1) 앱 데이터: 활동(rooms)·학생 글(posts)·댓글(replies) 등을 한 표에 문서처럼 저장
--    tid = 이 문서의 주인 교사(구글 로그인 id). 학생 글은 그 활동을 만든 교사의 것
create table if not exists public.docs (
  col        text not null,
  id         text not null,
  tid        uuid not null,              -- 서버가 채운다
  data       jsonb not null default '{}'::jsonb,
  owner      uuid,                       -- 학생이 쓴 문서의 주인(학생 id). 서버가 채운다
  room_id    text,                       -- data.roomId. 서버가 채운다
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (col, id, tid)
);
create index if not exists docs_tid_idx  on public.docs (tid, col);
create index if not exists docs_room_idx on public.docs (col, room_id);
create index if not exists docs_id_idx   on public.docs (id);

-- 2) 교사 명단: 여기에 들어 있는 구글 계정만 교사 화면을 쓴다
create table if not exists public.teachers (
  email text primary key
);

-- 3) 학생 명단과 개인 코드 (교사마다 따로. 학생에게는 보이지 않는다)
create table if not exists public.students (
  id         uuid primary key default gen_random_uuid(),
  tid        uuid not null default auth.uid(),   -- 이 명단을 만든 교사
  number     text not null,
  name       text not null,
  code       text not null unique,
  created_at timestamptz not null default now(),
  unique (tid, number, name)
);

-- 4) 이 기기(익명 세션)가 어느 선생님 반의 어떤 학생인지 (선생님마다 한 줄)
create table if not exists public.student_sessions (
  uid        uuid not null,
  tid        uuid not null,
  student_id uuid not null references public.students(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (uid, tid)
);

alter table public.docs             enable row level security;
alter table public.teachers         enable row level security;
alter table public.students         enable row level security;
alter table public.student_sessions enable row level security;

grant select, insert, update, delete on public.docs     to authenticated;
grant select, insert, update, delete on public.students to authenticated;

-- ---------------------------------------------------------------------
-- 권한 판단 함수
-- ---------------------------------------------------------------------
create or replace function public.is_teacher() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) = false
     and exists (select 1 from public.teachers t
                 where lower(t.email) = lower(coalesce(auth.jwt() ->> 'email', '')));
$$;

-- 이 기기가 그 선생님 반의 학생으로 확인되었나
create or replace function public.is_my_teacher(p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.student_sessions where uid = auth.uid() and tid = p_tid);
$$;

create or replace function public.my_student(p_tid uuid) returns uuid
language sql stable security definer set search_path = public as $$
  select student_id from public.student_sessions where uid = auth.uid() and tid = p_tid;
$$;

create or replace function public.my_student_name(p_tid uuid) returns text
language sql stable security definer set search_path = public as $$
  select s.number || ' ' || s.name
    from public.student_sessions ss join public.students s on s.id = ss.student_id
   where ss.uid = auth.uid() and ss.tid = p_tid;
$$;

-- 학생 글을 친구가 볼 수 있는 활동인가 (‘선생님만 보기’ 활동이면 안 됨)
create or replace function public.room_open_to_peers(p_room text, p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select r.data ->> 'reveal' from public.docs r
                    where r.col = 'rooms' and r.id = p_room and r.tid = p_tid), 'after') <> 'teacher';
$$;

-- 지금 접속한 사람이 누구인지. p_ref = 학생이 들어온 링크의 활동 id 또는 수업 id
-- 그 활동의 선생님 반 학생으로 확인되지 않았으면 student_name이 비어 있다 → 앱이 코드를 묻는다
create or replace function public.whoami(p_ref text default null) returns json
language plpgsql stable security definer set search_path = public as $$
declare t uuid; nm text;
begin
  if p_ref is not null and p_ref <> '' then
    select d.tid into t from public.docs d where d.id = p_ref and d.col in ('rooms', 'courses') limit 1;
  end if;
  if t is not null then
    nm := public.my_student_name(t);
  else
    select s.number || ' ' || s.name into nm
      from public.student_sessions ss join public.students s on s.id = ss.student_id
     where ss.uid = auth.uid() order by ss.created_at desc limit 1;
  end if;
  return json_build_object(
    'teacher', public.is_teacher(),
    'email', case when coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) then null else auth.jwt() ->> 'email' end,
    'student_name', nm);
end $$;

-- 학생: 학번·이름·코드가 맞으면 이 기기를 그 선생님 반의 그 학생으로 연결한다
create or replace function public.claim_student(p_number text, p_name text, p_code text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare s public.students;
begin
  if auth.uid() is null then return null; end if;
  select * into s from public.students
   where number = trim(p_number)
     and replace(name, ' ', '') = replace(trim(p_name), ' ', '')
     and upper(code) = upper(trim(p_code));
  if not found then
    perform pg_sleep(1);             -- 코드 맞히기 시도를 느리게
    return null;
  end if;
  insert into public.student_sessions (uid, tid, student_id) values (auth.uid(), s.tid, s.id)
  on conflict (uid, tid) do update set student_id = excluded.student_id, created_at = now();
  return json_build_object('id', s.id, 'name', s.number || ' ' || s.name);
end $$;

-- 문서 일부만 고치기 (권한 검사는 표의 규칙을 그대로 따른다)
create or replace function public.doc_merge(p_col text, p_id text, p_patch jsonb) returns void
language sql volatile security invoker set search_path = public as $$
  update public.docs set data = data || p_patch where col = p_col and id = p_id;
$$;

revoke all on function public.claim_student(text, text, text) from public;
grant execute on function public.claim_student(text, text, text) to authenticated;
grant execute on function public.whoami(text) to authenticated;
grant execute on function public.doc_merge(text, text, jsonb) to authenticated;
grant execute on function public.is_teacher(), public.is_my_teacher(uuid), public.my_student(uuid),
  public.my_student_name(uuid), public.room_open_to_peers(text, uuid) to authenticated;

-- 저장할 때 서버가 주인 교사·주인 학생·활동·시각을 채운다 (남의 것으로 꾸밀 수 없게)
create or replace function public.docs_stamp() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.room_id := new.data ->> 'roomId';
  new.updated_at := now();
  if tg_op = 'INSERT' then
    if public.is_teacher() then
      new.tid := auth.uid();
      new.owner := null;
    else                                            -- 학생 글: 그 활동을 만든 교사의 것
      new.tid := (select r.tid from public.docs r where r.col = 'rooms' and r.id = new.room_id limit 1);
      new.owner := public.my_student(new.tid);
    end if;
    new.created_at := now();
  else
    new.tid := old.tid;
    new.owner := old.owner;
    new.created_at := old.created_at;
  end if;
  return new;
end $$;
drop trigger if exists docs_stamp on public.docs;
create trigger docs_stamp before insert or update on public.docs
  for each row execute function public.docs_stamp();

-- 로그인 전(anon)에는 어떤 함수도 부를 수 없게, 트리거 함수는 직접 부를 수 없게
revoke execute on function public.claim_student(text,text,text), public.docs_stamp(), public.is_my_teacher(uuid), public.is_teacher(),
  public.my_student(uuid), public.my_student_name(uuid), public.room_open_to_peers(text,uuid), public.whoami(text), public.doc_merge(text,text,jsonb) from public, anon;
revoke execute on function public.docs_stamp() from authenticated;

-- ---------------------------------------------------------------------
-- 규칙 (Row Level Security)
-- 교사: 자기(tid) 문서만. 학생: 코드로 확인된 선생님 반의 문서만.
-- ---------------------------------------------------------------------
drop policy if exists docs_read   on public.docs;
drop policy if exists docs_insert on public.docs;
drop policy if exists docs_update on public.docs;
drop policy if exists docs_delete on public.docs;

create policy docs_read on public.docs for select to authenticated using (
  (public.is_teacher() and tid = auth.uid())
  or (public.is_my_teacher(tid) and (
        col in ('rooms', 'courses', 'config', 'treplies')
     or (col = 'posts' and (owner = public.my_student(tid) or public.room_open_to_peers(room_id, tid)))
     or col = 'replies'))
);

create policy docs_insert on public.docs for insert to authenticated with check (
  (public.is_teacher() and tid = auth.uid())
  or (col in ('posts', 'replies')
      and owner is not null
      and owner = public.my_student(tid)
      and data ->> 'author' = public.my_student_name(tid)
      and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
);

create policy docs_update on public.docs for update to authenticated
  using ((public.is_teacher() and tid = auth.uid())
         or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid)))
  with check (
    (public.is_teacher() and tid = auth.uid())
    or (col in ('posts', 'replies')
        and owner is not null
        and owner = public.my_student(tid)
        and data ->> 'author' = public.my_student_name(tid)
        and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
  );

create policy docs_delete on public.docs for delete to authenticated
  using (public.is_teacher() and tid = auth.uid());

-- 학생 명단·코드: 그 명단을 만든 교사만
drop policy if exists students_teacher on public.students;
create policy students_teacher on public.students for all to authenticated
  using (public.is_teacher() and tid = auth.uid())
  with check (public.is_teacher() and tid = auth.uid());
-- teachers, student_sessions: 정책 없음 = 앱에서 직접 읽고 쓸 수 없음 (함수만 사용)

-- 실시간 반영 켜기
do $$ begin
  begin
    alter publication supabase_realtime add table public.docs;
  exception when duplicate_object then null; when undefined_object then null;
  end;
end $$;

-- ---------------------------------------------------------------------
-- 📸 오늘의 필기: 사진 보관함(Storage) ‘notes’
-- 경로 = {활동id}/{학생id}/{파일}. 학생은 자기 폴더만 올리고·보고·지우고, 선생님은 자기 활동의 사진만 본다
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('notes', 'notes', false, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do nothing;

create or replace function public.room_tid(p_room text) returns uuid
language sql stable security definer set search_path = public as $$
  select tid from public.docs where col = 'rooms' and id = p_room limit 1;
$$;
create or replace function public.my_student_id(p_room text) returns uuid
language sql stable security definer set search_path = public as $$
  select public.my_student(public.room_tid(p_room));
$$;
create or replace function public.note_can_read(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select case when (storage.foldername(p_name))[1] is null then false else
    (public.is_teacher() and public.room_tid((storage.foldername(p_name))[1]) = auth.uid())
    or coalesce((storage.foldername(p_name))[2] = public.my_student(public.room_tid((storage.foldername(p_name))[1]))::text, false)
  end;
$$;
create or replace function public.note_can_write(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((storage.foldername(p_name))[2] = public.my_student(public.room_tid((storage.foldername(p_name))[1]))::text, false);
$$;
revoke execute on function public.room_tid(text), public.my_student_id(text), public.note_can_read(text), public.note_can_write(text) from public, anon;
grant execute on function public.room_tid(text), public.my_student_id(text), public.note_can_read(text), public.note_can_write(text) to authenticated;

drop policy if exists notes_read on storage.objects;
drop policy if exists notes_insert on storage.objects;
drop policy if exists notes_delete on storage.objects;
create policy notes_read on storage.objects for select to authenticated
  using (bucket_id = 'notes' and public.note_can_read(name));
create policy notes_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'notes' and public.note_can_write(name));
create policy notes_delete on storage.objects for delete to authenticated
  using (bucket_id = 'notes' and public.note_can_read(name));

-- ---------------------------------------------------------------------
-- 교사 가입: 구글로 로그인하면 누구나 교사(자기 공간만). 관리자는 교사 목록을 보고 계정을 막을 수 있다
-- ---------------------------------------------------------------------
alter table public.teachers add column if not exists uid uuid;
alter table public.teachers add column if not exists name text;
alter table public.teachers add column if not exists first_at timestamptz default now();
alter table public.teachers add column if not exists last_at timestamptz;
alter table public.teachers add column if not exists blocked boolean not null default false;
alter table public.teachers add column if not exists admin boolean not null default false;
create index if not exists teachers_uid_idx on public.teachers (uid);

create or replace function public.is_teacher() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) = false
     and coalesce(auth.jwt() ->> 'email', '') <> ''
     and not exists (select 1 from public.teachers t
                      where t.blocked and (t.uid = auth.uid() or lower(t.email) = lower(auth.jwt() ->> 'email')));
$$;
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select public.is_teacher() and exists (select 1 from public.teachers t
                                          where t.admin and lower(t.email) = lower(coalesce(auth.jwt() ->> 'email', '')));
$$;
create or replace function public.tid_active(p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select not exists (select 1 from public.teachers t where t.uid = p_tid and t.blocked);
$$;
create or replace function public.teacher_checkin() returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) or coalesce(auth.jwt() ->> 'email', '') = '' then return; end if;
  insert into public.teachers (email, uid, name, first_at, last_at)
  values (lower(auth.jwt() ->> 'email'), auth.uid(),
          coalesce(auth.jwt() -> 'user_metadata' ->> 'full_name', auth.jwt() -> 'user_metadata' ->> 'name'), now(), now())
  on conflict (email) do update set uid = excluded.uid, name = coalesce(excluded.name, public.teachers.name), last_at = now();
end $$;
create or replace function public.whoami(p_ref text default null) returns json
language plpgsql stable security definer set search_path = public as $$
declare t uuid; nm text; anon boolean := coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false);
begin
  if p_ref is not null and p_ref <> '' then
    select d.tid into t from public.docs d where d.id = p_ref and d.col in ('rooms', 'courses') limit 1;
  end if;
  if t is not null then
    nm := public.my_student_name(t);
  else
    select s.number || ' ' || s.name into nm
      from public.student_sessions ss join public.students s on s.id = ss.student_id
     where ss.uid = auth.uid() order by ss.created_at desc limit 1;
  end if;
  return json_build_object(
    'teacher', public.is_teacher(),
    'admin', public.is_admin(),
    'blocked', (not anon) and exists (select 1 from public.teachers x where x.blocked and lower(x.email) = lower(coalesce(auth.jwt() ->> 'email', ''))),
    'email', case when anon then null else auth.jwt() ->> 'email' end,
    'student_name', nm);
end $$;
create or replace function public.admin_list_teachers()
returns table(email text, name text, first_at timestamptz, last_at timestamptz, blocked boolean, admin boolean, rooms bigint, students bigint, photos bigint, photo_mb numeric)
language sql stable security definer set search_path = public as $$
  select t.email, t.name, t.first_at, t.last_at, t.blocked, t.admin,
    (select count(*) from public.docs d where d.col = 'rooms' and d.tid = t.uid),
    (select count(*) from public.students s where s.tid = t.uid),
    (select count(*) from storage.objects o where o.bucket_id = 'notes' and public.room_tid((storage.foldername(o.name))[1]) = t.uid),
    (select round(coalesce(sum((o.metadata ->> 'size')::numeric), 0) / 1048576, 1) from storage.objects o
      where o.bucket_id = 'notes' and public.room_tid((storage.foldername(o.name))[1]) = t.uid)
  from public.teachers t
  where public.is_admin()
  order by t.last_at desc nulls last;
$$;
create or replace function public.admin_set_blocked(p_email text, p_blocked boolean) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception '관리자만 할 수 있어요'; end if;
  if lower(p_email) = lower(coalesce(auth.jwt() ->> 'email', '')) then raise exception '내 계정은 막을 수 없어요'; end if;
  update public.teachers set blocked = coalesce(p_blocked, false) where lower(email) = lower(p_email) and not admin;
end $$;
create or replace function public.note_can_write(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((storage.foldername(p_name))[2] = public.my_student(public.room_tid((storage.foldername(p_name))[1]))::text
                  and public.tid_active(public.room_tid((storage.foldername(p_name))[1])), false);
$$;
revoke execute on function public.is_admin(), public.tid_active(uuid), public.teacher_checkin(), public.admin_list_teachers(), public.admin_set_blocked(text, boolean) from public, anon;
grant execute on function public.is_admin(), public.tid_active(uuid), public.teacher_checkin(), public.admin_list_teachers(), public.admin_set_blocked(text, boolean), public.whoami(text) to authenticated;

-- 막힌 교사의 활동: 학생도 보거나 새로 쓸 수 없다
alter policy docs_read on public.docs using (
  (public.is_teacher() and tid = auth.uid())
  or (public.is_my_teacher(tid) and public.tid_active(tid) and (
        col in ('rooms', 'courses', 'config', 'treplies')
     or (col = 'posts' and (owner = public.my_student(tid) or public.room_open_to_peers(room_id, tid)))
     or col = 'replies'))
);
alter policy docs_insert on public.docs with check (
  (public.is_teacher() and tid = auth.uid())
  or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid)
      and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
);
alter policy docs_update on public.docs
  using ((public.is_teacher() and tid = auth.uid())
         or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid)))
  with check ((public.is_teacher() and tid = auth.uid())
    or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid)
        and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class')));

-- ---------------------------------------------------------------------
-- 학교: 공동교육과정처럼 여러 학교 학생이 한 수업에 있을 때 (같은 학번·이름도 학교가 다르면 다른 학생)
-- 학생 이름표 = ‘학교 학번 이름’ (학교가 없으면 ‘학번 이름’)
-- ---------------------------------------------------------------------
alter table public.students add column if not exists school text not null default '';
create unique index if not exists students_tid_school_number_name on public.students (tid, school, number, name);
alter table public.students drop constraint if exists students_tid_number_name_key;

create or replace function public.my_student_name(p_tid uuid) returns text
language sql stable security definer set search_path = public as $$
  select case when s.school <> '' then s.school || ' ' else '' end || s.number || ' ' || s.name
    from public.student_sessions ss join public.students s on s.id = ss.student_id
   where ss.uid = auth.uid() and ss.tid = p_tid;
$$;
create or replace function public.claim_student(p_number text, p_name text, p_code text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare s public.students;
begin
  if auth.uid() is null then return null; end if;
  select * into s from public.students
   where number = trim(p_number)
     and replace(name, ' ', '') = replace(trim(p_name), ' ', '')
     and upper(code) = upper(trim(p_code));
  if not found then
    perform pg_sleep(1);
    return null;
  end if;
  insert into public.student_sessions (uid, tid, student_id) values (auth.uid(), s.tid, s.id)
  on conflict (uid, tid) do update set student_id = excluded.student_id, created_at = now();
  return json_build_object('id', s.id, 'name', case when s.school <> '' then s.school || ' ' else '' end || s.number || ' ' || s.name);
end $$;
create or replace function public.whoami(p_ref text default null) returns json
language plpgsql stable security definer set search_path = public as $$
declare t uuid; nm text; anon boolean := coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false);
begin
  if p_ref is not null and p_ref <> '' then
    select d.tid into t from public.docs d where d.id = p_ref and d.col in ('rooms', 'courses') limit 1;
  end if;
  if t is not null then
    nm := public.my_student_name(t);
  else
    select case when s.school <> '' then s.school || ' ' else '' end || s.number || ' ' || s.name into nm
      from public.student_sessions ss join public.students s on s.id = ss.student_id
     where ss.uid = auth.uid() order by ss.created_at desc limit 1;
  end if;
  return json_build_object(
    'teacher', public.is_teacher(),
    'admin', public.is_admin(),
    'blocked', (not anon) and exists (select 1 from public.teachers x where x.blocked and lower(x.email) = lower(coalesce(auth.jwt() ->> 'email', ''))),
    'email', case when anon then null else auth.jwt() ->> 'email' end,
    'student_name', nm);
end $$;

-- ---------------------------------------------------------------------
-- 🎭 가상 인물 대화: AI에 묻기 전에 서버가 확인 (활동·학생·마감·질문 수). 중계 프로그램은 supabase/functions/chat
-- ---------------------------------------------------------------------
create table if not exists public.chat_usage (
  room_id text not null, who text not null, n int not null default 0, updated_at timestamptz not null default now(),
  primary key (room_id, who));
alter table public.chat_usage enable row level security;
create or replace function public.chat_begin(p_room text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare d public.docs; v_sid uuid; v_who text; v_lim int; v_used int; v_st text; p jsonb;
begin
  select * into d from public.docs where col = 'rooms' and id = p_room limit 1;
  if not found or coalesce(d.data ->> 'template', '') <> 'chat' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  p := coalesce(d.data -> 'persona', '{}'::jsonb);
  if public.is_teacher() and d.tid = auth.uid() then
    v_who := 'T:' || auth.uid(); v_lim := 200;
  else
    v_sid := public.my_student(d.tid);
    if v_sid is null or not public.tid_active(d.tid) or not public.room_for_me(p_room, d.tid) then return json_build_object('ok', false, 'reason', 'denied'); end if;
    v_st := coalesce(d.data ->> 'status', 'open');
    if v_st in ('draft', 'archived', 'closed') or d.data ->> 'open' = 'false'
       or (jsonb_typeof(d.data -> 'dueAt') = 'number' and (d.data ->> 'dueAt')::numeric <= extract(epoch from now()) * 1000) then
      return json_build_object('ok', false, 'reason', 'closed'); end if;
    v_who := v_sid::text;
    v_lim := least(30, greatest(1, coalesce(nullif(p ->> 'maxTurns', '')::int, 8))) + 2;
  end if;
  insert into public.chat_usage (room_id, who, n) values (p_room, v_who, 0) on conflict do nothing;
  select n into v_used from public.chat_usage where room_id = p_room and who = v_who for update;
  if v_used >= v_lim then return json_build_object('ok', false, 'reason', 'limit'); end if;
  update public.chat_usage set n = n + 1, updated_at = now() where room_id = p_room and who = v_who;
  return json_build_object('ok', true, 'name', coalesce(nullif(p ->> 'name', ''), '인물'), 'about', coalesce(p ->> 'about', ''), 'style', coalesce(p ->> 'style', 'persona'),
    'prompt', coalesce(d.data ->> 'prompt', ''), 'context', left(coalesce(d.data ->> 'context', ''), 6000), 'facts', left(coalesce(p ->> 'facts', ''), 4000),
    'remaining', v_lim - v_used - 1);
end $$;
revoke execute on function public.chat_begin(text) from public, anon;
grant execute on function public.chat_begin(text) to authenticated;

-- ---------------------------------------------------------------------
-- 🔔 학생 앱 알림 (Web Push): 공지·새 활동을 선생님 반 학생 기기로 보낸다. 보내는 프로그램은 supabase/functions/notify
--   push_subs : 학생 기기가 알림을 받겠다고 한 주소 (본인만 저장·삭제, 선생님은 자기 반 학생 주소만 받아 감)
--   notify_log: 한 선생님이 1시간에 30번까지만 보내도록 기록
--   app_secrets: VAPID 키 (서버 프로그램만 읽음) — 아래 README의 ‘알림 키 만들기’ 참고
-- ---------------------------------------------------------------------
create table if not exists public.push_subs (
  endpoint text primary key, uid uuid not null, p256dh text not null, auth text not null, created_at timestamptz not null default now());
create index if not exists push_subs_uid_idx on public.push_subs (uid);
create table if not exists public.notify_log (tid uuid not null, at timestamptz not null default now());
create table if not exists public.app_secrets (k text primary key, v text not null);
alter table public.push_subs enable row level security;
alter table public.notify_log enable row level security;
alter table public.app_secrets enable row level security;
revoke all on public.app_secrets from anon, authenticated;

create or replace function public.push_save(p_endpoint text, p_p256dh text, p_auth text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or coalesce(p_endpoint, '') !~ '^https://' or length(p_endpoint) > 1000 then return; end if;
  insert into public.push_subs (endpoint, uid, p256dh, auth) values (p_endpoint, auth.uid(), left(p_p256dh, 200), left(p_auth, 100))
  on conflict (endpoint) do update set uid = excluded.uid, p256dh = excluded.p256dh, auth = excluded.auth, created_at = now();
end $$;
create or replace function public.push_forget(p_endpoint text) returns void
language sql security definer set search_path = public as $$
  delete from public.push_subs where endpoint = p_endpoint and uid = auth.uid();
$$;
create or replace function public.push_targets() returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  if (select count(*) from public.notify_log where tid = auth.uid() and at > now() - interval '1 hour') >= 30 then return; end if;
  insert into public.notify_log (tid) values (auth.uid());
  return query select s.endpoint, s.p256dh, s.auth from public.push_subs s
    where s.uid in (select ss.uid from public.student_sessions ss where ss.tid = auth.uid());
end $$;
create or replace function public.push_drop(p_endpoint text) returns void
language sql security definer set search_path = public as $$
  delete from public.push_subs s where s.endpoint = p_endpoint and public.is_teacher()
    and s.uid in (select ss.uid from public.student_sessions ss where ss.tid = auth.uid());
$$;

-- ---------------------------------------------------------------------
-- 💬 오류·건의하기: 누구나 보내고(하루 10번), 관리자만 읽는다
-- ---------------------------------------------------------------------
create table if not exists public.feedback (
  id bigint generated always as identity primary key, uid uuid, who text, kind text, body text not null, page text,
  done boolean not null default false, created_at timestamptz not null default now());
alter table public.feedback enable row level security;
create or replace function public.feedback_send(p_kind text, p_body text, p_page text) returns json
language plpgsql security definer set search_path = public as $$
declare w json; nm text;
begin
  if auth.uid() is null or length(trim(coalesce(p_body, ''))) < 2 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  if (select count(*) from public.feedback where uid = auth.uid() and created_at > now() - interval '1 day') >= 10 then
    return json_build_object('ok', false, 'reason', 'limit'); end if;
  w := public.whoami(null);
  nm := coalesce(w ->> 'student_name', case when (w ->> 'teacher')::boolean then '교사 ' || coalesce(w ->> 'email', '') end, '이름 없음');
  insert into public.feedback (uid, who, kind, body, page)
  values (auth.uid(), nm, case when p_kind in ('오류', '건의', '기타') then p_kind else '기타' end, left(trim(p_body), 2000), left(coalesce(p_page, ''), 200));
  return json_build_object('ok', true);
end $$;
create or replace function public.admin_list_feedback() returns table(id bigint, who text, kind text, body text, page text, done boolean, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select f.id, f.who, f.kind, f.body, f.page, f.done, f.created_at from public.feedback f where public.is_admin() order by f.done, f.created_at desc limit 200;
$$;
create or replace function public.admin_feedback_done(p_id bigint, p_done boolean) returns void
language sql security definer set search_path = public as $$
  update public.feedback set done = coalesce(p_done, true) where id = p_id and public.is_admin();
$$;
revoke execute on function public.push_save(text,text,text), public.push_forget(text), public.push_targets(), public.push_drop(text),
  public.feedback_send(text,text,text), public.admin_list_feedback(), public.admin_feedback_done(bigint,boolean) from public, anon;
grant execute on function public.push_save(text,text,text), public.push_forget(text), public.push_targets(), public.push_drop(text),
  public.feedback_send(text,text,text), public.admin_list_feedback(), public.admin_feedback_done(bigint,boolean) to authenticated;

-- ---------------------------------------------------------------------
-- 🪄 AI 질문 추천: 선생님이 구글 AI 스튜디오에서 받은 Gemini API 키를 선생님 계정 전용으로 보관한다
--   teacher_ai: 학생·다른 선생님·화면에서는 읽을 수 없고, 서버 프로그램(supabase/functions/suggest)만 꺼내 쓴다
-- ---------------------------------------------------------------------
create table if not exists public.teacher_ai (
  uid uuid primary key, gemini_key text not null, model text, updated_at timestamptz not null default now());
alter table public.teacher_ai enable row level security;
revoke all on public.teacher_ai from anon, authenticated;
create or replace function public.ai_key_set(p_key text) returns json
language plpgsql security definer set search_path = public as $$
declare k text := trim(coalesce(p_key, ''));
begin
  if not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if k = '' then delete from public.teacher_ai where uid = auth.uid(); return json_build_object('ok', true, 'has', false); end if;
  if k !~ '^[A-Za-z0-9_.-]{20,200}$' then return json_build_object('ok', false, 'reason', 'format'); end if;
  insert into public.teacher_ai (uid, gemini_key) values (auth.uid(), k)
  on conflict (uid) do update set gemini_key = excluded.gemini_key, model = null, updated_at = now();
  return json_build_object('ok', true, 'has', true, 'tail', right(k, 4));
end $$;
create or replace function public.ai_key_status() returns json
language sql stable security definer set search_path = public as $$
  select json_build_object('teacher', public.is_teacher(), 'has', t.uid is not null, 'tail', right(t.gemini_key, 4), 'model', t.model)
  from (select 1) x left join public.teacher_ai t on t.uid = auth.uid() and public.is_teacher();
$$;
revoke execute on function public.ai_key_set(text), public.ai_key_status() from public, anon;
grant execute on function public.ai_key_set(text), public.ai_key_status() to authenticated;

-- ---------------------------------------------------------------------
-- 👥 과목 수강 학생: courses 문서의 data.members = [학생 id, …]
--   members가 있으면 그 학생에게만 과목·그 과목의 활동·글·댓글이 보이고, 글도 그 학생만 쓸 수 있다
--   members가 없는 예전 과목과 과목에 넣지 않은 활동은 지금처럼 선생님의 모든 학생에게 보인다
-- ---------------------------------------------------------------------
create or replace function public.course_for_me(p_course text, p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select case when jsonb_typeof(c.data -> 'members') = 'array'
                               then coalesce((c.data -> 'members') ? (public.my_student(p_tid)::text), false) else true end
                     from public.docs c where c.col = 'courses' and c.id = p_course and c.tid = p_tid limit 1), true);
$$;
create or replace function public.room_for_me(p_room text, p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select public.course_for_me(coalesce(r.data ->> 'courseId', ''), p_tid)
                     from public.docs r where r.col = 'rooms' and r.id = p_room and r.tid = p_tid limit 1), true);
$$;
create or replace function public.room_open_to_peers(p_room text, p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select r.data ->> 'reveal' from public.docs r
                    where r.col = 'rooms' and r.id = p_room and r.tid = p_tid), 'after') <> 'teacher'
     and public.room_for_me(p_room, p_tid);
$$;
revoke execute on function public.course_for_me(text, uuid), public.room_for_me(text, uuid) from public, anon;
grant execute on function public.course_for_me(text, uuid), public.room_for_me(text, uuid) to authenticated;
alter policy docs_read on public.docs using (
  (public.is_teacher() and tid = auth.uid())
  or (public.is_my_teacher(tid) and public.tid_active(tid) and (
        col = 'config'
     or (col = 'courses' and public.course_for_me(id, tid))
     or (col = 'rooms' and public.course_for_me(coalesce(data ->> 'courseId', ''), tid))
     or (col = 'posts' and (owner = public.my_student(tid) or public.room_open_to_peers(room_id, tid)))
     or (col in ('replies', 'treplies') and public.room_for_me(room_id, tid))))
);
alter policy docs_insert on public.docs with check (
  (public.is_teacher() and tid = auth.uid())
  or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid) and public.room_for_me(room_id, tid)
      and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
);
alter policy docs_update on public.docs
  using ((public.is_teacher() and tid = auth.uid())
         or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid)))
  with check ((public.is_teacher() and tid = auth.uid())
    or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid) and public.room_for_me(room_id, tid)
        and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class')));
-- 과목 공지·새 활동 알림: 그 과목 수강 학생 기기에만 (members가 없으면 모든 학생)
create or replace function public.push_targets_for(p_course text) returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
declare m jsonb;
begin
  if not public.is_teacher() then return; end if;
  if (select count(*) from public.notify_log where tid = auth.uid() and at > now() - interval '1 hour') >= 30 then return; end if;
  insert into public.notify_log (tid) values (auth.uid());
  select c.data -> 'members' into m from public.docs c where c.col = 'courses' and c.id = p_course and c.tid = auth.uid() limit 1;
  return query select s.endpoint, s.p256dh, s.auth from public.push_subs s
    join public.student_sessions ss on ss.uid = s.uid and ss.tid = auth.uid()
   where jsonb_typeof(m) is distinct from 'array' or m ? ss.student_id::text;
end $$;
revoke execute on function public.push_targets_for(text) from public, anon;
grant execute on function public.push_targets_for(text) to authenticated;

-- 학생 기기: 내 학생 번호(선생님마다 하나) — 선생님이 학생으로 정한 그룹을 알아볼 때 쓴다 (내 것만 돌려준다)
create or replace function public.my_student_ids() returns uuid[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(student_id), '{}') from public.student_sessions where uid = auth.uid();
$$;
revoke execute on function public.my_student_ids() from public, anon;
grant execute on function public.my_student_ids() to authenticated;

-- ---------------------------------------------------------------------
-- 📚 활동 자료 사진: 공개 보관함 materials/{교사 id}/…  (선생님만 자기 폴더에 올리고 지운다, 보기는 주소를 아는 누구나)
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('materials', 'materials', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do nothing;
do $$ begin
  if not exists (select 1 from pg_policies where schemaname = 'storage' and tablename = 'objects' and policyname = 'materials_insert') then
    create policy materials_insert on storage.objects for insert to authenticated
      with check (bucket_id = 'materials' and public.is_teacher() and (storage.foldername(name))[1] = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'storage' and tablename = 'objects' and policyname = 'materials_delete') then
    create policy materials_delete on storage.objects for delete to authenticated
      using (bucket_id = 'materials' and public.is_teacher() and (storage.foldername(name))[1] = auth.uid()::text);
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 👀 활동 조회 기록: 학생이 활동을 열어 보면 남는다 (글을 쓰지 않아도)
--   학생은 room_view()로 자기 기록만 남기고, 선생님은 room_viewers()로 자기 활동의 기록만 본다
--   표에 직접 읽고 쓰는 권한은 아무에게도 주지 않는다
-- ---------------------------------------------------------------------
create table if not exists public.room_views (
  tid        uuid not null,
  room_id    text not null,
  student_id uuid not null,
  first_at   timestamptz not null default now(),
  last_at    timestamptz not null default now(),
  n          int not null default 1,
  primary key (tid, room_id, student_id)
);
alter table public.room_views enable row level security;
revoke all on public.room_views from public, anon, authenticated;
create or replace function public.room_view(p_room text) returns void
language plpgsql volatile security definer set search_path = public as $$
declare v_tid uuid; v_sid uuid;
begin
  select d.tid into v_tid from public.docs d where d.col = 'rooms' and d.id = p_room limit 1;
  if v_tid is null then return; end if;
  v_sid := public.my_student(v_tid);
  if v_sid is null or not public.tid_active(v_tid) or not public.room_for_me(p_room, v_tid) then return; end if;
  insert into public.room_views (tid, room_id, student_id) values (v_tid, p_room, v_sid)
    on conflict (tid, room_id, student_id) do update set last_at = now(), n = least(public.room_views.n + 1, 100000);
end $$;
create or replace function public.room_viewers(p_room text) returns table(student_id uuid, first_at timestamptz, last_at timestamptz, n int)
language sql stable security definer set search_path = public as $$
  select v.student_id, v.first_at, v.last_at, v.n from public.room_views v
   where public.is_teacher() and v.tid = auth.uid() and v.room_id = p_room;
$$;
revoke execute on function public.room_view(text), public.room_viewers(text) from public, anon;
grant execute on function public.room_view(text), public.room_viewers(text) to authenticated;

-- ---------------------------------------------------------------------
-- 👥 학생 한 명이 여러 선생님 과목을 들을 때: 선생님마다 명단의 이름표가 다를 수 있다 (학교 이름 등)
--   my_students(): 이 기기에 연결된 선생님별 {tid, sid, name} — 글을 쓸 때 그 선생님 명단의 이름표를 쓴다
-- ---------------------------------------------------------------------
create or replace function public.my_students() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('tid', ss.tid, 'sid', ss.student_id,
           'name', case when s.school <> '' then s.school || ' ' else '' end || s.number || ' ' || s.name) order by ss.created_at), '[]'::json)
    from public.student_sessions ss join public.students s on s.id = ss.student_id
   where ss.uid = auth.uid();
$$;
revoke execute on function public.my_students() from public, anon;
grant execute on function public.my_students() to authenticated;

-- ---------------------------------------------------------------------
-- 🔔 알림은 과목이 있는 활동·공지만, 그 과목(과 고른 그룹) 학생에게만
--   course_push_targets: 과목이 없으면 아무에게도 안 보낸다. 그룹에 학생 명단이 있으면 그 그룹 학생만 (학생이 고르는 그룹이면 과목 전체)
-- ---------------------------------------------------------------------
create or replace function public.course_push_targets(p_tid uuid, p_course text, p_groups text[]) returns table(endpoint text, p256dh text, auth text)
language sql stable security definer set search_path = public as $$
  with c as (select d.data from public.docs d where d.col = 'courses' and d.id = p_course and d.tid = p_tid limit 1),
       gs as (select g from c, jsonb_array_elements(case when jsonb_typeof(c.data -> 'groups') = 'array' then c.data -> 'groups' else '[]'::jsonb end) g
               where g ->> 'id' = any(coalesce(p_groups, '{}'))),
       byg as (select coalesce(array_length(p_groups, 1), 0) > 0
                  and (select count(*) from gs) = array_length(p_groups, 1)
                  and not exists (select 1 from gs where jsonb_typeof(g -> 'members') is distinct from 'array') as v),
       gids as (select x as sid from gs, jsonb_array_elements_text(g -> 'members') x)
  select s.endpoint, s.p256dh, s.auth from public.push_subs s
    join public.student_sessions ss on ss.uid = s.uid and ss.tid = p_tid
   where exists (select 1 from c)
     and (case when (select v from byg) then ss.student_id::text in (select sid from gids)
               when jsonb_typeof((select data -> 'members' from c)) = 'array' then (select data -> 'members' from c) ? ss.student_id::text
               else true end);
$$;
revoke execute on function public.course_push_targets(uuid, text, text[]) from public, anon, authenticated;
-- 과목 공지·새 활동(그룹 지정 없음): 과목이 없으면 보내지 않는다
create or replace function public.push_targets_for(p_course text) returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  if not exists (select 1 from public.docs where col = 'courses' and id = p_course and tid = auth.uid()) then return; end if;
  if (select count(*) from public.notify_log where tid = auth.uid() and at > now() - interval '1 hour') >= 30 then return; end if;
  insert into public.notify_log (tid) values (auth.uid());
  return query select * from public.course_push_targets(auth.uid(), p_course, null);
end $$;
revoke execute on function public.push_targets_for(text) from public, anon;
grant execute on function public.push_targets_for(text) to authenticated;
-- 그룹에만 공개한 활동: 그 그룹 학생에게만
create or replace function public.push_targets_groups(p_course text, p_groups text[]) returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  if not exists (select 1 from public.docs where col = 'courses' and id = p_course and tid = auth.uid()) then return; end if;
  if (select count(*) from public.notify_log where tid = auth.uid() and at > now() - interval '1 hour') >= 30 then return; end if;
  insert into public.notify_log (tid) values (auth.uid());
  return query select * from public.course_push_targets(auth.uid(), p_course, p_groups);
end $$;
revoke execute on function public.push_targets_groups(text, text[]) from public, anon;
grant execute on function public.push_targets_groups(text, text[]) to authenticated;

-- ---------------------------------------------------------------------
-- ⏰ 예약 알림: 그룹 공개 시각이 되면 그 그룹 학생에게 알림 (pg_cron이 1분마다 notify-due 함수를 부른다)
--   push_jobs: 활동·그룹마다 하나 (시각을 바꾸면 덮어씀). 선생님은 push_schedule()로만 넣고 지운다
-- ---------------------------------------------------------------------
create table if not exists public.push_jobs (
  tid uuid not null, room_id text not null, grp text not null default '', course text not null,
  title text not null, body text not null default '', url text not null default '', tag text not null default '',
  send_at timestamptz not null, sent_at timestamptz, created_at timestamptz not null default now(),
  primary key (tid, room_id, grp));
create index if not exists push_jobs_due_idx on public.push_jobs (send_at) where sent_at is null;
alter table public.push_jobs enable row level security;
revoke all on public.push_jobs from public, anon, authenticated;
create or replace function public.push_schedule(p_room text, p_group text, p_at bigint, p_title text, p_body text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare d public.docs; v_course text; v_at timestamptz; g text := coalesce(p_group, '');
begin
  if not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into d from public.docs where col = 'rooms' and id = p_room and tid = auth.uid() limit 1;
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  v_course := coalesce(d.data ->> 'courseId', '');
  v_at := case when p_at is null then null else to_timestamp(p_at / 1000.0) end;
  if v_course = '' or not exists (select 1 from public.docs where col = 'courses' and id = v_course and tid = auth.uid())
     or v_at is null or v_at <= now() or v_at > now() + interval '120 days' then
    delete from public.push_jobs where tid = auth.uid() and room_id = p_room and grp = g and sent_at is null;
    return json_build_object('ok', true, 'scheduled', false);
  end if;
  if (select count(*) from public.push_jobs where tid = auth.uid() and sent_at is null) >= 300 then return json_build_object('ok', false, 'reason', 'too_many'); end if;
  insert into public.push_jobs (tid, room_id, grp, course, title, body, url, tag, send_at)
  values (auth.uid(), p_room, g, v_course, left(coalesce(p_title, '생각이음'), 80), left(coalesce(p_body, ''), 200), '#' || p_room, 'r-' || p_room, v_at)
  on conflict (tid, room_id, grp) do update set course = excluded.course, title = excluded.title, body = excluded.body, url = excluded.url, tag = excluded.tag,
    send_at = excluded.send_at, sent_at = null, created_at = now();
  return json_build_object('ok', true, 'scheduled', true);
end $$;
revoke execute on function public.push_schedule(text, text, bigint, text, text) from public, anon;
grant execute on function public.push_schedule(text, text, bigint, text, text) to authenticated;
-- 서버(notify-due, 관리자 열쇠)만: 때가 된 예약을 꺼내 보낼 기기와 함께 돌려주고 ‘보냄’으로 표시
--   활동이 지워졌거나, 마감·작성 중·보관이거나, 그 그룹이 종료면 보내지 않는다
create or replace function public.push_due_take(p_limit int default 50) returns json
language plpgsql volatile security definer set search_path = public as $$
declare out json;
begin
  with due as (
    select j.* from public.push_jobs j where j.sent_at is null and j.send_at <= now() order by j.send_at limit greatest(1, least(p_limit, 200)) for update skip locked),
  mark as (update public.push_jobs j set sent_at = now() from due where j.tid = due.tid and j.room_id = due.room_id and j.grp = due.grp returning j.*),
  ok as (
    select m.* from mark m join public.docs r on r.col = 'rooms' and r.id = m.room_id and r.tid = m.tid
     where coalesce(r.data ->> 'status', 'open') = 'open' and coalesce(r.data ->> 'open', 'true') <> 'false'
       and (m.grp = '' or coalesce(r.data -> 'assign' -> m.grp ->> 'status', 'open') <> 'closed'))
  select coalesce(json_agg(json_build_object('title', ok.title, 'body', ok.body, 'url', ok.url, 'tag', ok.tag,
           'targets', (select coalesce(json_agg(json_build_object('endpoint', t.endpoint, 'p256dh', t.p256dh, 'auth', t.auth)), '[]'::json)
                         from public.course_push_targets(ok.tid, ok.course, case when ok.grp = '' then null else array[ok.grp] end) t))), '[]'::json)
    into out from ok;
  return out;
end $$;
revoke execute on function public.push_due_take(int) from public, anon, authenticated;
grant execute on function public.push_due_take(int) to service_role;
-- 1분마다: 때가 된 예약이 있을 때만 notify-due를 부른다. 주소·열쇠는 app_secrets(functions_url, cron_key)에서 읽는다 (없으면 건너뜀)
do $cron$
begin
  if exists (select 1 from pg_available_extensions where name = 'pg_cron') and exists (select 1 from pg_available_extensions where name = 'pg_net') then
    create extension if not exists pg_cron;
    create extension if not exists pg_net;
    insert into public.app_secrets (k, v) values ('cron_key', replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '')) on conflict (k) do nothing;
    if exists (select 1 from cron.job where jobname = 'push-due') then perform cron.unschedule('push-due'); end if;
    perform cron.schedule('push-due', '* * * * *', $job$
      select net.http_post(
        url := (select v from public.app_secrets where k = 'functions_url') || '/notify-due',
        headers := jsonb_build_object('Content-Type', 'application/json', 'x-cron-key', (select v from public.app_secrets where k = 'cron_key')),
        body := '{}'::jsonb)
      where exists (select 1 from public.push_jobs where sent_at is null and send_at <= now())
        and exists (select 1 from public.app_secrets where k = 'functions_url')
    $job$);
  else
    raise notice 'pg_cron/pg_net 없음: 예약 알림은 건너뜀';
  end if;
end $cron$;
-- 이 프로젝트의 함수 주소를 한 번 넣어 주세요 (예: https://<프로젝트>.supabase.co/functions/v1)
-- insert into public.app_secrets (k, v) values ('functions_url', 'https://<프로젝트>.supabase.co/functions/v1') on conflict (k) do update set v = excluded.v;

-- ---------------------------------------------------------------------
-- 👩‍🏫 교사 이름: 처음 구글로 로그인하면 선생님이 직접 정하고, 나중에도 바꿀 수 있다
--   teachers.name_set = 선생님이 정한 이름 (그 뒤로는 구글 이름으로 덮어쓰지 않는다)
-- ---------------------------------------------------------------------
alter table public.teachers add column if not exists name_set boolean not null default false;
create or replace function public.teacher_checkin() returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) or coalesce(auth.jwt() ->> 'email', '') = '' then return; end if;
  insert into public.teachers (email, uid, name, first_at, last_at)
  values (lower(auth.jwt() ->> 'email'), auth.uid(),
          coalesce(auth.jwt() -> 'user_metadata' ->> 'display_name', auth.jwt() -> 'user_metadata' ->> 'full_name', auth.jwt() -> 'user_metadata' ->> 'name'), now(), now())
  on conflict (email) do update set uid = excluded.uid,
    name = case when public.teachers.name_set then public.teachers.name else coalesce(excluded.name, public.teachers.name) end, last_at = now();
end $$;
create or replace function public.teacher_set_name(p_name text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare v text := left(regexp_replace(trim(coalesce(p_name, '')), '\s+', ' ', 'g'), 30);
begin
  if not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if length(v) < 1 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  update public.teachers set name = v, name_set = true where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''));
  return json_build_object('ok', true, 'name', v);
end $$;
revoke execute on function public.teacher_set_name(text) from public, anon;
grant execute on function public.teacher_set_name(text) to authenticated;

-- ---------------------------------------------------------------------
-- 📚 학습 나눔: 선생님이 ‘학생끼리 서로 보기’(reveal ≠ teacher)로 열면, 그 활동을 볼 수 있는 학생은 친구 사진도 본다
--   기존 규칙(note_can_read: 자기 사진·선생님, 지우기도 같음)은 그대로 두고, ‘보기’ 규칙만 하나 더한다
-- ---------------------------------------------------------------------
create or replace function public.note_can_read_shared(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select case when (storage.foldername(p_name))[1] is null then false else
    public.my_student(public.room_tid((storage.foldername(p_name))[1])) is not null
    and public.tid_active(public.room_tid((storage.foldername(p_name))[1]))
    and public.room_open_to_peers((storage.foldername(p_name))[1], public.room_tid((storage.foldername(p_name))[1]))
  end;
$$;
revoke execute on function public.note_can_read_shared(text) from public, anon;
grant execute on function public.note_can_read_shared(text) to authenticated;
do $p$ begin
  if not exists (select 1 from pg_policies where schemaname = 'storage' and tablename = 'objects' and policyname = 'notes_read_shared') then
    create policy notes_read_shared on storage.objects for select to authenticated
      using (bucket_id = 'notes' and public.note_can_read_shared(name));
  end if;
end $p$;

-- ---------------------------------------------------------------------
-- 📨 학생 개별 안내: 선생님이 고른 학생에게만 보내는 안내 (학생이 앱을 열면 화면 가운데에 크게 뜬다)
--   student_msgs: 받는 학생마다 한 줄. 같은 번에 보낸 것은 batch가 같다
--   표에 직접 읽고 쓰는 권한은 아무에게도 주지 않는다. 선생님은 msg_send/msg_sent/msg_withdraw, 학생은 my_msgs/msg_read로만
-- ---------------------------------------------------------------------
create table if not exists public.student_msgs (
  id         bigint generated always as identity primary key,
  tid        uuid not null,
  batch      text not null,
  student_id uuid not null references public.students(id) on delete cascade,
  title      text not null default '',
  body       text not null,
  created_at timestamptz not null default now(),
  read_at    timestamptz
);
alter table public.student_msgs add column if not exists withdrawn_at timestamptz;   -- 선생님이 거둔 안내 (지우지 않고 숨긴다)
create index if not exists student_msgs_sid_idx on public.student_msgs (student_id, created_at desc);
create index if not exists student_msgs_tid_idx on public.student_msgs (tid, created_at desc);
alter table public.student_msgs enable row level security;
revoke all on public.student_msgs from public, anon, authenticated;
-- 선생님: 내 명단의 학생에게만 보낸다 (한 번에 300명, 1시간에 30번까지)
create or replace function public.msg_send(p_students uuid[], p_title text, p_body text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare v_body text := left(trim(coalesce(p_body, '')), 1000); v_title text := left(trim(coalesce(p_title, '')), 60);
        v_batch text := gen_random_uuid()::text; v_n int;
begin
  if not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if length(v_body) < 1 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  if coalesce(array_length(p_students, 1), 0) = 0 or array_length(p_students, 1) > 300 then return json_build_object('ok', false, 'reason', 'students'); end if;
  if (select count(distinct batch) from public.student_msgs where tid = auth.uid() and created_at > now() - interval '1 hour') >= 30 then
    return json_build_object('ok', false, 'reason', 'limit'); end if;
  insert into public.student_msgs (tid, batch, student_id, title, body)
    select auth.uid(), v_batch, s.id, v_title, v_body from public.students s where s.tid = auth.uid() and s.id = any(p_students);
  get diagnostics v_n = row_count;
  if v_n = 0 then return json_build_object('ok', false, 'reason', 'students'); end if;
  return json_build_object('ok', true, 'batch', v_batch, 'n', v_n);
end $$;
-- 선생님: 내가 보낸 안내 (최근 100번) · 학생마다 읽은 시각
create or replace function public.msg_sent() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(b order by b.at desc), '[]'::json) from (
    select m.batch, max(m.title) as title, max(m.body) as body, min(m.created_at) as at,
           json_agg(json_build_object('sid', m.student_id, 'read_at', m.read_at)) as rcpt
      from public.student_msgs m where public.is_teacher() and m.tid = auth.uid() and m.withdrawn_at is null
     group by m.batch order by min(m.created_at) desc limit 100) b;
$$;
-- 선생님: 보낸 안내 거두기 (p_student가 없으면 그 번에 보낸 학생 모두) — 지우지 않고 withdrawn_at만 남겨 양쪽 화면에서 숨긴다
create or replace function public.msg_withdraw(p_batch text, p_student uuid) returns int
language plpgsql volatile security definer set search_path = public as $$
declare v_n int;
begin
  if not public.is_teacher() then return 0; end if;
  update public.student_msgs set withdrawn_at = now()
   where tid = auth.uid() and batch = p_batch and withdrawn_at is null and (p_student is null or student_id = p_student);
  get diagnostics v_n = row_count; return v_n;
end $$;
-- 학생: 나에게 온 안내 (최근 90일, 50개). 사용이 막힌 선생님의 안내는 빼고
create or replace function public.my_msgs() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(x order by x.at desc), '[]'::json) from (
    select m.id, m.title, m.body, m.created_at as at, m.read_at, coalesce(t.name, '') as teacher
      from public.student_msgs m
      join public.student_sessions ss on ss.uid = auth.uid() and ss.tid = m.tid and ss.student_id = m.student_id
      left join public.teachers t on t.uid = m.tid
     where m.withdrawn_at is null and m.created_at > now() - interval '90 days' and public.tid_active(m.tid)
     order by m.created_at desc limit 50) x;
$$;
-- 학생: ‘확인했어요’ (내 것만)
create or replace function public.msg_read(p_ids bigint[]) returns void
language sql volatile security definer set search_path = public as $$
  update public.student_msgs m set read_at = now()
   where m.id = any(coalesce(p_ids, '{}')) and m.read_at is null
     and exists (select 1 from public.student_sessions ss where ss.uid = auth.uid() and ss.tid = m.tid and ss.student_id = m.student_id);
$$;
revoke execute on function public.msg_send(uuid[], text, text), public.msg_sent(), public.msg_withdraw(text, uuid), public.my_msgs(), public.msg_read(bigint[]) from public, anon;
grant execute on function public.msg_send(uuid[], text, text), public.msg_sent(), public.msg_withdraw(text, uuid), public.my_msgs(), public.msg_read(bigint[]) to authenticated;
-- 🔔 개별 알림: 고른 학생(안내)·그 글을 쓴 학생(재제출 요청)의 기기에만. 1시간 30번 제한은 다른 알림과 함께 센다
create or replace function public.push_targets_students(p_students uuid[]) returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_teacher() or coalesce(array_length(p_students, 1), 0) = 0 then return; end if;
  if (select count(*) from public.notify_log where tid = auth.uid() and at > now() - interval '1 hour') >= 30 then return; end if;
  insert into public.notify_log (tid) values (auth.uid());
  return query select s.endpoint, s.p256dh, s.auth from public.push_subs s
    join public.student_sessions ss on ss.uid = s.uid and ss.tid = auth.uid()
   where ss.student_id = any(p_students);
end $$;
create or replace function public.push_targets_post(p_post text) returns table(endpoint text, p256dh text, auth text)
language plpgsql security definer set search_path = public as $$
declare v_sid uuid;
begin
  if not public.is_teacher() then return; end if;
  select d.owner into v_sid from public.docs d where d.col = 'posts' and d.id = p_post and d.tid = auth.uid() limit 1;
  if v_sid is null then return; end if;
  return query select * from public.push_targets_students(array[v_sid]);
end $$;
revoke execute on function public.push_targets_students(uuid[]), public.push_targets_post(text) from public, anon;
grant execute on function public.push_targets_students(uuid[]), public.push_targets_post(text) to authenticated;

-- ---------------------------------------------------------------------
-- 📊 수행평가 점수 안내: 학생마다 내용이 다른 안내(점수) + 예/아니오 질문 (확인했나요? · 이의가 있나요?)
--   kind = 'score', ask = 질문 목록, answers = 학생의 예/아니오(true/false) 목록, answered_at = 응답 시각
-- ---------------------------------------------------------------------
alter table public.student_msgs add column if not exists kind text not null default 'note';
alter table public.student_msgs add column if not exists ask jsonb;
alter table public.student_msgs add column if not exists answers jsonb;
alter table public.student_msgs add column if not exists answered_at timestamptz;
-- 선생님: 학생마다 다른 내용 보내기 p_items = [{sid, body}], p_ask = ["질문", …] (5개까지)
create or replace function public.msg_send_each(p_title text, p_items jsonb, p_ask jsonb) returns json
language plpgsql volatile security definer set search_path = public as $$
declare v_title text := left(trim(coalesce(p_title, '')), 60); v_batch text := gen_random_uuid()::text; v_n int; v_ask jsonb;
begin
  if not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if jsonb_typeof(p_items) is distinct from 'array' or jsonb_array_length(p_items) = 0 or jsonb_array_length(p_items) > 300 then
    return json_build_object('ok', false, 'reason', 'students'); end if;
  if (select count(distinct batch) from public.student_msgs where tid = auth.uid() and created_at > now() - interval '1 hour') >= 30 then
    return json_build_object('ok', false, 'reason', 'limit'); end if;
  select case when count(*) = 0 then null else jsonb_agg(left(trim(q), 100)) end into v_ask
    from (select q from jsonb_array_elements_text(case when jsonb_typeof(p_ask) = 'array' then p_ask else '[]'::jsonb end) with ordinality a(q, i)
           where trim(q) <> '' order by i limit 5) z;
  insert into public.student_msgs (tid, batch, student_id, title, body, kind, ask)
    select distinct on (s.id) auth.uid(), v_batch, s.id, v_title, left(trim(it ->> 'body'), 2000), 'score', v_ask
      from jsonb_array_elements(p_items) it join public.students s on s.tid = auth.uid() and s.id::text = it ->> 'sid'
     where length(trim(coalesce(it ->> 'body', ''))) > 0;
  get diagnostics v_n = row_count;
  if v_n = 0 then return json_build_object('ok', false, 'reason', 'students'); end if;
  return json_build_object('ok', true, 'batch', v_batch, 'n', v_n);
end $$;
-- 학생: 예/아니오 답하기 (내 것만, 한 번만). 답하면 읽음으로도
create or replace function public.msg_answer(p_id bigint, p_answers jsonb) returns json
language plpgsql volatile security definer set search_path = public as $$
declare m public.student_msgs;
begin
  select * into m from public.student_msgs x where x.id = p_id and x.withdrawn_at is null
     and exists (select 1 from public.student_sessions ss where ss.uid = auth.uid() and ss.tid = x.tid and ss.student_id = x.student_id);
  if m.id is null or m.ask is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if m.answered_at is not null then return json_build_object('ok', false, 'reason', 'done'); end if;
  if jsonb_typeof(p_answers) is distinct from 'array' or jsonb_array_length(p_answers) <> jsonb_array_length(m.ask)
     or exists (select 1 from jsonb_array_elements(p_answers) a where jsonb_typeof(a) <> 'boolean') then
    return json_build_object('ok', false, 'reason', 'bad'); end if;
  update public.student_msgs set answers = p_answers, answered_at = now(), read_at = coalesce(read_at, now()) where id = m.id;
  return json_build_object('ok', true);
end $$;
revoke execute on function public.msg_send_each(text, jsonb, jsonb), public.msg_answer(bigint, jsonb) from public, anon;
grant execute on function public.msg_send_each(text, jsonb, jsonb), public.msg_answer(bigint, jsonb) to authenticated;
-- 보낸 안내·받은 안내에 종류·질문·응답을 함께 (점수 안내는 학생마다 내용이 달라 학생별 내용도)
create or replace function public.msg_sent() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(b order by b.at desc), '[]'::json) from (
    select m.batch, max(m.title) as title, max(m.body) as body, min(m.created_at) as at, max(m.kind) as kind, (array_agg(m.ask))[1] as ask,
           json_agg(json_build_object('sid', m.student_id, 'read_at', m.read_at, 'answers', m.answers, 'answered_at', m.answered_at,
                                      'body', case when m.kind = 'score' then m.body end)) as rcpt
      from public.student_msgs m where public.is_teacher() and m.tid = auth.uid() and m.withdrawn_at is null
     group by m.batch order by min(m.created_at) desc limit 100) b;
$$;
create or replace function public.my_msgs() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(x order by x.at desc), '[]'::json) from (
    select m.id, m.title, m.body, m.created_at as at, m.read_at, coalesce(t.name, '') as teacher,
           m.kind, m.ask, m.answers, m.answered_at
      from public.student_msgs m
      join public.student_sessions ss on ss.uid = auth.uid() and ss.tid = m.tid and ss.student_id = m.student_id
      left join public.teachers t on t.uid = m.tid
     where m.withdrawn_at is null and m.created_at > now() - interval '90 days' and public.tid_active(m.tid)
     order by m.created_at desc limit 50) x;
$$;

-- ---------------------------------------------------------------------
-- 🙋 과목 없는 활동: 학생 코드 없이 이름·닉네임만 넣고 바로 참여 (임시 참가자)
--   guest_sessions: 이 기기(익명 세션)가 어느 활동에 어떤 이름으로 들어왔는지 (활동마다 한 줄)
--   · 과목이 없는 활동(courseId가 비어 있음)의 링크·QR로 들어온 사람만 참가자가 될 수 있고, 들어온 활동의 글·댓글·하트만 쓰고 본다
--   · 한 기기는 이름 하나만 쓴다(여러 활동에 들어가도 같은 이름). 같은 활동에서는 이름이 겹치지 않는다
--   · 학번처럼 숫자만 있는 낱말(3~10자리)이 들어간 이름은 못 쓴다 → 코드로 들어온 학생의 이름표(‘학번 이름’)를 흉내 낼 수 없다
--   · 활동 하나에 참가자는 500명까지. 참가자는 읽기·쓰기·고치기만 가능하고 지울 수는 없다
-- ---------------------------------------------------------------------
create table if not exists public.guest_sessions (
  uid        uuid not null,
  room_id    text not null,
  tid        uuid not null,               -- 활동을 만든 선생님
  nick       text not null,               -- 화면에 보이는 이름
  nick_key   text not null,               -- 겹침 확인용(공백 없애고 소문자)
  created_at timestamptz not null default now(),
  primary key (uid, room_id)
);
create unique index if not exists guest_sessions_room_nick on public.guest_sessions (room_id, nick_key);
create index if not exists guest_sessions_tid_idx on public.guest_sessions (tid);
alter table public.guest_sessions enable row level security;
revoke all on public.guest_sessions from public, anon, authenticated;

-- 과목이 없는 활동인가
create or replace function public.room_is_free(p_room text) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.docs r
                  where r.col = 'rooms' and r.id = p_room and coalesce(r.data ->> 'courseId', '') = '');
$$;
-- 지금 새로 들어올 수 있는 활동인가 (과목 없음 · 작성 중/보관 아님 · 선생님이 막히지 않음)
create or replace function public.guest_room_ok(p_room text) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.docs r
                  where r.col = 'rooms' and r.id = p_room
                    and coalesce(r.data ->> 'courseId', '') = ''
                    and coalesce(r.data ->> 'status', 'open') not in ('draft', 'archived')
                    and public.tid_active(r.tid));
$$;
create or replace function public.guest_in(p_room text) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.guest_sessions g where g.uid = auth.uid() and g.room_id = p_room);
$$;
create or replace function public.my_guest_name(p_room text) returns text
language sql stable security definer set search_path = public as $$
  select g.nick from public.guest_sessions g where g.uid = auth.uid() and g.room_id = p_room;
$$;
-- 참가자가 쓴 글의 주인 표시 = 자기 계정 번호 (이 활동에 들어와 있을 때만)
create or replace function public.guest_owner(p_room text) returns uuid
language sql stable security definer set search_path = public as $$
  select case when public.guest_in(p_room) and public.room_is_free(p_room) then auth.uid() end;
$$;
-- 참가자가 볼 수 있는 문서: 들어온 활동, 그 활동의 글(내 글 + 친구에게 열린 글)·댓글·하트, 내게 온 선생님 피드백과 반 전체 피드백
create or replace function public.guest_can_read(p_col text, p_id text, p_room text, p_tid uuid, p_owner uuid, p_data jsonb) returns boolean
language sql stable security definer set search_path = public as $$
  select auth.uid() is not null
     and exists (select 1 from public.guest_sessions g
                  where g.uid = auth.uid() and g.tid = p_tid and g.room_id = case when p_col = 'rooms' then p_id else p_room end)
     and public.room_is_free(case when p_col = 'rooms' then p_id else p_room end)
     and public.tid_active(p_tid)
     and case p_col
           when 'rooms'    then true
           when 'posts'    then p_owner = auth.uid() or public.room_open_to_peers(p_room, p_tid)
           when 'replies'  then true
           when 'treplies' then coalesce(p_data ->> 'kind', '') = 'class'
                                or exists (select 1 from public.docs x
                                            where x.col = 'posts' and x.id = p_data ->> 'postId' and x.tid = p_tid and x.owner = auth.uid())
           else false end;
$$;

-- 활동 링크로 들어온 사람이 이름·닉네임을 넣고 참가자가 된다 (익명 세션만, 교사·코드 학생은 해당 없음)
create or replace function public.guest_join(p_room text, p_nick text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; v_have text; v_nick text; v_key text;
begin
  if auth.uid() is null or not coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) then
    return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into r from public.docs where col = 'rooms' and id = p_room limit 1;
  if not found or not public.guest_room_ok(p_room) then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if public.my_student(r.tid) is not null then return json_build_object('ok', false, 'reason', 'student'); end if;
  select nick into v_have from public.guest_sessions where uid = auth.uid() and room_id = p_room;       -- 이미 들어와 있으면 그대로
  if v_have is not null then return json_build_object('ok', true, 'name', v_have); end if;
  select nick into v_have from public.guest_sessions where uid = auth.uid() order by created_at limit 1;  -- 이 기기의 이름은 하나
  v_nick := regexp_replace(regexp_replace(trim(coalesce(v_have, p_nick, '')), '[[:cntrl:]]', '', 'g'), '\s+', ' ', 'g');
  if char_length(v_nick) < 1 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  if char_length(v_nick) > 20 then return json_build_object('ok', false, 'reason', 'long'); end if;
  if exists (select 1 from unnest(string_to_array(v_nick, ' ')) as t(x) where x ~ '^[0-9]{3,10}$') then
    return json_build_object('ok', false, 'reason', 'number'); end if;
  v_key := lower(replace(v_nick, ' ', ''));
  if v_key in ('선생님', '선생', 'teacher', '관리자', '익명') then return json_build_object('ok', false, 'reason', 'reserved'); end if;
  if (select count(*) from public.guest_sessions where room_id = p_room) >= 500 then return json_build_object('ok', false, 'reason', 'full'); end if;
  begin
    insert into public.guest_sessions (uid, room_id, tid, nick, nick_key) values (auth.uid(), p_room, r.tid, v_nick, v_key);
  exception when unique_violation then
    return json_build_object('ok', false, 'reason', 'taken');
  end;
  return json_build_object('ok', true, 'name', v_nick);
end $$;

-- 이 기기가 들어온 활동들 [{room, nick}]
create or replace function public.my_guests() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('room', g.room_id, 'nick', g.nick) order by g.created_at), '[]'::json)
    from public.guest_sessions g where g.uid = auth.uid();
$$;

revoke execute on function public.room_is_free(text), public.guest_room_ok(text), public.guest_in(text), public.my_guest_name(text), public.guest_owner(text),
  public.guest_can_read(text, text, text, uuid, uuid, jsonb), public.guest_join(text, text), public.my_guests() from public, anon;
grant execute on function public.room_is_free(text), public.guest_room_ok(text), public.guest_in(text), public.my_guest_name(text), public.guest_owner(text),
  public.guest_can_read(text, text, text, uuid, uuid, jsonb), public.guest_join(text, text), public.my_guests() to authenticated;

-- 글을 저장할 때 서버가 채우는 ‘글 주인’: 코드로 들어온 학생이면 학생 번호, 참가자면 자기 계정 번호
create or replace function public.docs_stamp() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.room_id := new.data ->> 'roomId';
  new.updated_at := now();
  if tg_op = 'INSERT' then
    if public.is_teacher() then
      new.tid := auth.uid();
      new.owner := null;
    else                                            -- 학생 글: 그 활동을 만든 교사의 것
      new.tid := (select r.tid from public.docs r where r.col = 'rooms' and r.id = new.room_id limit 1);
      new.owner := coalesce(public.my_student(new.tid), public.guest_owner(new.room_id));
    end if;
    new.created_at := now();
  else
    new.tid := old.tid;
    new.owner := old.owner;
    new.created_at := old.created_at;
  end if;
  return new;
end $$;

-- 규칙: 기존 학생 규칙은 그대로 두고, 참가자 규칙을 한 줄씩 더한다
alter policy docs_read on public.docs using (
  (public.is_teacher() and tid = auth.uid())
  or (public.is_my_teacher(tid) and public.tid_active(tid) and (
        col = 'config'
     or (col = 'courses' and public.course_for_me(id, tid))
     or (col = 'rooms' and public.course_for_me(coalesce(data ->> 'courseId', ''), tid))
     or (col = 'posts' and (owner = public.my_student(tid) or public.room_open_to_peers(room_id, tid)))
     or (col in ('replies', 'treplies') and public.room_for_me(room_id, tid))))
  or public.guest_can_read(col, id, room_id, tid, owner, data)
);
alter policy docs_insert on public.docs with check (
  (public.is_teacher() and tid = auth.uid())
  or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid) and public.room_for_me(room_id, tid)
      and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
  or (col in ('posts', 'replies') and owner is not null and owner = public.guest_owner(room_id) and public.tid_active(tid)
      and data ->> 'author' = public.my_guest_name(room_id) and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
);
alter policy docs_update on public.docs
  using ((public.is_teacher() and tid = auth.uid())
         or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid))
         or (col in ('posts', 'replies') and owner is not null and owner = public.guest_owner(room_id) and public.tid_active(tid)))
  with check ((public.is_teacher() and tid = auth.uid())
    or (col in ('posts', 'replies') and owner is not null and owner = public.my_student(tid) and public.tid_active(tid) and public.room_for_me(room_id, tid)
        and data ->> 'author' = public.my_student_name(tid) and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
    or (col in ('posts', 'replies') and owner is not null and owner = public.guest_owner(room_id) and public.tid_active(tid)
        and data ->> 'author' = public.my_guest_name(room_id) and coalesce(data ->> 'kind', '') not in ('teacher', 'class')));

-- 지금 접속한 사람이 누구인지 (참가자 정보 추가)
--   guest_room: 이 링크의 활동에 이름만 넣고 들어올 수 있나 · guest_name: 이 활동에 들어온 내 이름 · guest_nick: 이 기기가 쓰는 이름 · ref_found: 링크가 가리키는 활동·수업을 찾았나
create or replace function public.whoami(p_ref text default null) returns json
language plpgsql stable security definer set search_path = public as $$
declare t uuid; nm text; anon boolean := coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false);
        gnm text; gnick text; groom boolean := false; gtitle text; gteach text;
begin
  if p_ref is not null and p_ref <> '' then
    select d.tid into t from public.docs d where d.id = p_ref and d.col in ('rooms', 'courses') limit 1;
  end if;
  if t is not null then
    nm := public.my_student_name(t);
  else
    select case when s.school <> '' then s.school || ' ' else '' end || s.number || ' ' || s.name into nm
      from public.student_sessions ss join public.students s on s.id = ss.student_id
     where ss.uid = auth.uid() order by ss.created_at desc limit 1;
  end if;
  if anon then
    select g.nick into gnick from public.guest_sessions g where g.uid = auth.uid() order by g.created_at limit 1;
    if p_ref is not null and p_ref <> '' then
      gnm := public.my_guest_name(p_ref);
      if nm is null and public.guest_room_ok(p_ref) then
        groom := true;
        select r.data ->> 'title', r.data ->> 'teacherName' into gtitle, gteach from public.docs r where r.col = 'rooms' and r.id = p_ref limit 1;
      end if;
    end if;
  end if;
  return json_build_object(
    'teacher', public.is_teacher(),
    'admin', public.is_admin(),
    'blocked', (not anon) and exists (select 1 from public.teachers x where x.blocked and lower(x.email) = lower(coalesce(auth.jwt() ->> 'email', ''))),
    'email', case when anon then null else auth.jwt() ->> 'email' end,
    'student_name', nm, 'ref_found', t is not null,
    'guest_room', groom, 'guest_name', gnm, 'guest_nick', gnick, 'guest_title', gtitle, 'guest_teacher', gteach);
end $$;

-- 📸 학습 나눔 사진: 참가자의 폴더 이름은 자기 계정 번호 (코드 학생은 학생 번호)
create or replace function public.my_student_id(p_room text) returns uuid
language sql stable security definer set search_path = public as $$
  select coalesce(public.my_student(public.room_tid(p_room)), public.guest_owner(p_room));
$$;
create or replace function public.note_can_read(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select case when (storage.foldername(p_name))[1] is null then false else
    (public.is_teacher() and public.room_tid((storage.foldername(p_name))[1]) = auth.uid())
    or coalesce((storage.foldername(p_name))[2] = public.my_student(public.room_tid((storage.foldername(p_name))[1]))::text, false)
    or coalesce((storage.foldername(p_name))[2] = public.guest_owner((storage.foldername(p_name))[1])::text, false)
  end;
$$;
create or replace function public.note_can_write(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(((storage.foldername(p_name))[2] = public.my_student(public.room_tid((storage.foldername(p_name))[1]))::text
                   or (storage.foldername(p_name))[2] = public.guest_owner((storage.foldername(p_name))[1])::text)
                  and public.tid_active(public.room_tid((storage.foldername(p_name))[1])), false);
$$;
create or replace function public.note_can_read_shared(p_name text) returns boolean
language sql stable security definer set search_path = public as $$
  select case when (storage.foldername(p_name))[1] is null then false else
    (public.my_student(public.room_tid((storage.foldername(p_name))[1])) is not null or public.guest_owner((storage.foldername(p_name))[1]) is not null)
    and public.tid_active(public.room_tid((storage.foldername(p_name))[1]))
    and public.room_open_to_peers((storage.foldername(p_name))[1], public.room_tid((storage.foldername(p_name))[1]))
  end;
$$;

-- 🎭 가상 인물 대화: 참가자도 쓸 수 있다 (질문 횟수는 참가자마다 같은 제한 + 활동 하나의 참가자 전체 600번까지)
--   선생님 지시문(persona.guide)과 최대 질문 수도 돌려준다 → chat 함수가 지시문이 있는 활동만 지시문 규칙으로 대화
create or replace function public.chat_begin(p_room text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare d public.docs; v_sid uuid; v_who text; v_lim int; v_used int; v_st text; p jsonb; v_guest boolean := false;
begin
  select * into d from public.docs where col = 'rooms' and id = p_room limit 1;
  if not found or coalesce(d.data ->> 'template', '') <> 'chat' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  p := coalesce(d.data -> 'persona', '{}'::jsonb);
  if public.is_teacher() and d.tid = auth.uid() then
    v_who := 'T:' || auth.uid(); v_lim := 200;
  else
    v_sid := public.my_student(d.tid);
    if v_sid is null then v_sid := public.guest_owner(p_room); v_guest := v_sid is not null; end if;
    if v_sid is null or not public.tid_active(d.tid) or not public.room_for_me(p_room, d.tid) then return json_build_object('ok', false, 'reason', 'denied'); end if;
    v_st := coalesce(d.data ->> 'status', 'open');
    if v_st in ('draft', 'archived', 'closed') or d.data ->> 'open' = 'false'
       or (jsonb_typeof(d.data -> 'dueAt') = 'number' and (d.data ->> 'dueAt')::numeric <= extract(epoch from now()) * 1000) then
      return json_build_object('ok', false, 'reason', 'closed'); end if;
    v_who := case when v_guest then 'G:' || v_sid::text else v_sid::text end;
    if v_guest and (select coalesce(sum(n), 0) from public.chat_usage where room_id = p_room and who like 'G:%') >= 600 then
      return json_build_object('ok', false, 'reason', 'limit'); end if;
    v_lim := least(30, greatest(1, coalesce(nullif(p ->> 'maxTurns', '')::int, 8))) + 2;
  end if;
  insert into public.chat_usage (room_id, who, n) values (p_room, v_who, 0) on conflict do nothing;
  select n into v_used from public.chat_usage where room_id = p_room and who = v_who for update;
  if v_used >= v_lim then return json_build_object('ok', false, 'reason', 'limit'); end if;
  update public.chat_usage set n = n + 1, updated_at = now() where room_id = p_room and who = v_who;
  return json_build_object('ok', true, 'name', coalesce(nullif(p ->> 'name', ''), '인물'), 'about', coalesce(p ->> 'about', ''), 'style', coalesce(p ->> 'style', 'persona'),
    'prompt', coalesce(d.data ->> 'prompt', ''), 'context', left(coalesce(d.data ->> 'context', ''), 6000), 'facts', left(coalesce(p ->> 'facts', ''), 4000),
    'remaining', v_lim - v_used - 1,
    -- 선생님이 적용한 대화 지시문(프롬프트)과 학생 한 명의 최대 질문 수 (지시문이 없으면 빈 글 → 예전과 같은 규칙으로 대화)
    'guide', left(coalesce(p ->> 'guide', ''), 6000), 'max_turns', least(30, greatest(1, coalesce(nullif(p ->> 'maxTurns', '')::int, 8))),
    -- 캐릭터 설정(학생에게 보이는 값): 시작 메시지, 학생의 역할, 캐릭터가 학생을 부르는 말 → chat 함수가 역할·호칭을 고정하는 데 쓴다
    'greeting', left(coalesce(p ->> 'greeting', ''), 600), 'user_role', left(coalesce(p ->> 'user', ''), 80), 'call', left(coalesce(p ->> 'call', ''), 20));
end $$;

-- =====================================================================
-- 마지막으로 관리자(나)의 구글 이메일을 등록하세요 (따옴표 안을 바꿔서 실행)
-- 다른 선생님은 등록하지 않아도 구글로 로그인하면 바로 교사가 돼요
-- insert into public.teachers (email, admin) values ('me@example.com', true) on conflict (email) do update set admin = true;
-- =====================================================================

-- ---------------------------------------------------------------------
-- 🚪 교사 탈퇴: 내 과목·활동·학생 명단·안내·알림 구독·AI 키와 계정을 지운다 (되돌릴 수 없다)
--   · 올린 사진 파일은 앱이 저장소(Storage) API로 먼저 지운다 (여기서는 데이터베이스만)
--   · p_dry = true 이면 아무것도 지우지 않고 ‘탈퇴할 수 있는 계정인지’만 알려 준다
--   · 관리자 계정은 탈퇴할 수 없다 (먼저 다른 관리자에게 넘긴다)
-- ---------------------------------------------------------------------
create or replace function public.teacher_delete_me(p_dry boolean default false) returns json
language plpgsql volatile security definer set search_path = public as $$
declare v uuid := auth.uid(); em text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if v is null or not public.is_teacher() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if public.is_admin() then return json_build_object('ok', false, 'reason', 'admin'); end if;
  if p_dry then return json_build_object('ok', true, 'dry', true); end if;
  delete from public.docs          where tid = v;
  delete from public.room_views    where tid = v;
  delete from public.push_jobs     where tid = v;
  delete from public.notify_log    where tid = v;
  delete from public.guest_sessions where tid = v;
  delete from public.student_msgs  where tid = v;
  delete from public.students      where tid = v;
  delete from public.teacher_ai    where uid = v;
  delete from public.push_subs     where uid = v;
  delete from public.teachers      where uid = v or lower(email) = em;
  delete from auth.users           where id = v;
  return json_build_object('ok', true);
end $$;
revoke execute on function public.teacher_delete_me(boolean) from public, anon;
grant  execute on function public.teacher_delete_me(boolean) to authenticated;

-- ---------------------------------------------------------------------
-- 📎 학습 나눔 파일 첨부(선생님이 활동 설정에서 켠 때만): ‘notes’ 보관함이 사진 말고 문서도 받도록
-- 파일 한 개 10MB까지. 형식은 앱에서 PDF·한글·워드·PPT·엑셀·텍스트로 제한한다(보관함은 비공개, 경로 정책은 그대로).
-- 여러 번 실행해도 안전하다.
-- ---------------------------------------------------------------------
update storage.buckets set file_size_limit = 10485760, allowed_mime_types = null where id = 'notes';
