(function(){
  { const ow = console.warn; console.warn = (...a) => { if(String(a[0]).includes("[icon]")) setTimeout(() => { throw new Error("ICON missing: " + a[1]) }); ow(...a) } }   // 없는 아이콘 → 테스트 오류
  const KEY="__sbmock", q=new URLSearchParams(location.search), who=q.get("who")||"anon";
  const load=()=>JSON.parse(localStorage.getItem(KEY)||'{"docs":{},"students":[],"sessions":{}}');
  let D=load(); const save=()=>localStorage.setItem(KEY,JSON.stringify(D));
  const uid = who==="teacher" ? "T" : who==="teacher2" ? "T2" : (sessionStorage.getItem("uid") || (()=>{const u="A"+Math.random().toString(36).slice(2,8); sessionStorage.setItem("uid",u); return u})());
  const isT = who==="teacher" || who==="teacher2";
  /* 선생님 여러 명: 문서·학생에 tid(없으면 "T"), 학생 기기 연결은 sess2[uid][tid] = 학생 id */
  const tidOf = r => (r && r.tid) || "T";
  const sess = () => { const m = {...((D.sess2||{})[uid]||{})}; const legacy = D.sessions[uid]; if(legacy && !Object.values(m).includes(legacy)){ const st = D.students.find(x=>x.id===legacy); if(st) m[tidOf(st)] = st.id } return m };
  const sidFor = t => sess()[t||"T"];
  const mySids = () => Object.values(sess());
  const label = st => st ? (st.school ? st.school+" " : "")+st.number+" "+st.name : null;
  const nameFor = t => label(D.students.find(x=>x.id===sidFor(t)));
  const myStu = () => { const sid=D.sessions[uid]; return D.students.find(s=>s.id===sid) };
  const myName = () => label(myStu());
  const ch=[]; window.__sbLog=[];
  const notify=(ev,row)=>ch.forEach(c=>c(ev,row));
  window.addEventListener("storage",e=>{ if(e.key===KEY){ const old=D; D=JSON.parse(e.newValue); for(const k in D.docs) if(JSON.stringify(D.docs[k])!==JSON.stringify(old.docs[k])) notify(old.docs[k]?"UPDATE":"INSERT",D.docs[k]); for(const k in old.docs) if(!D.docs[k]) notify("DELETE",{col:old.docs[k].col,id:old.docs[k].id});
    for(const t of ["debate_members","debate_msgs","debate_votes","debate_jury","debate_notes","debate_marks"]){ const a=((old.live||{})[t]||[]), b=((D.live||{})[t]||[]), key=r=>["debate_msgs","debate_notes","debate_jury"].includes(t)?r.id:t==="debate_marks"?r.room_id+"|"+r.mkey+"|"+r.msg_id:r.room_id+"|"+r.mkey;
      const om=new Map(a.map(r=>[key(r),JSON.stringify(r)])); b.forEach(r=>{ const o=om.get(key(r)); if(o===undefined) notify("INSERT",{...r,table:t}); else if(o!==JSON.stringify(r)) notify("UPDATE",{...r,table:t}) }) } }});
  const courseOk = (cid, t) => { const c = cid && D.docs["courses/"+cid]; if(!c || !Array.isArray(c.data.members)) return true; return c.data.members.includes(sidFor(t || tidOf(c))) };
  const roomOk = rid => { const r = D.docs["rooms/"+rid]; return !r || courseOk(r.data.courseId, tidOf(r)) };
  const canRead0 = r => isT ? tidOf(r)===uid : !!sidFor(tidOf(r)) && (["config","treplies"].includes(r.col) || (r.col==="courses" && courseOk(r.id)) || (r.col==="rooms" && courseOk(r.data.courseId)) || (r.col==="posts" && (mySids().includes(r.owner) || ((D.docs["rooms/"+r.data.roomId]?.data?.reveal||"after")!=="teacher" && roomOk(r.data.roomId)))) || (r.col==="replies" && roomOk(r.data.roomId)));
  /* 🙋 임시 참가자(과목 없는 활동에 이름·닉네임만 넣고 참여): D.guests = [{uid, room, tid, nick}] */
  const gList = () => D.guests || [];
  const gIn = rid => gList().some(g => g.uid===uid && g.room===rid);
  const gNick = rid => gList().find(g => g.uid===uid && g.room===rid)?.nick;
  const roomFree = rid => { const r = D.docs["rooms/"+rid]; return !!r && !(r.data.courseId||""); };
  const guestRead = r => { if(isT) return false; const rid = r.col==="rooms" ? r.id : r.data.roomId; if(!rid || !gIn(rid) || !roomFree(rid)) return false;
    if(r.col==="rooms" || r.col==="replies") return true;
    if(r.col==="posts") return r.owner===uid || (D.docs["rooms/"+rid]?.data?.reveal||"after")!=="teacher";
    if(r.col==="treplies") return r.data.kind==="class" || D.docs["posts/"+r.data.postId]?.owner===uid; return false };
  const guestWrite = r => !isT && ["posts","replies"].includes(r.col) && !!r.data.roomId && gIn(r.data.roomId) && roomFree(r.data.roomId) && r.data.author===gNick(r.data.roomId) && !["teacher","class"].includes(r.data.kind||"");
  const canRead = r => canRead0(r) || guestRead(r);
  /* 💬 실시간 토론(debate_*) 흉내: 서버 함수·권한 규칙을 그대로 따라 한다 */
  const LVD = () => { D.live = D.live || {debate_members:[], debate_msgs:[], debate_votes:[], debate_jury:[], debate_notes:[], seq:0}; D.live.debate_jury = D.live.debate_jury || []; D.live.debate_notes = D.live.debate_notes || []; D.live.debate_marks = D.live.debate_marks || []; return D.live };
  const lvRoom = rid => { const r = D.docs["rooms/"+rid]; return r && r.data.template==="live" ? r : null };
  const lvKey = rid => { const r = lvRoom(rid); if(!r || isT) return null; const sid = sidFor(tidOf(r)); if(sid && roomOk(rid)) return "s:"+sid; if(gIn(rid) && roomFree(rid)) return "g:"+uid; return null };
  const lvMember = rid => LVD().debate_members.find(m => m.room_id===rid && m.mkey===lvKey(rid));
  const lvPfx = (r, team) => team==="pro" ? (((r.data.stances||[])[0])||"찬성").slice(0,4) : team==="con" ? (((r.data.stances||[])[1])||"반대").slice(0,4) : "판정단";
  const lvGen = (rid, team) => { const r = lvRoom(rid), pf = lvPfx(r, team); for(let i=1;;i++){ const c = pf + String(i).padStart(2,"0"); if(!LVD().debate_members.some(m => m.room_id===rid && m.nick===c)) return c } };
  const lvCfg = r => r.data.liveCfg || {};
  const lvState = r => (r.data.live||{}).state || "wait";
  const lvCanRead = row => { const r = lvRoom(row.room_id); if(!r) return false; if(isT) return tidOf(r)===uid;
    if(["debate_msgs","debate_notes"].includes(row.table)) return !!lvMember(row.room_id); return row.mkey===lvKey(row.room_id) };
  const lvSave = (t, row, ev) => { save(); notify(ev, {...row, table:t}) };
  const canWrite = (r) => isT ? tidOf(r)===uid : guestWrite(r) || (["posts","replies"].includes(r.col) && !!sidFor(tidOf(r)) && r.data.author===nameFor(tidOf(r)) && roomOk(r.data.roomId) && !["teacher","class"].includes(r.data.kind||""));
  const deny = () => ({data:null, error:{message:"new row violates row-level security policy"}});
  function qb(table){
    const st={table, filters:[], op:"select", rng:null};
    const run = async () => {
      await new Promise(r=>setTimeout(r,5)); D=load();
      if(table.startsWith("debate_")){
        const L = LVD(), rows = L[table];
        const match = r => st.filters.every(([k,v]) => r[k]===v);
        if(st.op==="select"){ let out = rows.filter(r => match(r) && lvCanRead({...r, table})).sort((a,b) => (a.id||0)-(b.id||0)); if(st.rng) out = out.slice(st.rng[0], st.rng[1]+1);
          return {data: out.map(r => { const x = {...r}; if(!isT) delete x.real_name; return x }), error:null} }
        if(st.op==="update"){ if(!isT) return {data:null, error:null}; let n=0; rows.forEach(r => { if(match(r) && tidOf(lvRoom(r.room_id))===uid){ Object.assign(r, st.row); n++; lvSave(table, r, "UPDATE") } }); return {data:null, error:null} }
        return {data:null, error:{message:"permission denied"}};
      }
      if(table==="docs"){
        if(st.op==="select"){ let rows=Object.values(D.docs).filter(r=>st.filters.every(([k,v])=>r[k]===v)).filter(canRead); if(st.rng) rows=rows.slice(st.rng[0],st.rng[1]+1); return {data:rows.map(r=>({id:r.id,data:r.data,tid:tidOf(r)})),error:null} }
        if(st.op==="upsert"||st.op==="insert"){ const k=st.row.col+"/"+st.row.id, ex=D.docs[k];
          if(ex && st.op==="insert") return {error:{message:"duplicate"}};
          const rt = isT ? uid : tidOf(D.docs["rooms/"+(st.row.data||{}).roomId]);
          const row={...st.row, tid: ex ? tidOf(ex) : rt, owner: ex ? ex.owner : (isT?null:sidFor(rt)||((st.row.data||{}).roomId && gIn((st.row.data||{}).roomId) ? uid : null))};
          if(ex && !isT && !mySids().includes(ex.owner) && ex.owner!==uid) return deny();
          if(!canWrite(row)) return deny();
          D.docs[k]=row; save(); notify(ex?"UPDATE":"INSERT",row); return {data:null,error:null} }
        if(st.op==="delete"){ if(!isT) return {data:null,error:null}; const [c,i]=[st.filters.find(f=>f[0]==="col")[1],st.filters.find(f=>f[0]==="id")[1]]; delete D.docs[c+"/"+i]; save(); notify("DELETE",{col:c,id:i}); return {error:null} }
      }
      if(table==="students"){
        if(!isT) return {data:[],error:null};
        if(st.op==="select"){ return {data:D.students.filter(x=>tidOf(x)===uid).sort((a,b)=>a.number.localeCompare(b.number)),error:null} }
        if(st.op==="insert"){ st.row.forEach(r=>D.students.push({id:"s"+Math.random().toString(36).slice(2,8),...r,tid:uid})); save(); return {error:null} }
        if(st.op==="update"){ const id=st.filters.find(f=>f[0]==="id")[1]; Object.assign(D.students.find(s=>s.id===id),st.row); save(); return {error:null} }
        if(st.op==="delete"){ const id=st.filters.find(f=>f[0]==="id")[1]; D.students=D.students.filter(s=>s.id!==id); save(); return {error:null} }
      }
      return {data:null,error:{message:"?"}};
    };
    const api={ select(){return api}, eq(k,v){st.filters.push([k,v]);return api}, range(a,b){st.rng=[a,b];return api}, order(){return api},
      upsert(row){st.op= table==="students" ? "insert" : "upsert";st.row=row;return api}, insert(row){st.op="insert";st.row=row;return api}, delete(){st.op="delete";return api}, update(row){st.op="update";st.row=row;return api},
      then(res,rej){ return run().then(res,rej) } };
    return api;
  }
  let rpcImpl;
  const client={
    auth:{ getSession: async()=>({data:{session: {user:{user_metadata: isT ? {full_name:"Google 이름", ...(q.get("newteacher") && !localStorage.getItem("__tname") ? {} : {display_name: localStorage.getItem("__tname") || "이태형"})} : {}, id: isT ? (uid==="T2" ? "teacher2-uid" : "teacher-uid") : uid, is_anonymous: !isT}}}}), signInAnonymously: async()=>({data:{session:{user:{is_anonymous:true}}}}),
      signInWithOAuth: async(o)=>{ window.__oauth=o; return {data:{}} }, updateUser: async(o)=>{ window.__sbLog.push("updateUser:"+JSON.stringify(o)); if(o?.data?.display_name) localStorage.setItem("__tname", o.data.display_name); return {data:{},error:null} }, signOut: async()=>{ sessionStorage.removeItem("uid"); window.__signedOut=true; return {} } },
    rpc: (fn, p) => { const pr = rpcImpl(fn, p); return {then:(a,b) => pr.then(a,b)} },   // 실제 supabase-js처럼 .catch 없음
    rpcImpl_: 0,
    _rpc: async (fn, p) => { await new Promise(r=>setTimeout(r,5)); D=load(); window.__sbLog.push(fn);
      if(fn==="whoami"){ const ref=p&&p.p_ref, rr=ref&&D.docs["rooms/"+ref], coded=!!rr && !!sidFor(tidOf(rr)), fr=!isT && !!rr && !(rr.data.courseId||"") && !["draft","archived"].includes(rr.data.status||"open") && !coded;
        return {data:{teacher:isT, admin:isT, blocked:false, email:isT?(uid==="T2"?"t2@school.kr":"t@school.kr"):null, student_name: isT?null:myName(),
          ref_found: !!(ref && (rr || D.docs["courses/"+ref])), guest_room: fr, guest_name: ref&&!isT ? (gNick(ref)||null) : null, guest_nick: isT ? null : (gList().find(g=>g.uid===uid)?.nick||null), guest_title: fr ? rr.data.title : null, guest_teacher: fr ? (rr.data.teacherName||null) : null}} }
      if(fn==="my_guests") return {data: isT ? [] : gList().filter(g=>g.uid===uid).map(g=>({room:g.room, nick:g.nick})), error:null};
      if(fn==="guest_join"){ const rr=D.docs["rooms/"+p.p_room], bad=r=>({data:{ok:false,reason:r},error:null});
        if(isT || !rr || (rr.data.courseId||"") || ["draft","archived"].includes(rr.data.status||"open")) return bad("denied");
        if(sidFor(tidOf(rr))) return bad("student");
        const mine=gList().find(g=>g.uid===uid && g.room===p.p_room); if(mine) return {data:{ok:true,name:mine.nick},error:null};
        const dev=gList().find(g=>g.uid===uid)?.nick, nick=(dev||p.p_nick||"").trim().replace(/\s+/g," ");
        if(!nick) return bad("empty"); if(nick.length>20) return bad("long"); if(nick.split(" ").some(x=>/^\d{3,10}$/.test(x))) return bad("number");
        const key=nick.replace(/ /g,"").toLowerCase(); if(["선생님","선생","teacher","관리자","익명"].includes(key)) return bad("reserved");
        if(gList().filter(g=>g.room===p.p_room).some(g=>g.nick.replace(/ /g,"").toLowerCase()===key)) return bad("taken");
        D.guests=[...gList(), {uid, room:p.p_room, tid:tidOf(rr), nick}]; save(); window.__sbLog.push("guest_join:"+nick); return {data:{ok:true,name:nick},error:null} }
      if(fn==="teacher_checkin") return {data:null,error:null};
      if(fn.startsWith("debate_")){ const L = LVD(), rid = p.p_room, r = lvRoom(rid), no = why => ({data:{ok:false, reason:why}, error:null});
        if(fn==="debate_join"){ if(!r || ["draft","archived"].includes(r.data.status||"open")) return no("denied"); const k = lvKey(rid); if(!k) return no("denied");
          const ex = L.debate_members.find(m => m.room_id===rid && m.mkey===k); if(ex) return {data:{ok:true, nick:ex.nick, team:ex.team, muted:ex.muted, mkey:k}, error:null};
          let nick;
          const team = "jury"; nick = lvGen(rid, "jury");
          const real = k.startsWith("s:") ? nameFor(tidOf(r)) : gNick(rid);
          const row = {room_id:rid, mkey:k, tid:tidOf(r), uid, real_name:real||"이름 없음", nick, team, muted:false, joined_at:new Date().toISOString()};
          L.debate_members.push(row); lvSave("debate_members", row, "INSERT"); return {data:{ok:true, nick, team, muted:false, mkey:k}, error:null} }
        if(fn==="debate_send"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m) return no("denied");
          if(m.team==="jury") return no("jury"); if(((r.data.live||{}).state||"wait") !== "live") return no("closed"); if(!m.team) return no("noteam"); if(m.muted) return no("muted");
          const b = String(p.p_body||"").trim(); if(!b) return no("empty"); if(b.length > 200) return no("long");
          const now = Date.now(), mine = L.debate_msgs.filter(x => x.room_id===rid && x.mkey===m.mkey);
          if(mine.some(x => now - Date.parse(x.created_at) < 3000)) return no("fast"); if(mine.filter(x => now - Date.parse(x.created_at) < 60000).length >= 10) return no("many");
          const rp = p.p_reply != null && L.debate_msgs.some(x => x.id===p.p_reply && x.room_id===rid && !x.deleted) ? p.p_reply : null;
          const rn = p.p_note != null && L.debate_notes.some(x => x.id===p.p_note && x.room_id===rid && !x.deleted && x.kind==="q" && (x.target==="all" || x.target===m.team)) ? p.p_note : null;
          const row = {id:++L.seq, room_id:rid, tid:m.tid, mkey:m.mkey, nick:m.nick, team:m.team, body:b, deleted:false, created_at:new Date().toISOString(), reply_to:rp, reply_note:rn};
          L.debate_msgs.push(row); lvSave("debate_msgs", row, "INSERT"); window.__sbLog.push("debate_send"); return {data:{ok:true, id:row.id}, error:null} }
        if(fn==="debate_pre"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m) return no("denied"); if(p.p_choice==null) return {data:{ok:true, pre:m.pre||null}, error:null};
          if(m.team!=="jury") return no("denied"); if(!["pro","con","none"].includes(p.p_choice)) return no("bad"); const st = lvState(r);
          if(!["wait","live"].includes(st)) return no("closed"); if(st==="live" && m.pre) return no("locked");
          m.pre = p.p_choice; lvSave("debate_members", m, "UPDATE"); return {data:{ok:true, pre:m.pre}, error:null} }
        if(fn==="debate_shift"){ if(!r) return {data:null, error:null}; const ok = (isT && tidOf(r)===uid) || (lvState(r)==="result" && !!lvMember(rid)); if(!ok) return {data:null, error:null};
          const js = L.debate_members.filter(x => x.room_id===rid && x.team==="jury"), jj = k => (L.debate_jury.find(x => x.room_id===rid && x.mkey===k)||{}).c4;
          const c = f => js.filter(f).length;
          return {data:{pre:{pro:c(x=>x.pre==="pro"), con:c(x=>x.pre==="con"), none:c(x=>x.pre==="none")}, post:{pro:c(x=>jj(x.mkey)==="pro"), con:c(x=>jj(x.mkey)==="con")},
            changed:c(x=>["pro","con"].includes(x.pre) && ["pro","con"].includes(jj(x.mkey)) && jj(x.mkey)!==x.pre), kept:c(x=>["pro","con"].includes(x.pre) && jj(x.mkey)===x.pre),
            decided:c(x=>x.pre==="none" && ["pro","con"].includes(jj(x.mkey))), both:c(x=>x.pre && jj(x.mkey))}, error:null} }
        if(fn==="debate_mark"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m || m.team!=="jury") return no("denied"); if(!["live","ended","vote"].includes(lvState(r))) return no("closed");
          if(!L.debate_msgs.some(x => x.id===p.p_msg && x.room_id===rid && !x.deleted)) return no("bad");
          const has = L.debate_marks.find(x => x.room_id===rid && x.mkey===m.mkey && x.msg_id===p.p_msg);
          if(p.p_on){ if(L.debate_marks.filter(x => x.room_id===rid && x.mkey===m.mkey).length >= 30) return no("many"); if(!has){ const row = {room_id:rid, tid:m.tid, mkey:m.mkey, msg_id:p.p_msg, created_at:new Date().toISOString()}; L.debate_marks.push(row); lvSave("debate_marks", row, "INSERT") } }
          else if(has){ L.debate_marks.splice(L.debate_marks.indexOf(has), 1); save() }
          window.__sbLog.push("debate_mark:"+p.p_msg+":"+p.p_on); return {data:{ok:true}, error:null} }
        if(fn==="debate_mark_sum"){ if(!r) return {data:null, error:null}; const ok = (isT && tidOf(r)===uid) || (lvState(r)==="result" && !!lvMember(rid)); if(!ok) return {data:null, error:null};
          const n = {}; L.debate_marks.filter(x => x.room_id===rid && L.debate_msgs.some(g => g.id===x.msg_id && !g.deleted)).forEach(x => n[x.msg_id] = (n[x.msg_id]||0)+1);
          return {data:Object.entries(n).map(([id, c]) => ({id:+id, n:c})).sort((a,b) => b.n-a.n || a.id-b.id), error:null} }
        if(fn==="debate_vote"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m) return no("denied"); if(m.team==="jury") return no("jury"); if(L.debate_members.some(x => x.room_id===rid && x.team==="jury")) return no("byjury"); if(((r.data.live||{}).state||"wait") !== "vote") return no("closed");
          if(!["pro","con"].includes(p.p_choice)) return no("bad"); if(L.debate_votes.some(v => v.room_id===rid && v.mkey===m.mkey)) return no("dup");
          const row = {room_id:rid, mkey:m.mkey, tid:m.tid, choice:p.p_choice, created_at:new Date().toISOString()}; L.debate_votes.push(row); lvSave("debate_votes", row, "INSERT"); return {data:{ok:true}, error:null} }
        if(fn==="debate_result"){ if(!r) return {data:null, error:null}; const ok = (isT && tidOf(r)===uid) || (((r.data.live||{}).state)==="result" && !!lvMember(rid)); if(!ok) return {data:null, error:null};
          const vs = L.debate_votes.filter(v => v.room_id===rid), js = L.debate_jury.filter(v => v.room_id===rid), isTe = isT && tidOf(r)===uid;
          const t = k => ({pro:js.filter(j => j[k]==="pro").length, con:js.filter(j => j[k]==="con").length}), w = f => js.filter(j => ["c1","c2","c3"].filter(k => j[k]===f).length >= 2).length;
          return {data:{pro:vs.filter(v => v.choice==="pro").length + js.filter(j => j.c4==="pro").length, con:vs.filter(v => v.choice==="con").length + js.filter(j => j.c4==="con").length, jury:{n:js.length, c1:t("c1"), c2:t("c2"), c3:t("c3"), c4:t("c4"), win:{pro:w("pro"), con:w("con")}, reasons:js.filter(j => isTe || !j.hidden).map(j => ({id:j.id, reason:j.reason, hidden:!!j.hidden}))}}, error:null} }
        if(fn==="debate_judge"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m || m.team!=="jury") return no("denied"); if(((r.data.live||{}).state||"wait") !== "vote") return no("closed");
          if(![p.p_c1,p.p_c2,p.p_c3,p.p_c4].every(x => ["pro","con"].includes(x))) return no("bad"); const b = String(p.p_reason||"").trim(); if(b.length < 5) return no("short"); if(b.length > 300) return no("long");
          const need = [0,1,2].includes(lvCfg(r).noteMin) ? lvCfg(r).noteMin : 1; if(L.debate_notes.filter(x => x.room_id===rid && x.mkey===m.mkey && !x.deleted).length < need) return no("notes");
          if(L.debate_jury.some(v => v.room_id===rid && v.mkey===m.mkey)) return no("dup");
          const row = {id:++L.seq, room_id:rid, mkey:m.mkey, tid:m.tid, c1:p.p_c1, c2:p.p_c2, c3:p.p_c3, c4:p.p_c4, reason:b, hidden:false, created_at:new Date().toISOString()}; L.debate_jury.push(row); lvSave("debate_jury", row, "INSERT"); return {data:{ok:true}, error:null} }
        if(fn==="debate_move"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m) return no("denied"); const t = p.p_team; if(!["pro","con","jury"].includes(t)) return no("bad");
          if(lvState(r) !== "wait") return no("locked"); if(lvCfg(r).selfMove === false) return no("selfoff"); if(m.team===t) return {data:{ok:true, nick:m.nick, team:m.team}, error:null};
          const N = Math.min(10, Math.max(1, parseInt(lvCfg(r).teamN)||4)); if(t!=="jury" && L.debate_members.filter(x => x.room_id===rid && x.team===t).length >= N) return no("full");
          m.nick = (lvCfg(r).nickMode==="custom" && m.nick_set) ? m.nick : lvGen(rid, t); m.team = t; lvSave("debate_members", m, "UPDATE"); return {data:{ok:true, nick:m.nick, team:t}, error:null} }
        if(fn==="debate_assign"){ if(!r || !isT || tidOf(r)!==uid) return no("denied"); const m = L.debate_members.find(x => x.room_id===rid && x.mkey===p.p_mkey); if(!m) return no("denied"); const t = p.p_team; if(!["pro","con","jury"].includes(t)) return no("bad");
          if(m.team!==t){ m.nick = (lvCfg(r).nickMode==="custom" && m.nick_set) ? m.nick : lvGen(rid, t); m.team = t; lvSave("debate_members", m, "UPDATE") } return {data:{ok:true, nick:m.nick, team:m.team}, error:null} }
        if(fn==="debate_nick"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m) return no("denied"); if(lvCfg(r).nickMode!=="custom") return no("mode"); if(lvState(r)!=="wait") return no("locked");
          const n = String(p.p_nick||"").trim(); if(!/^[가-힣A-Za-z0-9_·-]{2,8}$/.test(n)) return no("bad"); if(/^(판정단|찬성|반대)[0-9]+$/.test(n)) return no("reserved");
          if(L.debate_members.some(x => x.room_id===rid && x.real_name===n)) return no("real"); if(L.debate_members.some(x => x.room_id===rid && x.nick===n && x.mkey!==m.mkey)) return no("dup");
          m.nick = n; m.nick_set = true; lvSave("debate_members", m, "UPDATE"); return {data:{ok:true, nick:n}, error:null} }
        if(fn==="debate_nick_reset"){ if(!r || !isT || tidOf(r)!==uid) return no("denied"); const m = L.debate_members.find(x => x.room_id===rid && x.mkey===p.p_mkey); if(!m) return no("denied");
          m.nick = lvGen(rid, m.team||"jury"); m.nick_set = false; lvSave("debate_members", m, "UPDATE"); return {data:{ok:true, nick:m.nick}, error:null} }
        if(fn==="debate_roster"){ if(!r) return {data:null, error:null}; if(!((isT && tidOf(r)===uid) || lvMember(rid))) return {data:null, error:null};
          return {data:L.debate_members.filter(x => x.room_id===rid).map(x => ({nick:x.nick, team:x.team})).sort((a,b) => String(a.team).localeCompare(String(b.team)) || a.nick.localeCompare(b.nick)), error:null} }
        if(fn==="debate_note"){ if(!r) return no("denied"); const m = lvMember(rid); if(!m || m.team!=="jury") return no("denied"); if(!["live","ended","vote"].includes(lvState(r))) return no("closed"); if(m.muted) return no("muted");
          if(!["q","t"].includes(p.p_kind) || !["pro","con","all"].includes(p.p_target)) return no("bad"); const b = String(p.p_body||"").trim(); if(!b) return no("empty"); if(b.length > 100) return no("long");
          const mine = L.debate_notes.filter(x => x.room_id===rid && x.mkey===m.mkey); if(mine.some(x => Date.now()-Date.parse(x.created_at) < 3000)) return no("fast"); if(mine.length >= 20) return no("many");
          const row = {id:++L.seq, room_id:rid, tid:m.tid, mkey:m.mkey, nick:m.nick, kind:p.p_kind, target:p.p_target, body:b, deleted:false, created_at:new Date().toISOString()}; L.debate_notes.push(row); lvSave("debate_notes", row, "INSERT"); return {data:{ok:true, id:row.id}, error:null} }
        if(fn==="debate_purge"){ if(!isT) return {data:null, error:null}; ["debate_msgs","debate_votes","debate_jury","debate_notes","debate_members"].forEach(t => { L[t] = L[t].filter(x => x.room_id!==rid) }); save(); window.__sbLog.push("debate_purge:"+rid); return {data:null, error:null} }
      }
      if(fn==="ai_key_status"){ const k=localStorage.getItem("__aikey"); return {data:{teacher:isT, has:!!k && isT, tail:k?k.slice(-4):null, model:k?"gemini-3.5-flash-lite":null}} }
      if(fn==="ai_key_set"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const k=(p.p_key||"").trim(); if(!k){ localStorage.removeItem("__aikey"); return {data:{ok:true,has:false}} } if(!/^[A-Za-z0-9_.-]{20,200}$/.test(k)) return {data:{ok:false,reason:"format"}}; localStorage.setItem("__aikey",k); return {data:{ok:true,has:true,tail:k.slice(-4)}} }
      if(fn==="room_view"){ const sid=sidFor(tidOf(D.docs["rooms/"+p.p_room])); if(isT||!sid) return {data:null,error:null}; const v=JSON.parse(localStorage.getItem("__views")||"{}"); const r=v[p.p_room]=v[p.p_room]||{}; const now=new Date().toISOString(); r[sid]=r[sid]?{...r[sid],last_at:now,n:r[sid].n+1}:{first_at:now,last_at:now,n:1}; localStorage.setItem("__views",JSON.stringify(v)); return {data:null,error:null} }
      if(fn==="room_viewers"){ if(!isT) return {data:[],error:null}; const v=JSON.parse(localStorage.getItem("__views")||"{}")[p.p_room]||{}; return {data:Object.entries(v).map(([student_id,x])=>({student_id,...x})),error:null} }
      if(fn==="push_schedule"){ window.__sbLog.push("sched:"+p.p_room+"/"+p.p_group+"@"+(p.p_at?"set":"clear")); return {data:{ok:isT,scheduled:!!p.p_at},error:null} }
      if(fn==="teacher_delete_me"){ if(!isT) return {data:{ok:false,reason:"denied"}}; if(localStorage.getItem("__admin")) return {data:{ok:false,reason:"admin"}}; if(p&&p.p_dry) return {data:{ok:true,dry:true}}; window.__sbLog.push("deleteMe"); localStorage.setItem("__deleted","1"); return {data:{ok:true}} }
      if(fn==="teacher_set_name"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const v=(p.p_name||"").trim(); if(!v) return {data:{ok:false,reason:"empty"}}; window.__sbLog.push("tname:"+v); return {data:{ok:true,name:v},error:null} }
      { const M=JSON.parse(localStorage.getItem("__msgs")||"[]"), saveM=()=>localStorage.setItem("__msgs",JSON.stringify(M));
        if(fn==="msg_send"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const body=(p.p_body||"").trim(); if(!body) return {data:{ok:false,reason:"empty"}};
          const ok=p.p_students.filter(id=>D.students.some(x=>x.id===id && tidOf(x)===uid)); if(!ok.length) return {data:{ok:false,reason:"students"}};
          const batch="b"+Math.random().toString(36).slice(2,8), at=new Date().toISOString(); ok.forEach(sid=>M.push({id:M.length+1,tid:uid,batch,student_id:sid,title:(p.p_title||"").trim(),body,created_at:at,read_at:null})); saveM(); window.__sbLog.push("msg_send:"+ok.length); return {data:{ok:true,batch,n:ok.length},error:null} }
        if(fn==="msg_send_each"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const items=p.p_items.filter(it=>D.students.some(x=>x.id===it.sid && tidOf(x)===uid) && (it.body||"").trim()); if(!items.length) return {data:{ok:false,reason:"students"}};
          const batch="b"+Math.random().toString(36).slice(2,8), at=new Date().toISOString(), ask=(p.p_ask||[]).filter(q=>q.trim()); items.forEach(it=>M.push({id:M.length+1,tid:uid,batch,student_id:it.sid,title:p.p_title,body:it.body,created_at:at,read_at:null,kind:"score",ask:ask.length?ask:null,answers:null,answered_at:null})); saveM(); window.__sbLog.push("msg_send_each:"+items.length); return {data:{ok:true,batch,n:items.length},error:null} }
        if(fn==="msg_answer"){ const s=sess(), m=M.find(m=>m.id===p.p_id && s[m.tid]===m.student_id); if(!m||!m.ask) return {data:{ok:false,reason:"denied"}}; if(m.answered_at) return {data:{ok:false,reason:"done"}}; if(p.p_answers.length!==m.ask.length) return {data:{ok:false,reason:"bad"}}; m.answers=p.p_answers; m.answered_at=new Date().toISOString(); m.read_at=m.read_at||m.answered_at; saveM(); window.__sbLog.push("msg_answer:"+JSON.stringify(p.p_answers)); return {data:{ok:true},error:null} }
        if(fn==="msg_sent"){ if(!isT) return {data:[],error:null}; const by=new Map(); M.filter(m=>m.tid===uid).forEach(m=>{ if(!by.has(m.batch)) by.set(m.batch,{batch:m.batch,title:m.title,body:m.body,at:m.created_at,kind:m.kind||"note",ask:m.ask||null,rcpt:[]}); by.get(m.batch).rcpt.push({sid:m.student_id,read_at:m.read_at,answers:m.answers||null,answered_at:m.answered_at||null,body:m.kind==="score"?m.body:null}) }); return {data:[...by.values()].reverse(),error:null} }
        if(fn==="msg_withdraw"){ if(!isT) return {data:0}; const n=M.length; const keep=M.filter(m=>!(m.tid===uid && m.batch===p.p_batch && (!p.p_student||m.student_id===p.p_student))); localStorage.setItem("__msgs",JSON.stringify(keep)); return {data:n-keep.length,error:null} }
        if(fn==="my_msgs"){ if(isT) return {data:[],error:null}; const s=sess(); return {data:M.filter(m=>s[m.tid]===m.student_id).reverse().map(m=>({id:m.id,title:m.title,body:m.body,at:m.created_at,read_at:m.read_at,teacher:m.tid==="T"?"이태형":"김선생",kind:m.kind||"note",ask:m.ask||null,answers:m.answers||null,answered_at:m.answered_at||null})),error:null} }
        if(fn==="msg_read"){ const s=sess(); M.forEach(m=>{ if(p.p_ids.includes(m.id) && s[m.tid]===m.student_id && !m.read_at) m.read_at=new Date().toISOString() }); saveM(); window.__sbLog.push("msg_read:"+p.p_ids.join(",")); return {data:null,error:null} } }
      if(fn==="my_student_ids") return {data: mySids(), error:null};
      if(fn==="my_students") return {data: isT ? [] : Object.entries(sess()).map(([tid,sid])=>({tid, sid, name:label(D.students.find(x=>x.id===sid))})), error:null};
      if(fn==="push_who"){ return {data:window.__pushWho||[],error:null} }
      if(fn==="push_save"){ window.__push=p; return {data:null,error:null} }
      if(fn==="feedback_send"){ if(!p.p_body||p.p_body.length<2) return {data:{ok:false,reason:"empty"}}; const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.push({id:fb.length+1, who: isT?"교사 t@school.kr":(myName()||"이름 없음"), kind:p.p_kind, body:p.p_body, page:p.p_page, done:false, created_at:new Date().toISOString()}); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:{ok:true},error:null} }
      if(fn==="admin_list_feedback") return {data:JSON.parse(localStorage.getItem("__fb")||"[]"),error:null};
      if(fn==="admin_feedback_done"){ const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.forEach(x=>{ if(x.id===p.p_id) x.done=p.p_done }); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:null,error:null} }
      if(fn==="admin_list_teachers"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); return {data:[{email:"t@school.kr",name:"이태형",first_at:"2026-10-11T05:29:00Z",last_at:new Date().toISOString(),blocked:false,admin:true,rooms:3,students:30,photos:42,photo_mb:11.3},{email:"new@example.com",name:"새선생",first_at:"2026-10-11T07:00:00Z",last_at:"2026-10-11T07:10:00Z",blocked:!!bl["new@example.com"],admin:false,rooms:1,students:2,photos:3,photo_mb:0.8}],error:null} }
      if(fn==="admin_set_blocked"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); bl[p.p_email]=p.p_blocked; localStorage.setItem("__tblock",JSON.stringify(bl)); window.__sbLog.push("block:"+p.p_email+":"+p.p_blocked); return {data:null,error:null} }
      if(fn==="claim_student"){ const s=D.students.find(s=>s.number===p.p_number.trim() && s.name.replace(/ /g,"")===p.p_name.replace(/ /g,"") && s.code.toUpperCase()===p.p_code.trim().toUpperCase()); if(!s) return {data:null}; D.sess2=D.sess2||{}; D.sess2[uid]={...sess(), [tidOf(s)]:s.id}; D.sessions[uid]=s.id; save(); return {data:{id:s.id,name:(s.school ? s.school+" " : "")+s.number+" "+s.name}} }
      if(fn==="my_student_id") return {data: isT ? null : (D.sessions[uid] || (gIn(p.p_room) ? uid : null))};
      if(fn==="doc_merge"){ const k=p.p_col+"/"+p.p_id, ex=D.docs[k]; if(!ex) return {error:null}; const row={...ex,data:{...ex.data,...p.p_patch}}; if(!isT && !mySids().includes(ex.owner) && ex.owner!==uid) return {error:null}; if(!canWrite(row)) return deny(); D.docs[k]=row; save(); notify("UPDATE",row); return {error:null} }
    },
    functions:{ invoke: async (name, {body}) => { await new Promise(r=>setTimeout(r,20)); if(name==="suggest"){ window.__sbLog.push("suggest:"+JSON.stringify(body)); const k=localStorage.getItem("__aikey"); if(!isT) return {data:{error:"denied"},error:null}; if(!k) return {data:{error:"no_key"},error:null}; if(k.startsWith("BAD")) return {data:{error:"bad_key"},error:null}; if(body.test) return {data:{ok:true,model:"gemini-3.5-flash-lite"},error:null};
        if(body.op==="guide"){ const m=localStorage.getItem("__guidemode")||""; if(m==="err") return {data:{error:"quota"},error:null}; if(m==="bad") return {data:{text:"제목이 빠진 짧은 글", model:"gemini-3.5-flash-lite"},error:null};
          return {data:{text:"(Gemini 다듬음 "+(body.regen?"다시":"처음")+") "+body.role+"\n"+body.base, greeting:"(테스트 시작) 어서 오게. 무슨 일로 왔는가?", user:"젊은 관리", call:"경", starters:["보고드리겠습니다","개화가 필요합니다"], model:"gemini-3.5-flash-lite"},error:null} }
        if(body.op==="persona") return {data:{text:"[생애와 활동]\n- "+body.name+" 테스트 사실 (장면: "+(body.scene||"")+")\n[말투]\n- 테스트 말투", model:"gemini-3.5-flash-lite"},error:null};
        return {data:{items:[{q:"["+body.keywords+"] 콜럼버스의 항해는 발견인가 침략인가?", a:"발견", b:"침략", why:"관점 차이"},{q:"두 번째 논제?", a:"가", b:"나", why:"이유"}], model:"gemini-3.5-flash-lite"},error:null} }
      if(name==="notify"){ window.__sbLog.push("notify:"+body.title+"|"+body.body+"|"+body.url+"|course="+(body.course||"")+(body.groups?"|groups="+body.groups.join("+"):"")+(body.students?"|students="+body.students.length:"")+(body.post?"|post="+body.post:"")); if(body.students||body.post) return {data:{sent:1,gone:0,failed:0,total:1},error:null}; if(!body.course) return {data:{error:"no_course",sent:0,total:0},error:null}; return {data:{sent:2,gone:0,failed:0,total:2},error:null} }
      window.__sbLog.push("fn:"+name+":"+(body.op||"chat"));
      if(body.op==="status") return {data:{ready: q.get("ai")!=="0"}, error:null};
      const last = body.history[body.history.length-1]?.content || "";
      if(last.includes("!!quota")) return {data:{error:"quota"}, error:null};
      if(body.history[0]?.content?.includes("너는 한국 학교")) return {data:{error:"bad_request"}, error:null};
      window.__lastHist = body.history; window.__lastChat = body;
      return {data:{text:"(AI가 연기하는 가상 인물) 질문 고마워요. '"+last.slice(0,20)+"'에 대해 말하자면…", remaining:3}, error:null} } },
    from: qb,
    storage:{ from:(bucket)=> bucket==="materials" ? ({
      list: async () => ({data:[],error:null}), remove: async (paths) => { window.__sbLog.push("rmM:"+paths.length); return {data:null,error:null} },
      upload: async (path, blob) => { if(!isT) return {error:{message:"denied"}}; const d = await new Promise(ok=>{const fr=new FileReader(); fr.onload=()=>ok(fr.result); fr.readAsDataURL(blob)}); const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); st["m/"+path]=d; localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("mupload:"+path); return {data:{path},error:null} },
      getPublicUrl: (path) => ({data:{publicUrl: JSON.parse(localStorage.getItem("__sbstore")||"{}")["m/"+path]}}) }) : ({
      upload: async (path, blob, o) => { const sid=path.split("/")[1]; if(isT || !(mySids().includes(sid) || (sid===uid && gIn(path.split("/")[0])))) return {error:{message:"new row violates row-level security policy"}};
        const d = await new Promise(ok=>{const fr=new FileReader(); fr.onload=()=>ok(fr.result); fr.readAsDataURL(blob)});
        const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); if(st[path]) return {error:{message:"exists"}}; st[path]=d; localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("upload:"+path); return {data:{path},error:null} },
      createSignedUrls: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); window.__sbLog.push("sign:"+paths.length);
        return {data: paths.map(p => { const sid=p.split("/")[1], rm = D.docs["rooms/"+p.split("/")[0]], ok = isT || mySids().includes(sid) || (sid===uid && gIn(p.split("/")[0])) || (!!rm && (rm.data.reveal||"teacher") !== "teacher" && !!sidFor(tidOf(rm))); return {path:p, signedUrl: ok && st[p] ? st[p] : null, error: ok ? null : "denied"} })} },
      list: async (prefix) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"), seen=new Map(); Object.keys(st).filter(k=>k.startsWith(prefix+"/")).forEach(k=>{ const rest=k.slice(prefix.length+1).split("/"); seen.set(rest[0], rest.length>1 ? null : "f") }); return {data:[...seen].map(([name,id])=>({name,id})),error:null} },
      remove: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); paths.forEach(p=>{ const sid=p.split("/")[1]; if(isT || mySids().includes(sid)) delete st[p] }); localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("remove:"+paths.length); return {error:null} }
    })},
    channel(name, opts){
      if(String(name||"").startsWith("lvp-")){       // presence: 같은 이름 채널끼리 localStorage로 접속 상태 공유 (1초마다 신호, 4초 넘게 없으면 빠짐)
        const key=opts?.config?.presence?.key||"anon", PK="__pres", syncs=[]; let me=null, hb=null;
        const read=()=>{ try{ return JSON.parse(localStorage.getItem(PK)||"{}") }catch(e){ return {} } };
        const write=o=>localStorage.setItem(PK, JSON.stringify(o));
        const beat=()=>{ if(!me) return; const o=read(); o[name]=o[name]||{}; o[name][key]={...me, t:Date.now()}; write(o) };
        const fire=()=>syncs.forEach(f=>f());
        const pc={ on(type,f,cb){ if(type==="presence") syncs.push(cb); return pc },
          presenceState(){ const o=read()[name]||{}, now=Date.now(), st={}; for(const k in o) if(now-o[k].t<4000) st[k]=[o[k]]; return st },
          track(pl){ me=pl||{}; beat(); return Promise.resolve("ok") },
          untrack(){ me=null; const o=read(); if(o[name]) delete o[name][key]; write(o); return Promise.resolve("ok") },
          subscribe(sc){ hb=setInterval(()=>{ beat(); fire() }, 1000); window.addEventListener("storage", e=>{ if(e.key===PK) fire() }); if(sc) setTimeout(()=>{ sc("SUBSCRIBED"); fire() }, 10); return pc },
          unsubscribe(){ clearInterval(hb) } };
        window.__presStop = () => { clearInterval(hb); me=null };
        return pc;
      }
      const subs=[]; const c={ on(type,f,cb){ subs.push([f,cb]); return c }, subscribe(sc){ ch.push((ev,row)=>{ for(const [f,cb] of subs){ if(f.event!==ev && f.event!=="*") continue;
          if(row.table){ if(f.table!==row.table) continue; if(f.filter && f.filter!=="room_id=eq."+row.room_id) continue; if(!lvCanRead(row)) continue; const x={...row}; delete x.table; if(!isT) delete x.real_name; cb({new:x}); continue }
          if(f.table && f.table!=="docs") continue;
          if(f.filter && f.filter!=="col=eq."+row.col) continue; if(!canRead(row) && ev!=="DELETE") continue; cb(ev==="DELETE"?{old:row}:{new:{id:row.id,data:row.data,col:row.col}}) } }); if(sc) setTimeout(()=>sc("SUBSCRIBED"), 10); return c } }; return c }
  };
  rpcImpl = client._rpc;
  window.supabase={createClient:()=>client};
})();
