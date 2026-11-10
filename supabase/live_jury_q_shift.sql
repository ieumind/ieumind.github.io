-- =========================================================
-- 실시간 토론 (2026-11-10s): 판정단 질문에 답하기 + 판정단의 토론 전후 생각 변화
--  · debate_msgs.reply_note: 이 메시지가 답한 판정단 질문(debate_notes.id, 우리 팀이나 모두에게 한 질문만)
--  · debate_members.pre: 판정단이 토론 전에 고른 생각 ('pro' | 'con' | 'none'). 대기실에서는 바꿀 수 있고 토론 중에는 한 번만
--  · debate_pre(p_room, p_choice): 고르기 (p_choice가 null이면 지금 값만 돌려준다)
--  · debate_shift(p_room): 토론 전 생각과 종합 판정(c4)을 견준 숫자. 교사는 언제나, 참여 학생은 결과 공개 뒤
-- live_marks.sql 다음에 실행한다.
-- =========================================================
alter table public.debate_msgs add column if not exists reply_note bigint;
alter table public.debate_members add column if not exists pre text;
do $$ begin
  alter table public.debate_members add constraint debate_members_pre_check check (pre in ('pro', 'con', 'none'));
exception when duplicate_object then null; end $$;

drop function if exists public.debate_send(text, text, bigint);
create or replace function public.debate_send(p_room text, p_body text, p_reply bigint default null, p_note bigint default null) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; b text; v_id bigint; v_reply bigint; v_note bigint;
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
  if p_note is not null and exists (select 1 from public.debate_notes where id = p_note and room_id = p_room and not deleted and kind = 'q' and target in ('all', m.team)) then v_note := p_note; end if;
  insert into public.debate_msgs (room_id, tid, mkey, nick, team, body, reply_to, reply_note) values (p_room, r.tid, m.mkey, m.nick, m.team, b, v_reply, v_note) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.debate_pre(p_room text, p_choice text) returns json
language plpgsql volatile security definer set search_path = public as $$
declare r public.docs; m public.debate_members; st text;
begin
  r := public.debate_room(p_room);
  if r.id is null then return json_build_object('ok', false, 'reason', 'denied'); end if;
  select * into m from public.debate_members where room_id = p_room and mkey = public.debate_mkey(p_room, r.tid);
  if not found then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if p_choice is null then return json_build_object('ok', true, 'pre', m.pre); end if;
  if m.team is distinct from 'jury' then return json_build_object('ok', false, 'reason', 'denied'); end if;
  if p_choice not in ('pro', 'con', 'none') then return json_build_object('ok', false, 'reason', 'bad'); end if;
  st := coalesce(r.data -> 'live' ->> 'state', 'wait');
  if st not in ('wait', 'live') then return json_build_object('ok', false, 'reason', 'closed'); end if;
  if st = 'live' and m.pre is not null then return json_build_object('ok', false, 'reason', 'locked'); end if;
  update public.debate_members set pre = p_choice where room_id = p_room and mkey = m.mkey;
  return json_build_object('ok', true, 'pre', p_choice);
end $$;

create or replace function public.debate_shift(p_room text) returns json
language plpgsql stable security definer set search_path = public as $$
declare r public.docs; v_t boolean; res json;
begin
  r := public.debate_room(p_room);
  if r.id is null then return null; end if;
  v_t := public.is_teacher() and r.tid = auth.uid();
  if not (v_t or (coalesce(r.data -> 'live' ->> 'state', '') = 'result' and public.debate_is_member(p_room, r.tid))) then return null; end if;
  select json_build_object(
      'pre',  json_build_object('pro', count(*) filter (where m.pre = 'pro'), 'con', count(*) filter (where m.pre = 'con'), 'none', count(*) filter (where m.pre = 'none')),
      'post', json_build_object('pro', count(*) filter (where j.c4 = 'pro'), 'con', count(*) filter (where j.c4 = 'con')),
      'changed', count(*) filter (where m.pre in ('pro', 'con') and j.c4 in ('pro', 'con') and j.c4 <> m.pre),
      'kept',    count(*) filter (where m.pre in ('pro', 'con') and j.c4 = m.pre),
      'decided', count(*) filter (where m.pre = 'none' and j.c4 in ('pro', 'con')),
      'both',    count(*) filter (where m.pre is not null and j.c4 is not null))
    into res
    from public.debate_members m left join public.debate_jury j on j.room_id = m.room_id and j.mkey = m.mkey
   where m.room_id = p_room and m.team = 'jury';
  return res;
end $$;

revoke execute on function public.debate_send(text, text, bigint, bigint), public.debate_pre(text, text), public.debate_shift(text) from public, anon;
grant execute on function public.debate_send(text, text, bigint, bigint), public.debate_pre(text, text), public.debate_shift(text) to authenticated;
