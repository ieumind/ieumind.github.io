-- =====================================================================
-- 💬 실시간 토론 채팅 (2026-11-09)
--   기존 docs·학생·게스트 구조는 그대로 두고, 토론 채팅에만 쓰는 표 3개와 서버 함수를 더한다.
--   · 학생끼리는 실명을 볼 수 없다: 메시지에는 닉네임·팀만 저장하고, 실명 연결표(debate_members)는 교사만 본다.
--   · 학생은 표에 직접 쓰지 못하고 서버 함수로만 쓴다(토론 상태·참여 제한·글자 수·도배를 서버가 확인).
--   · 토론 상태는 활동 문서(docs rooms)의 data.live.state 에 둔다: wait → live → ended → vote → result
-- =====================================================================

create table if not exists public.debate_members (
  room_id   text not null,
  mkey      text not null,               -- 's:학생id'(명단 학생) 또는 'g:로그인id'(이름만 넣은 참가자) — 한 학생은 기기가 달라도 한 명
  tid       uuid not null,               -- 활동을 만든 선생님
  uid       uuid not null,               -- 처음 들어온 기기
  real_name text not null,               -- 교사만 본다
  nick      text not null,               -- 학생에게 보이는 익명 닉네임
  team      text check (team in ('pro', 'con')),   -- null = 팀 배정 대기
  muted     boolean not null default false,
  joined_at timestamptz not null default now(),
  primary key (room_id, mkey)
);
create unique index if not exists debate_members_nick on public.debate_members (room_id, nick);
create index if not exists debate_members_tid on public.debate_members (tid);

create table if not exists public.debate_msgs (
  id         bigint generated always as identity primary key,   -- 서버가 매기는 순서 번호
  room_id    text not null,
  tid        uuid not null,
  mkey       text not null,
  nick       text not null,
  team       text not null check (team in ('pro', 'con')),
  body       text not null,
  deleted    boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists debate_msgs_room on public.debate_msgs (room_id, id);
create index if not exists debate_msgs_rate on public.debate_msgs (room_id, mkey, created_at);

create table if not exists public.debate_votes (
  room_id    text not null,
  mkey       text not null,
  tid        uuid not null,
  choice     text not null check (choice in ('pro', 'con')),
  created_at timestamptz not null default now(),
  primary key (room_id, mkey)             -- 한 사람 한 표
);

alter table public.debate_members enable row level security;
alter table public.debate_msgs    enable row level security;
alter table public.debate_votes   enable row level security;
revoke all on public.debate_members, public.debate_msgs, public.debate_votes from public, anon, authenticated;
grant select on public.debate_members, public.debate_msgs, public.debate_votes to authenticated;
grant update (team, muted) on public.debate_members to authenticated;          -- 교사만(정책에서 확인)
grant update (deleted, body) on public.debate_msgs to authenticated;             -- 교사만(정책에서 확인)
grant delete on public.debate_members to authenticated;                          -- 교사만(정책에서 확인)

-- 이 기기 사용자가 그 토론에서 누구인지 (명단 학생 → 게스트 순서)
create or replace function public.debate_mkey(p_room text, p_tid uuid) returns text
language sql stable security definer set search_path = public as $$
  select case
    when public.my_student(p_tid) is not null and public.room_for_me(p_room, p_tid) then 's:' || public.my_student(p_tid)::text
    when public.guest_in(p_room) and public.room_is_free(p_room) then 'g:' || auth.uid()::text
  end;
$$;
create or replace function public.debate_room(p_room text) returns public.docs
language sql stable security definer set search_path = public as $$
  select r.* from public.docs r where r.col = 'rooms' and r.id = p_room and r.data ->> 'template' = 'live' limit 1;
$$;
create or replace function public.debate_is_member(p_room text, p_tid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.debate_members m where m.room_id = p_room and m.mkey = public.debate_mkey(p_room, p_tid));
$$;

drop policy if exists debate_members_read on public.debate_members;
create policy debate_members_read on public.debate_members for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or mkey = public.debate_mkey(room_id, tid));
drop policy if exists debate_members_teacher_upd on public.debate_members;
create policy debate_members_teacher_upd on public.debate_members for update to authenticated
  using (public.is_teacher() and tid = auth.uid()) with check (public.is_teacher() and tid = auth.uid());
drop policy if exists debate_members_teacher_del on public.debate_members;
create policy debate_members_teacher_del on public.debate_members for delete to authenticated
  using (public.is_teacher() and tid = auth.uid());

drop policy if exists debate_msgs_read on public.debate_msgs;
create policy debate_msgs_read on public.debate_msgs for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or public.debate_is_member(room_id, tid));
drop policy if exists debate_msgs_teacher_upd on public.debate_msgs;
create policy debate_msgs_teacher_upd on public.debate_msgs for update to authenticated
  using (public.is_teacher() and tid = auth.uid()) with check (public.is_teacher() and tid = auth.uid());

drop policy if exists debate_votes_read on public.debate_votes;
create policy debate_votes_read on public.debate_votes for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or mkey = public.debate_mkey(room_id, tid));

-- 들어오기: 닉네임을 겹치지 않게 만들고, ‘자동 배정’이면 인원이 적은 팀에 넣는다
create or replace function public.debate_join(p_room text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; k text; nm text; m public.debate_members; v_nick text; v_team text; np int; nc int; i int := 0;
  pre text[] := array['논객', '역사탐정', '기록자', '탐구자', '사관', '관찰자', '해설자', '질문가'];
begin
  r := public.debate_room(p_room);
  if r.id is null or coalesce(r.data ->> 'status', 'open') in ('draft', 'archived') or not public.tid_active(r.tid) then
    return json_build_object('ok', false, 'reason', 'denied'); end if;
  k := public.debate_mkey(p_room, r.tid);
  if k is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = k;
  if found then return json_build_object('ok', true, 'nick', m.nick, 'team', m.team, 'muted', m.muted, 'mkey', m.mkey); end if;
  nm := case when k like 's:%' then public.my_student_name(r.tid) else public.my_guest_name(p_room) end;
  if (select count(*) from public.debate_members where room_id = p_room) >= 300 then return json_build_object('ok', false, 'reason', 'full'); end if;
  loop
    i := i + 1;
    v_nick := pre[1 + floor(random() * array_length(pre, 1))::int] || lpad((floor(random() * (case when i < 20 then 100 else 1000 end)))::int::text, 2, '0');
    exit when not exists (select 1 from public.debate_members where room_id = p_room and nick = v_nick) or i > 60;
  end loop;
  if coalesce(r.data -> 'liveCfg' ->> 'teamMode', 'auto') = 'auto' then
    select count(*) filter (where team = 'pro'), count(*) filter (where team = 'con') into np, nc from public.debate_members where room_id = p_room;
    v_team := case when np < nc then 'pro' when nc < np then 'con' when random() < .5 then 'pro' else 'con' end;
  end if;
  begin
    insert into public.debate_members (room_id, mkey, tid, uid, real_name, nick, team)
      values (p_room, k, r.tid, auth.uid(), coalesce(nm, '이름 없음'), v_nick, v_team);
  exception when unique_violation then
    select * into m from public.debate_members where room_id = p_room and mkey = k;
    if found then return json_build_object('ok', true, 'nick', m.nick, 'team', m.team, 'muted', m.muted, 'mkey', m.mkey); end if;
    return json_build_object('ok', false, 'reason', 'retry');
  end;
  return json_build_object('ok', true, 'nick', v_nick, 'team', v_team, 'muted', false, 'mkey', k);
end $$;

-- 메시지 보내기: 토론 중(live)·팀 배정됨·참여 제한 아님·200자 이하·3초에 1개·1분에 10개
create or replace function public.debate_send(p_room text, p_body text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_id bigint;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'live' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if m.team is null then return json_build_object('ok', false, 'reason', 'noteam'); end if;
  if m.muted then return json_build_object('ok', false, 'reason', 'muted'); end if;
  b := regexp_replace(trim(coalesce(p_body, '')), '[\x01-\x09\x0b-\x1f\x7f]', '', 'g');
  b := regexp_replace(b, '\n{3,}', E'\n\n', 'g');
  if char_length(b) < 1 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  if char_length(b) > 200 then return json_build_object('ok', false, 'reason', 'long'); end if;
  if exists (select 1 from public.debate_msgs where room_id = p_room and mkey = m.mkey and created_at > now() - interval '3 seconds') then
    return json_build_object('ok', false, 'reason', 'fast'); end if;
  if (select count(*) from public.debate_msgs where room_id = p_room and mkey = m.mkey and created_at > now() - interval '60 seconds') >= 10 then
    return json_build_object('ok', false, 'reason', 'many'); end if;
  insert into public.debate_msgs (room_id, tid, mkey, nick, team, body) values (p_room, r.tid, m.mkey, m.nick, m.team, b) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- 최종 투표: 투표 중(vote)일 때 한 사람 한 번
create or replace function public.debate_vote(p_room text, p_choice text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; k text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  k := public.debate_mkey(p_room, r.tid);
  if k is null or not exists (select 1 from public.debate_members where room_id = p_room and mkey = k) then
    return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'vote' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if p_choice not in ('pro', 'con') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  insert into public.debate_votes (room_id, mkey, tid, choice) values (p_room, k, r.tid, p_choice) on conflict do nothing;
  if not found then return json_build_object('ok', false, 'reason', 'dup'); end if;
  return json_build_object('ok', true);
end $$;

-- 투표 결과: 교사는 언제나, 참여 학생은 결과 공개(result) 뒤에만
create or replace function public.debate_result(p_room text) returns json
language plpgsql stable security definer set search_path = public as $$
declare r public.docs;
begin
  r := public.debate_room(p_room);
  if r.id is null then return null; end if;
  if not ((public.is_teacher() and r.tid = auth.uid())
          or (coalesce(r.data -> 'live' ->> 'state', '') = 'result' and public.debate_is_member(p_room, r.tid))) then return null; end if;
  return (select json_build_object('pro', count(*) filter (where choice = 'pro'), 'con', count(*) filter (where choice = 'con'))
            from public.debate_votes where room_id = p_room);
end $$;

-- 교사: 활동을 지울 때 토론 기록도 함께 지운다
create or replace function public.debate_purge(p_room text) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  delete from public.debate_msgs    where room_id = p_room and tid = auth.uid();
  delete from public.debate_votes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_members where room_id = p_room and tid = auth.uid();
end $$;

revoke execute on function public.debate_mkey(text, uuid), public.debate_room(text), public.debate_is_member(text, uuid),
  public.debate_join(text), public.debate_send(text, text), public.debate_vote(text, text), public.debate_result(text), public.debate_purge(text) from public, anon, authenticated;
grant execute on function public.debate_mkey(text, uuid), public.debate_is_member(text, uuid),
  public.debate_join(text), public.debate_send(text, text), public.debate_vote(text, text), public.debate_result(text), public.debate_purge(text) to authenticated;
-- debate_room 은 서버 함수 안에서만 쓴다(다른 선생님 활동 내용을 직접 꺼내 보지 못하게) — 위에서 authenticated 권한도 뺐다

do $$ begin
  begin alter publication supabase_realtime add table public.debate_members; exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.debate_msgs;    exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.debate_votes;   exception when duplicate_object then null; end;
end $$;

-- 토론 자료 파일(PDF·한글·워드·PPT·엑셀·텍스트)을 자료 사진과 같은 공개 보관함(materials)에 올릴 수 있게 한다 (교사만 올림 · 5MB)
update storage.buckets set allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp',
  'application/pdf', 'application/x-hwp', 'application/hwp+zip', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain']
 where id = 'materials';
