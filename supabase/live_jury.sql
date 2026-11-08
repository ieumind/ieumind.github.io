-- =====================================================================
-- ⚖️ 실시간 토론 채팅 · 청중 판정단 (2026-11-09)
--   live_debate.sql 위에 더한다. 기존 표·함수를 지우지 않고, 참여 역할 'jury' 하나와 판정 표 1개만 추가한다.
--   · 판정단 = debate_members.team 이 'jury' 인 참여자: 채팅은 읽기만(서버가 글쓰기·최종 투표를 막음)
--   · 판정 = 세 기준(근거·설득력·반박)마다 찬성/반대 + 이유. 한 사람 한 번, 투표 단계(vote)에서만
--   · 결과는 교사는 언제나, 학생은 결과 공개(result) 뒤에만
--   · 활동 설정 data.liveCfg.jury = 0 | 10 | 20 | 30 (자동 배정 때 판정단 비율 %, 0은 사용 안 함)
-- =====================================================================

alter table public.debate_members drop constraint if exists debate_members_team_check;
alter table public.debate_members add constraint debate_members_team_check check (team in ('pro', 'con', 'jury'));

create table if not exists public.debate_jury (
  id         bigint generated always as identity primary key,
  room_id    text not null,
  mkey       text not null,
  tid        uuid not null,
  c1         text not null check (c1 in ('pro', 'con')),   -- 역사적 근거의 타당성
  c2         text not null check (c2 in ('pro', 'con')),   -- 논리적 설득력
  c3         text not null check (c3 in ('pro', 'con')),   -- 반박의 적절성
  reason     text not null,
  hidden     boolean not null default false,               -- 교사가 결과 화면에서 가린 의견
  created_at timestamptz not null default now(),
  unique (room_id, mkey)                                    -- 한 사람 한 번
);
create index if not exists debate_jury_tid on public.debate_jury (tid);
alter table public.debate_jury enable row level security;
revoke all on public.debate_jury from public, anon, authenticated;
grant select on public.debate_jury to authenticated;
grant update (hidden) on public.debate_jury to authenticated;                    -- 교사만(정책에서 확인)
grant delete on public.debate_jury to authenticated;

drop policy if exists debate_jury_read on public.debate_jury;
create policy debate_jury_read on public.debate_jury for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or mkey = public.debate_mkey(room_id, tid));
drop policy if exists debate_jury_teacher_upd on public.debate_jury;
create policy debate_jury_teacher_upd on public.debate_jury for update to authenticated
  using (public.is_teacher() and tid = auth.uid()) with check (public.is_teacher() and tid = auth.uid());

-- 들어오기: 자동 배정이고 판정단 비율이 있으면, 부족할 때 판정단으로 먼저 넣고 나머지는 인원이 적은 팀에 넣는다
create or replace function public.debate_join(p_room text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; k text; nm text; m public.debate_members; v_nick text; v_team text; np int; nc int; nj int; tot int; pct int; i int := 0;
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
    select count(*) filter (where team = 'pro'), count(*) filter (where team = 'con'), count(*) filter (where team = 'jury'), count(*)
      into np, nc, nj, tot from public.debate_members where room_id = p_room;
    pct := case when (r.data -> 'liveCfg' ->> 'jury') in ('10', '20', '30') then (r.data -> 'liveCfg' ->> 'jury')::int else 0 end;
    if pct > 0 and nj < round((tot + 1) * pct / 100.0) then v_team := 'jury';
    else v_team := case when np < nc then 'pro' when nc < np then 'con' when random() < .5 then 'pro' else 'con' end; end if;
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

-- 메시지 보내기: 판정단은 읽기만 (나머지 규칙은 그대로)
create or replace function public.debate_send(p_room text, p_body text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_id bigint;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if m.team = 'jury' then return json_build_object('ok', false, 'reason', 'jury'); end if;
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

-- 최종 투표: 판정단은 투표 대신 판정으로 참여한다 (두 결과가 섞이지 않게)
create or replace function public.debate_vote(p_room text, p_choice text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; k text; t text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  k := public.debate_mkey(p_room, r.tid);
  select team into t from public.debate_members where room_id = p_room and mkey = k;
  if k is null or not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if t = 'jury' then return json_build_object('ok', false, 'reason', 'jury'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'vote' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if p_choice not in ('pro', 'con') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  insert into public.debate_votes (room_id, mkey, tid, choice) values (p_room, k, r.tid, p_choice) on conflict do nothing;
  if not found then return json_build_object('ok', false, 'reason', 'dup'); end if;
  return json_build_object('ok', true);
end $$;

-- 판정 제출: 판정단만 · 투표 단계(vote)에서만 · 한 번 · 이유 5~300자
create or replace function public.debate_judge(p_room text, p_c1 text, p_c2 text, p_c3 text, p_reason text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found or m.team is distinct from 'jury' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'vote' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if p_c1 not in ('pro', 'con') or p_c2 not in ('pro', 'con') or p_c3 not in ('pro', 'con') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  b := regexp_replace(trim(coalesce(p_reason, '')), '[\x01-\x09\x0b-\x1f\x7f]', '', 'g');
  b := regexp_replace(b, '\n{3,}', E'\n\n', 'g');
  if char_length(b) < 5 then return json_build_object('ok', false, 'reason', 'short'); end if;
  if char_length(b) > 300 then return json_build_object('ok', false, 'reason', 'long'); end if;
  insert into public.debate_jury (room_id, mkey, tid, c1, c2, c3, reason) values (p_room, m.mkey, r.tid, p_c1, p_c2, p_c3, b) on conflict do nothing;
  if not found then return json_build_object('ok', false, 'reason', 'dup'); end if;
  return json_build_object('ok', true);
end $$;

-- 결과: 최종 투표(pro, con)와 판정(jury)을 따로 돌려준다. 교사는 언제나, 학생은 결과 공개(result) 뒤에만
create or replace function public.debate_result(p_room text) returns json
language plpgsql stable security definer set search_path = public as $$
declare r public.docs; v_t boolean; jr json;
begin
  r := public.debate_room(p_room);
  if r.id is null then return null; end if;
  v_t := public.is_teacher() and r.tid = auth.uid();
  if not (v_t or (coalesce(r.data -> 'live' ->> 'state', '') = 'result' and public.debate_is_member(p_room, r.tid))) then return null; end if;
  select json_build_object(
      'n', count(*),
      'c1', json_build_object('pro', count(*) filter (where c1 = 'pro'), 'con', count(*) filter (where c1 = 'con')),
      'c2', json_build_object('pro', count(*) filter (where c2 = 'pro'), 'con', count(*) filter (where c2 = 'con')),
      'c3', json_build_object('pro', count(*) filter (where c3 = 'pro'), 'con', count(*) filter (where c3 = 'con')),
      'win', json_build_object(
        'pro', count(*) filter (where (c1 = 'pro')::int + (c2 = 'pro')::int + (c3 = 'pro')::int >= 2),
        'con', count(*) filter (where (c1 = 'con')::int + (c2 = 'con')::int + (c3 = 'con')::int >= 2)),
      'reasons', coalesce(json_agg(json_build_object('id', id, 'reason', reason, 'hidden', hidden) order by id) filter (where v_t or not hidden), '[]'::json))
    into jr from public.debate_jury where room_id = p_room;
  return json_build_object(
    'pro', (select count(*) from public.debate_votes where room_id = p_room and choice = 'pro'),
    'con', (select count(*) from public.debate_votes where room_id = p_room and choice = 'con'),
    'jury', jr);
end $$;

create or replace function public.debate_purge(p_room text) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  delete from public.debate_msgs    where room_id = p_room and tid = auth.uid();
  delete from public.debate_votes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_jury    where room_id = p_room and tid = auth.uid();
  delete from public.debate_members where room_id = p_room and tid = auth.uid();
end $$;

revoke execute on function public.debate_judge(text, text, text, text, text) from public, anon, authenticated;
grant execute on function public.debate_judge(text, text, text, text, text) to authenticated;
revoke execute on function public.debate_join(text), public.debate_send(text, text), public.debate_vote(text, text), public.debate_result(text), public.debate_purge(text) from public, anon;
grant execute on function public.debate_join(text), public.debate_send(text, text), public.debate_vote(text, text), public.debate_result(text), public.debate_purge(text) to authenticated;

do $$ begin
  begin alter publication supabase_realtime add table public.debate_jury; exception when duplicate_object then null; end;
end $$;
-- (대기실·직접 닉네임·판정단 의견: supabase/live_lobby.sql 을 이어서 실행)
