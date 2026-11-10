-- =========================================================
-- 실시간 토론 ④ (2026-11-10o): 반박 인용 + 청중 판정단의 ‘좋은 근거’ 표시
--  · debate_msgs.reply_to: 이 메시지가 반박하는 메시지 번호(같은 방, 지워지지 않은 메시지만)
--  · debate_marks: 판정단이 ‘좋은 근거’로 표시한 메시지 (한 사람 한 메시지에 한 번, 30개까지)
--    - 표시한 사람 본인과 교사만 행을 읽는다. 메시지별 개수는 debate_mark_sum으로 (교사는 언제나, 학생은 결과 공개 뒤)
-- 이미 setup.sql·live_debate.sql·live_jury.sql·live_lobby.sql이 적용된 뒤에 실행한다.
-- =========================================================
alter table public.debate_msgs add column if not exists reply_to bigint;

create table if not exists public.debate_marks (
  room_id    text not null,
  tid        uuid not null,
  mkey       text not null,                 -- 표시한 판정단
  msg_id     bigint not null references public.debate_msgs (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (room_id, mkey, msg_id)
);
create index if not exists debate_marks_msg on public.debate_marks (room_id, msg_id);
alter table public.debate_marks enable row level security;
revoke all on public.debate_marks from public, anon, authenticated;
grant select on public.debate_marks to authenticated;
drop policy if exists debate_marks_read on public.debate_marks;
create policy debate_marks_read on public.debate_marks for select to authenticated
  using ((public.is_teacher() and tid = auth.uid()) or mkey = public.debate_mkey(room_id, tid));

-- 메시지 보내기: 세 번째 값(p_reply)이 있으면 그 메시지에 대한 반박으로 저장 (예전 앱의 두 값 호출도 그대로 된다)
drop function if exists public.debate_send(text, text);
create or replace function public.debate_send(p_room text, p_body text, p_reply bigint default null) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_id bigint; v_reply bigint;
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
  if p_reply is not null and exists (select 1 from public.debate_msgs where id = p_reply and room_id = p_room and not deleted) then v_reply := p_reply; end if;
  insert into public.debate_msgs (room_id, tid, mkey, nick, team, body, reply_to) values (p_room, r.tid, m.mkey, m.nick, m.team, b, v_reply) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- 좋은 근거 표시: 판정단만 · 토론 중/종료 후/판정 중 · 켜고 끄기
create or replace function public.debate_mark(p_room text, p_msg bigint, p_on boolean) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found or m.team is distinct from 'jury' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if coalesce(r.data -> 'live' ->> 'state', 'wait') not in ('live', 'ended', 'vote') then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if not exists (select 1 from public.debate_msgs where id = p_msg and room_id = p_room and not deleted) then return json_build_object('ok', false, 'reason', 'bad'); end if;
  if coalesce(p_on, false) then
    if (select count(*) from public.debate_marks where room_id = p_room and mkey = m.mkey) >= 30 then return json_build_object('ok', false, 'reason', 'many'); end if;
    insert into public.debate_marks (room_id, tid, mkey, msg_id) values (p_room, r.tid, m.mkey, p_msg) on conflict do nothing;
  else
    delete from public.debate_marks where room_id = p_room and mkey = m.mkey and msg_id = p_msg;
  end if;
  return json_build_object('ok', true);
end $$;

-- 메시지별 ‘좋은 근거’ 개수: 교사는 언제나, 참여 학생은 결과 공개(result) 뒤에만
create or replace function public.debate_mark_sum(p_room text) returns json
language plpgsql stable security definer set search_path = public as $$
declare r public.docs; v_t boolean;
begin
  r := public.debate_room(p_room);
  if r.id is null then return null; end if;
  v_t := public.is_teacher() and r.tid = auth.uid();
  if not (v_t or (coalesce(r.data -> 'live' ->> 'state', '') = 'result' and public.debate_is_member(p_room, r.tid))) then return null; end if;
  return (select coalesce(json_agg(json_build_object('id', t.msg_id, 'n', t.n) order by t.n desc, t.msg_id), '[]'::json)
            from (select k.msg_id, count(*) as n from public.debate_marks k join public.debate_msgs g on g.id = k.msg_id and not g.deleted
                   where k.room_id = p_room group by k.msg_id) t);
end $$;

create or replace function public.debate_purge(p_room text) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if not public.is_teacher() then return; end if;
  delete from public.debate_marks   where room_id = p_room and tid = auth.uid();
  delete from public.debate_msgs    where room_id = p_room and tid = auth.uid();
  delete from public.debate_notes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_votes   where room_id = p_room and tid = auth.uid();
  delete from public.debate_jury    where room_id = p_room and tid = auth.uid();
  delete from public.debate_members where room_id = p_room and tid = auth.uid();
end $$;

revoke execute on function public.debate_send(text, text, bigint), public.debate_mark(text, bigint, boolean), public.debate_mark_sum(text), public.debate_purge(text) from public, anon;
grant execute on function public.debate_send(text, text, bigint), public.debate_mark(text, bigint, boolean), public.debate_mark_sum(text), public.debate_purge(text) to authenticated;

do $$ begin
  begin alter publication supabase_realtime add table public.debate_marks; exception when duplicate_object then null; end;
end $$;
