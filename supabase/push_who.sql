-- 알림을 켠 학생 표시 (교사 전용): 학생 id 목록만 돌려준다. 기기 주소·키는 내보내지 않는다.
create or replace function public.push_who() returns uuid[]
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_teacher() then return '{}'; end if;
  return coalesce((select array_agg(distinct ss.student_id) from public.student_sessions ss
    where ss.tid = auth.uid() and ss.student_id is not null
      and exists (select 1 from public.push_subs s where s.uid = ss.uid)), '{}');
end $$;
revoke execute on function public.push_who() from public, anon;
grant execute on function public.push_who() to authenticated;
