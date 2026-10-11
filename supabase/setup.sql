-- =====================================================================
-- 생각이음 · Supabase 설정 (SQL Editor에 통째로 붙여 넣고 Run)
-- 여러 번 실행해도 괜찮게 만들어져 있어요.
-- =====================================================================

-- 1) 앱 데이터: 활동(rooms)·학생 글(posts)·댓글(replies) 등을 한 표에 문서처럼 저장
create table if not exists public.docs (
  col        text not null,
  id         text not null,
  data       jsonb not null default '{}'::jsonb,
  owner      uuid,                     -- 학생이 쓴 문서의 주인(학생 id). 서버가 채운다
  room_id    text,                     -- data.roomId (공개 범위 확인용). 서버가 채운다
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (col, id)
);
create index if not exists docs_room_idx on public.docs (col, room_id);

-- 2) 교사 명단: 여기에 들어 있는 구글 계정만 교사 화면을 쓴다
create table if not exists public.teachers (
  email text primary key
);

-- 3) 학생 명단과 개인 코드 (학생에게는 절대 보이지 않는다)
create table if not exists public.students (
  id         uuid primary key default gen_random_uuid(),
  number     text not null,
  name       text not null,
  code       text not null unique,
  created_at timestamptz not null default now(),
  unique (number, name)
);

-- 4) 이 기기(익명 세션) = 어떤 학생인지
create table if not exists public.student_sessions (
  uid        uuid primary key,
  student_id uuid not null references public.students(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.docs             enable row level security;
alter table public.teachers         enable row level security;
alter table public.students         enable row level security;
alter table public.student_sessions enable row level security;

-- ---------------------------------------------------------------------
-- 권한 판단 함수
-- ---------------------------------------------------------------------
create or replace function public.is_teacher() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) = false
     and exists (select 1 from public.teachers t
                 where lower(t.email) = lower(coalesce(auth.jwt() ->> 'email', '')));
$$;

create or replace function public.my_student() returns uuid
language sql stable security definer set search_path = public as $$
  select student_id from public.student_sessions where uid = auth.uid();
$$;

create or replace function public.my_student_name() returns text
language sql stable security definer set search_path = public as $$
  select s.number || ' ' || s.name
    from public.student_sessions ss join public.students s on s.id = ss.student_id
   where ss.uid = auth.uid();
$$;

-- 학생 글을 친구가 볼 수 있는 활동인가 (‘선생님만 보기’ 활동이면 안 됨)
create or replace function public.room_open_to_peers(p_room text) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select r.data ->> 'reveal' from public.docs r where r.col = 'rooms' and r.id = p_room), 'after') <> 'teacher';
$$;

-- 지금 접속한 사람이 누구인지 (앱이 처음에 한 번 묻는다)
create or replace function public.whoami() returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'teacher', public.is_teacher(),
    'email', case when coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) then null else auth.jwt() ->> 'email' end,
    'student_name', public.my_student_name());
$$;

-- 학생: 학번·이름·코드가 맞으면 이 기기를 그 학생으로 연결한다
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
  insert into public.student_sessions (uid, student_id) values (auth.uid(), s.id)
  on conflict (uid) do update set student_id = excluded.student_id, created_at = now();
  return json_build_object('id', s.id, 'name', s.number || ' ' || s.name);
end $$;

-- 문서 일부만 고치기 (권한 검사는 표의 규칙을 그대로 따른다)
create or replace function public.doc_merge(p_col text, p_id text, p_patch jsonb) returns void
language sql volatile security invoker set search_path = public as $$
  update public.docs set data = data || p_patch where col = p_col and id = p_id;
$$;

revoke all on function public.claim_student(text, text, text) from public;
grant execute on function public.claim_student(text, text, text) to authenticated;
grant execute on function public.whoami() to authenticated;
grant execute on function public.doc_merge(text, text, jsonb) to authenticated;
grant execute on function public.is_teacher(), public.my_student(), public.my_student_name(), public.room_open_to_peers(text) to authenticated;

-- 저장할 때 서버가 주인·활동·시각을 채운다 (학생이 남의 것으로 꾸밀 수 없게)
create or replace function public.docs_stamp() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.room_id := new.data ->> 'roomId';
  new.updated_at := now();
  if tg_op = 'INSERT' then
    new.owner := case when public.is_teacher() then null else public.my_student() end;
    new.created_at := now();
  else
    new.owner := old.owner;
    new.created_at := old.created_at;
  end if;
  return new;
end $$;
drop trigger if exists docs_stamp on public.docs;
create trigger docs_stamp before insert or update on public.docs
  for each row execute function public.docs_stamp();

-- ---------------------------------------------------------------------
-- 규칙 (Row Level Security)
-- ---------------------------------------------------------------------
drop policy if exists docs_read   on public.docs;
drop policy if exists docs_insert on public.docs;
drop policy if exists docs_update on public.docs;
drop policy if exists docs_delete on public.docs;

create policy docs_read on public.docs for select to authenticated using (
  public.is_teacher()
  or col in ('rooms', 'courses', 'config', 'treplies')
  or (col = 'posts'   and (owner = public.my_student()
                           or (public.my_student() is not null and public.room_open_to_peers(room_id))))
  or (col = 'replies' and public.my_student() is not null)
);

create policy docs_insert on public.docs for insert to authenticated with check (
  public.is_teacher()
  or (col in ('posts', 'replies')
      and public.my_student() is not null
      and owner = public.my_student()
      and data ->> 'author' = public.my_student_name()
      and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
);

create policy docs_update on public.docs for update to authenticated
  using (public.is_teacher() or (col in ('posts', 'replies') and owner = public.my_student()))
  with check (
    public.is_teacher()
    or (col in ('posts', 'replies')
        and owner = public.my_student()
        and data ->> 'author' = public.my_student_name()
        and coalesce(data ->> 'kind', '') not in ('teacher', 'class'))
  );

create policy docs_delete on public.docs for delete to authenticated using (public.is_teacher());

-- 학생 명단·코드: 교사만
drop policy if exists students_teacher on public.students;
create policy students_teacher on public.students for all to authenticated
  using (public.is_teacher()) with check (public.is_teacher());
-- teachers, student_sessions: 정책 없음 = 앱에서 직접 읽고 쓸 수 없음 (함수만 사용)

-- 실시간 반영 켜기
do $$ begin
  begin
    alter publication supabase_realtime add table public.docs;
  exception when duplicate_object then null; when undefined_object then null;
  end;
end $$;

-- =====================================================================
-- 마지막으로 교사 구글 계정을 등록하세요 (따옴표 안을 바꿔서 실행)
-- insert into public.teachers (email) values ('teacher@example.com') on conflict do nothing;
-- =====================================================================
