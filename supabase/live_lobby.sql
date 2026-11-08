-- =====================================================================
-- 🚪 실시간 토론 · 대기실·역할 이동·직접 닉네임·판정단 의견 (2026-11-09c)
--   live_debate.sql · live_jury.sql 위에 더한다.
--   · 들어오면 모두 '판정단'(대기실). 학생이 찬성/반대로 스스로 옮기거나(팀당 최대 N명, 기본 4) 교사가 직접 지정한다. 대기 단계(wait)에서만 학생 이동 가능.
--   · 닉네임: liveCfg.nickMode = 'auto'(찬성01·반대01·판정단01, 역할이 바뀌면 새로 부여) | 'custom'(대기 단계에서 학생이 직접 정함, 2~8자·중복 불가)
--   · 판정단 의견(debate_notes): 판정단만 쓰고(질문/생각), 토론방 모든 참여자가 실시간으로 본다. 토론 중·종료 후·투표 중에 쓸 수 있다.
--   · 판정 제출 = 최종 투표: 세 기준 + 종합(c4) + 이유. liveCfg.noteMin(0~2, 기본 1)개 이상 의견을 써야 제출된다.
--     판정단이 없는 토론(전원 토론자)에서만 토론자가 직접 최종 투표를 한다.
-- =====================================================================

alter table public.debate_members add column if not exists nick_set boolean not null default false;
alter table public.debate_jury add column if not exists c4 text check (c4 in ('pro', 'con'));

create table if not exists public.debate_notes (
  id         bigint generated always as identity primary key,
  room_id    text not null,
  tid        uuid not null,
  mkey       text not null,
  nick       text not null,
  kind       text not null check (kind in ('q', 't')),          -- 질문 / 생각
  target     text not null check (target in ('pro', 'con', 'all')),
  body       text not null,
  deleted    boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists debate_notes_room on public.debate_notes (room_id, id);
alter table public.debate_notes enable row level security;
revoke all on public.debate_notes from public, anon, authenticated;
grant select on public.debate_notes to authenticated;
grant update (deleted, body) on public.debate_notes to authenticated;           -- 교사만(정책에서 확인)
drop policy if exists debate_notes_read on public.debate_notes;
create policy debate_notes_read on public.debate_notes for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or public.debate_is_member(room_id, tid));
drop policy if exists debate_notes_teacher_upd on public.debate_notes;
create policy debate_notes_teacher_upd on public.debate_notes for update to authenticated
  using (public.is_teacher() and tid = auth.uid()) with check (public.is_teacher() and tid = auth.uid());

-- 역할에 맞는 새 닉네임 (찬성01 · 반대01 · 판정단01 … 비어 있는 가장 작은 번호). 서버 함수 안에서만 쓴다
create or replace function public.debate_nick_gen(p_room text, p_team text) returns text
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; pfx text; n int := 0; cand text;
begin
  r := public.debate_room(p_room);
  pfx := case p_team
    when 'pro' then coalesce(nullif(left(trim(r.data -> 'stances' ->> 0), 4), ''), '찬성')
    when 'con' then coalesce(nullif(left(trim(r.data -> 'stances' ->> 1), 4), ''), '반대')
    else '판정단' end;
  loop
    n := n + 1; cand := pfx || lpad(n::text, 2, '0');
    exit when not exists (select 1 from public.debate_members where room_id = p_room and nick = cand);
  end loop;
  return cand;
end $$;

-- 들어오기: 누구나 '판정단'(대기실)으로 시작한다
create or replace function public.debate_join(p_room text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; k text; nm text; m public.debate_members; v_nick text;
begin
  r := public.debate_room(p_room);
  if r.id is null or coalesce(r.data ->> 'status', 'open') in ('draft', 'archived') or not public.tid_active(r.tid) then
    return json_build_object('ok', false, 'reason', 'denied'); end if;
  k := public.debate_mkey(p_room, r.tid);
  if k is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  perform pg_advisory_xact_lock(hashtext('debate:' || p_room));
  select * into m from public.debate_members where room_id = p_room and mkey = k;
  if found then return json_build_object('ok', true, 'nick', m.nick, 'team', m.team, 'muted', m.muted, 'mkey', m.mkey); end if;
  nm := case when k like 's:%' then public.my_student_name(r.tid) else public.my_guest_name(p_room) end;
  if (select count(*) from public.debate_members where room_id = p_room) >= 300 then return json_build_object('ok', false, 'reason', 'full'); end if;
  v_nick := public.debate_nick_gen(p_room, 'jury');
  insert into public.debate_members (room_id, mkey, tid, uid, real_name, nick, team)
    values (p_room, k, r.tid, auth.uid(), coalesce(nm, '이름 없음'), v_nick, 'jury');
  return json_build_object('ok', true, 'nick', v_nick, 'team', 'jury', 'muted', false, 'mkey', k);
end $$;

-- 학생이 스스로 역할 옮기기: 대기 단계(wait)만 · 교사가 허용했을 때만 · 찬성/반대는 팀당 최대 N명
create or replace function public.debate_move(p_room text, p_team text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; n int; cfg jsonb; v_nick text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if p_team not in ('pro', 'con', 'jury') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  perform pg_advisory_xact_lock(hashtext('debate:' || p_room));
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'wait' then return json_build_object('ok', false, 'reason', 'locked'); end if;
  cfg := coalesce(r.data -> 'liveCfg', '{}'::jsonb);
  if cfg ->> 'selfMove' = 'false' then return json_build_object('ok', false, 'reason', 'selfoff'); end if;
  if m.team is not distinct from p_team then return json_build_object('ok', true, 'nick', m.nick, 'team', m.team); end if;
  if p_team in ('pro', 'con') then
    n := case when cfg ->> 'teamN' ~ '^\d+$' then least(greatest((cfg ->> 'teamN')::int, 1), 10) else 4 end;
    if (select count(*) from public.debate_members where room_id = p_room and team = p_team) >= n then
      return json_build_object('ok', false, 'reason', 'full'); end if;
  end if;
  v_nick := case when cfg ->> 'nickMode' = 'custom' and m.nick_set then m.nick else public.debate_nick_gen(p_room, p_team) end;
  update public.debate_members set team = p_team, nick = v_nick where room_id = p_room and mkey = m.mkey;
  return json_build_object('ok', true, 'nick', v_nick, 'team', p_team);
end $$;

-- 교사가 역할을 직접 정하기 (언제든 · 인원 제한 없음)
create or replace function public.debate_assign(p_room text, p_mkey text, p_team text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; cfg jsonb; v_nick text;
begin
  r := public.debate_room(p_room);
  if r.id is null or not public.is_teacher() or r.tid <> auth.uid() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if p_team not in ('pro', 'con', 'jury') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  perform pg_advisory_xact_lock(hashtext('debate:' || p_room));
  select * into m from public.debate_members where room_id = p_room and mkey = p_mkey;
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if m.team is not distinct from p_team then return json_build_object('ok', true, 'nick', m.nick, 'team', m.team); end if;
  cfg := coalesce(r.data -> 'liveCfg', '{}'::jsonb);
  v_nick := case when cfg ->> 'nickMode' = 'custom' and m.nick_set then m.nick else public.debate_nick_gen(p_room, p_team) end;
  update public.debate_members set team = p_team, nick = v_nick where room_id = p_room and mkey = p_mkey;
  return json_build_object('ok', true, 'nick', v_nick, 'team', p_team);
end $$;

-- 직접 닉네임: nickMode 가 custom 일 때 · 대기 단계에서만 · 2~8자(한글·영문·숫자·_·-) · 중복·실명·역할 이름 흉내 불가
create or replace function public.debate_nick(p_room text, p_nick text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; n text; p1 text; p2 text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  perform pg_advisory_xact_lock(hashtext('debate:' || p_room));
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'liveCfg' ->> 'nickMode', 'auto') <> 'custom' then return json_build_object('ok', false, 'reason', 'mode'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'wait' then return json_build_object('ok', false, 'reason', 'locked'); end if;
  n := trim(coalesce(p_nick, ''));
  if char_length(n) < 2 or char_length(n) > 8 or n !~ '^[가-힣A-Za-z0-9_·-]+$' then return json_build_object('ok', false, 'reason', 'bad'); end if;
  p1 := coalesce(nullif(left(trim(r.data -> 'stances' ->> 0), 4), ''), '찬성'); p2 := coalesce(nullif(left(trim(r.data -> 'stances' ->> 1), 4), ''), '반대');
  if n ~ ('^(판정단|' || regexp_replace(p1, '[^가-힣A-Za-z0-9]', '', 'g') || '|' || regexp_replace(p2, '[^가-힣A-Za-z0-9]', '', 'g') || ')[0-9]+$') then
    return json_build_object('ok', false, 'reason', 'reserved'); end if;
  if exists (select 1 from public.debate_members where room_id = p_room and real_name = n) then return json_build_object('ok', false, 'reason', 'real'); end if;
  begin
    update public.debate_members set nick = n, nick_set = true where room_id = p_room and mkey = m.mkey;
  exception when unique_violation then return json_build_object('ok', false, 'reason', 'dup'); end;
  return json_build_object('ok', true, 'nick', n);
end $$;

-- 교사: 부적절한 닉네임을 역할에 맞는 자동 닉네임으로 되돌리기
create or replace function public.debate_nick_reset(p_room text, p_mkey text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; v_nick text;
begin
  r := public.debate_room(p_room);
  if r.id is null or not public.is_teacher() or r.tid <> auth.uid() then return json_build_object('ok', false, 'reason', 'denied'); end if;
  perform pg_advisory_xact_lock(hashtext('debate:' || p_room));
  select * into m from public.debate_members where room_id = p_room and mkey = p_mkey;
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  v_nick := public.debate_nick_gen(p_room, coalesce(m.team, 'jury'));
  update public.debate_members set nick = v_nick, nick_set = false where room_id = p_room and mkey = p_mkey;
  return json_build_object('ok', true, 'nick', v_nick);
end $$;

-- 대기실 명단: 닉네임과 역할만 (실명 없음). 교사와 그 토론 참여자만
create or replace function public.debate_roster(p_room text) returns json
language plpgsql stable security definer set search_path = public as $$
declare r public.docs;
begin
  r := public.debate_room(p_room);
  if r.id is null then return null; end if;
  if not ((public.is_teacher() and r.tid = auth.uid()) or public.debate_is_member(p_room, r.tid)) then return null; end if;
  return (select coalesce(json_agg(json_build_object('nick', nick, 'team', team) order by team, nick), '[]'::json) from public.debate_members where room_id = p_room);
end $$;

-- 판정단 의견: 판정단만 · 토론 중/종료 후/투표 중 · 100자 · 3초에 1개 · 한 사람 20개까지
create or replace function public.debate_note(p_room text, p_kind text, p_target text, p_body text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_id bigint;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found or m.team is distinct from 'jury' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') not in ('live', 'ended', 'vote') then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if m.muted then return json_build_object('ok', false, 'reason', 'muted'); end if;
  if p_kind not in ('q', 't') or p_target not in ('pro', 'con', 'all') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  b := regexp_replace(trim(coalesce(p_body, '')), '[\x01-\x09\x0b-\x1f\x7f]', '', 'g');
  b := regexp_replace(b, '\n{2,}', E'\n', 'g');
  if char_length(b) < 1 then return json_build_object('ok', false, 'reason', 'empty'); end if;
  if char_length(b) > 100 then return json_build_object('ok', false, 'reason', 'long'); end if;
  if exists (select 1 from public.debate_notes where room_id = p_room and mkey = m.mkey and created_at > now() - interval '3 seconds') then
    return json_build_object('ok', false, 'reason', 'fast'); end if;
  if (select count(*) from public.debate_notes where room_id = p_room and mkey = m.mkey) >= 20 then return json_build_object('ok', false, 'reason', 'many'); end if;
  insert into public.debate_notes (room_id, tid, mkey, nick, kind, target, body) values (p_room, r.tid, m.mkey, m.nick, p_kind, p_target, b) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- 토론자 최종 투표: 판정단이 있으면 판정단의 판정이 최종 투표다 (판정단이 없는 토론에서만 토론자가 투표)
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
  if exists (select 1 from public.debate_members where room_id = p_room and team = 'jury') then return json_build_object('ok', false, 'reason', 'byjury'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'vote' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if p_choice not in ('pro', 'con') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  insert into public.debate_votes (room_id, mkey, tid, choice) values (p_room, k, r.tid, p_choice) on conflict do nothing;
  if not found then return json_build_object('ok', false, 'reason', 'dup'); end if;
  return json_build_object('ok', true);
end $$;

-- 판정 제출(= 최종 투표): 세 기준 + 종합 + 이유. 판정단만 · 투표 단계만 · 1회 · 의견 최소 개수 확인
drop function if exists public.debate_judge(text, text, text, text, text);
create or replace function public.debate_judge(p_room text, p_c1 text, p_c2 text, p_c3 text, p_c4 text, p_reason text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_min int;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found or m.team is distinct from 'jury' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') <> 'vote' then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if p_c1 not in ('pro', 'con') or p_c2 not in ('pro', 'con') or p_c3 not in ('pro', 'con') or p_c4 not in ('pro', 'con') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  b := regexp_replace(trim(coalesce(p_reason, '')), '[\x01-\x09\x0b-\x1f\x7f]', '', 'g');
  b := regexp_replace(b, '\n{3,}', E'\n\n', 'g');
  if char_length(b) < 5 then return json_build_object('ok', false, 'reason', 'short'); end if;
  if char_length(b) > 300 then return json_build_object('ok', false, 'reason', 'long'); end if;
  v_min := case when (r.data -> 'liveCfg' ->> 'noteMin') in ('0', '1', '2') then (r.data -> 'liveCfg' ->> 'noteMin')::int else 1 end;
  if (select count(*) from public.debate_notes where room_id = p_room and mkey = m.mkey and not deleted) < v_min then
    return json_build_object('ok', false, 'reason', 'notes', 'need', v_min); end if;
  insert into public.debate_jury (room_id, mkey, tid, c1, c2, c3, c4, reason) values (p_room, m.mkey, r.tid, p_c1, p_c2, p_c3, p_c4, b) on conflict do nothing;
  if not found then return json_build_object('ok', false, 'reason', 'dup'); end if;
  return json_build_object('ok', true);
end $$;

-- 결과: pro/con = 최종 투표(판정단의 종합 + 판정단이 없는 토론의 토론자 투표), jury = 세 기준 판정
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
      'c4', json_build_object('pro', count(*) filter (where c4 = 'pro'), 'con', count(*) filter (where c4 = 'con')),
      'win', json_build_object(
        'pro', count(*) filter (where (c1 = 'pro')::int + (c2 = 'pro')::int + (c3 = 'pro')::int >= 2),
        'con', count(*) filter (where (c1 = 'con')::int + (c2 = 'con')::int + (c3 = 'con')::int >= 2)),
      'reasons', coalesce(json_agg(json_build_object('id', id, 'reason', reason, 'hidden', hidden) order by id) filter (where v_t or not hidden), '[]'::json))
    into jr from public.debate_jury where room_id = p_room;
  return json_build_object(
    'pro', (select count(*) from public.debate_votes where room_id = p_room and choice = 'pro') + (select count(*) from public.debate_jury where room_id = p_room and c4 = 'pro'),
    'con', (select count(*) from public.debate_votes where room_id = p_room and choice = 'con') + (select count(*) from public.debate_jury where room_id = p_room and c4 = 'con'),
    'jury', jr);
end $$;

create or replace function public.debate_purge(p_room text) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  delete from public.debate_msgs    where room_id = p_room and tid = auth.uid();
  delete from public.debate_notes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_votes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_jury    where room_id = p_room and tid = auth.uid();
  delete from public.debate_members where room_id = p_room and tid = auth.uid();
end $$;

revoke execute on function public.debate_nick_gen(text, text) from public, anon, authenticated;
revoke execute on function public.debate_join(text), public.debate_move(text, text), public.debate_assign(text, text, text), public.debate_nick(text, text),
  public.debate_nick_reset(text, text), public.debate_roster(text), public.debate_note(text, text, text, text), public.debate_vote(text, text),
  public.debate_judge(text, text, text, text, text, text), public.debate_result(text), public.debate_purge(text) from public, anon;
grant execute on function public.debate_join(text), public.debate_move(text, text), public.debate_assign(text, text, text), public.debate_nick(text, text),
  public.debate_nick_reset(text, text), public.debate_roster(text), public.debate_note(text, text, text, text), public.debate_vote(text, text),
  public.debate_judge(text, text, text, text, text, text), public.debate_result(text), public.debate_purge(text) to authenticated;

do $$ begin
  begin alter publication supabase_realtime add table public.debate_notes; exception when duplicate_object then null; end;
end $$;
