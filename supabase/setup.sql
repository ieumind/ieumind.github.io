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
    'prompt', coalesce(d.data ->> 'prompt', ''), 'context', left(coalesce(d.data ->> 'context', ''), 6000), 'remaining', v_lim - v_used - 1);
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

-- =====================================================================
-- 마지막으로 관리자(나)의 구글 이메일을 등록하세요 (따옴표 안을 바꿔서 실행)
-- 다른 선생님은 등록하지 않아도 구글로 로그인하면 바로 교사가 돼요
-- insert into public.teachers (email, admin) values ('me@example.com', true) on conflict (email) do update set admin = true;
-- =====================================================================
