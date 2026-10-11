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

-- =====================================================================
-- 마지막으로 관리자(나)의 구글 이메일을 등록하세요 (따옴표 안을 바꿔서 실행)
-- 다른 선생님은 등록하지 않아도 구글로 로그인하면 바로 교사가 돼요
-- insert into public.teachers (email, admin) values ('me@example.com', true) on conflict (email) do update set admin = true;
-- =====================================================================
