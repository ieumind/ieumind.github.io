(function(){
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
  window.addEventListener("storage",e=>{ if(e.key===KEY){ const old=D; D=JSON.parse(e.newValue); for(const k in D.docs) if(JSON.stringify(D.docs[k])!==JSON.stringify(old.docs[k])) notify(old.docs[k]?"UPDATE":"INSERT",D.docs[k]); for(const k in old.docs) if(!D.docs[k]) notify("DELETE",{col:old.docs[k].col,id:old.docs[k].id}) }});
  const courseOk = (cid, t) => { const c = cid && D.docs["courses/"+cid]; if(!c || !Array.isArray(c.data.members)) return true; return c.data.members.includes(sidFor(t || tidOf(c))) };
  const roomOk = rid => { const r = D.docs["rooms/"+rid]; return !r || courseOk(r.data.courseId, tidOf(r)) };
  const canRead0 = r => isT ? tidOf(r)===uid : !!sidFor(tidOf(r)) && (["config","treplies"].includes(r.col) || (r.col==="courses" && courseOk(r.id)) || (r.col==="rooms" && courseOk(r.data.courseId)) || (r.col==="posts" && (mySids().includes(r.owner) || ((D.docs["rooms/"+r.data.roomId]?.data?.reveal||"after")!=="teacher" && roomOk(r.data.roomId)))) || (r.col==="replies" && roomOk(r.data.roomId)));
  const canRead = r => canRead0(r);
  const canWrite = (r) => isT ? tidOf(r)===uid : (["posts","replies"].includes(r.col) && !!sidFor(tidOf(r)) && r.data.author===nameFor(tidOf(r)) && roomOk(r.data.roomId) && !["teacher","class"].includes(r.data.kind||""));
  const deny = () => ({data:null, error:{message:"new row violates row-level security policy"}});
  function qb(table){
    const st={table, filters:[], op:"select", rng:null};
    const run = async () => {
      await new Promise(r=>setTimeout(r,5)); D=load();
      if(table==="docs"){
        if(st.op==="select"){ let rows=Object.values(D.docs).filter(r=>st.filters.every(([k,v])=>r[k]===v)).filter(canRead); if(st.rng) rows=rows.slice(st.rng[0],st.rng[1]+1); return {data:rows.map(r=>({id:r.id,data:r.data,tid:tidOf(r)})),error:null} }
        if(st.op==="upsert"||st.op==="insert"){ const k=st.row.col+"/"+st.row.id, ex=D.docs[k];
          if(ex && st.op==="insert") return {error:{message:"duplicate"}};
          const rt = isT ? uid : tidOf(D.docs["rooms/"+(st.row.data||{}).roomId]);
          const row={...st.row, tid: ex ? tidOf(ex) : rt, owner: ex ? ex.owner : (isT?null:sidFor(rt)||null)};
          if(ex && !isT && !mySids().includes(ex.owner)) return deny();
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
      if(fn==="whoami") return {data:{teacher:isT, admin:isT, blocked:false, email:isT?(uid==="T2"?"t2@school.kr":"t@school.kr"):null, student_name: isT?null:myName()}};
      if(fn==="teacher_checkin") return {data:null,error:null};
      if(fn==="ai_key_status"){ const k=localStorage.getItem("__aikey"); return {data:{teacher:isT, has:!!k && isT, tail:k?k.slice(-4):null, model:k?"gemini-3.5-flash-lite":null}} }
      if(fn==="ai_key_set"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const k=(p.p_key||"").trim(); if(!k){ localStorage.removeItem("__aikey"); return {data:{ok:true,has:false}} } if(!/^[A-Za-z0-9_.-]{20,200}$/.test(k)) return {data:{ok:false,reason:"format"}}; localStorage.setItem("__aikey",k); return {data:{ok:true,has:true,tail:k.slice(-4)}} }
      if(fn==="room_view"){ const sid=sidFor(tidOf(D.docs["rooms/"+p.p_room])); if(isT||!sid) return {data:null,error:null}; const v=JSON.parse(localStorage.getItem("__views")||"{}"); const r=v[p.p_room]=v[p.p_room]||{}; const now=new Date().toISOString(); r[sid]=r[sid]?{...r[sid],last_at:now,n:r[sid].n+1}:{first_at:now,last_at:now,n:1}; localStorage.setItem("__views",JSON.stringify(v)); return {data:null,error:null} }
      if(fn==="room_viewers"){ if(!isT) return {data:[],error:null}; const v=JSON.parse(localStorage.getItem("__views")||"{}")[p.p_room]||{}; return {data:Object.entries(v).map(([student_id,x])=>({student_id,...x})),error:null} }
      if(fn==="push_schedule"){ window.__sbLog.push("sched:"+p.p_room+"/"+p.p_group+"@"+(p.p_at?"set":"clear")); return {data:{ok:isT,scheduled:!!p.p_at},error:null} }
      if(fn==="teacher_set_name"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const v=(p.p_name||"").trim(); if(!v) return {data:{ok:false,reason:"empty"}}; window.__sbLog.push("tname:"+v); return {data:{ok:true,name:v},error:null} }
      { const M=JSON.parse(localStorage.getItem("__msgs")||"[]"), saveM=()=>localStorage.setItem("__msgs",JSON.stringify(M));
        if(fn==="msg_send"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const body=(p.p_body||"").trim(); if(!body) return {data:{ok:false,reason:"empty"}};
          const ok=p.p_students.filter(id=>D.students.some(x=>x.id===id && tidOf(x)===uid)); if(!ok.length) return {data:{ok:false,reason:"students"}};
          const batch="b"+Math.random().toString(36).slice(2,8), at=new Date().toISOString(); ok.forEach(sid=>M.push({id:M.length+1,tid:uid,batch,student_id:sid,title:(p.p_title||"").trim(),body,created_at:at,read_at:null})); saveM(); window.__sbLog.push("msg_send:"+ok.length); return {data:{ok:true,batch,n:ok.length},error:null} }
        if(fn==="msg_sent"){ if(!isT) return {data:[],error:null}; const by=new Map(); M.filter(m=>m.tid===uid).forEach(m=>{ if(!by.has(m.batch)) by.set(m.batch,{batch:m.batch,title:m.title,body:m.body,at:m.created_at,rcpt:[]}); by.get(m.batch).rcpt.push({sid:m.student_id,read_at:m.read_at}) }); return {data:[...by.values()].reverse(),error:null} }
        if(fn==="msg_withdraw"){ if(!isT) return {data:0}; const n=M.length; const keep=M.filter(m=>!(m.tid===uid && m.batch===p.p_batch && (!p.p_student||m.student_id===p.p_student))); localStorage.setItem("__msgs",JSON.stringify(keep)); return {data:n-keep.length,error:null} }
        if(fn==="my_msgs"){ if(isT) return {data:[],error:null}; const s=sess(); return {data:M.filter(m=>s[m.tid]===m.student_id).reverse().map(m=>({id:m.id,title:m.title,body:m.body,at:m.created_at,read_at:m.read_at,teacher:m.tid==="T"?"이태형":"김선생"})),error:null} }
        if(fn==="msg_read"){ const s=sess(); M.forEach(m=>{ if(p.p_ids.includes(m.id) && s[m.tid]===m.student_id && !m.read_at) m.read_at=new Date().toISOString() }); saveM(); window.__sbLog.push("msg_read:"+p.p_ids.join(",")); return {data:null,error:null} } }
      if(fn==="my_student_ids") return {data: mySids(), error:null};
      if(fn==="my_students") return {data: isT ? [] : Object.entries(sess()).map(([tid,sid])=>({tid, sid, name:label(D.students.find(x=>x.id===sid))})), error:null};
      if(fn==="push_save"){ window.__push=p; return {data:null,error:null} }
      if(fn==="feedback_send"){ if(!p.p_body||p.p_body.length<2) return {data:{ok:false,reason:"empty"}}; const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.push({id:fb.length+1, who: isT?"교사 t@school.kr":(myName()||"이름 없음"), kind:p.p_kind, body:p.p_body, page:p.p_page, done:false, created_at:new Date().toISOString()}); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:{ok:true},error:null} }
      if(fn==="admin_list_feedback") return {data:JSON.parse(localStorage.getItem("__fb")||"[]"),error:null};
      if(fn==="admin_feedback_done"){ const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.forEach(x=>{ if(x.id===p.p_id) x.done=p.p_done }); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:null,error:null} }
      if(fn==="admin_list_teachers"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); return {data:[{email:"t@school.kr",name:"이태형",first_at:"2026-10-11T05:29:00Z",last_at:new Date().toISOString(),blocked:false,admin:true,rooms:3,students:30,photos:42,photo_mb:11.3},{email:"new@example.com",name:"새선생",first_at:"2026-10-11T07:00:00Z",last_at:"2026-10-11T07:10:00Z",blocked:!!bl["new@example.com"],admin:false,rooms:1,students:2,photos:3,photo_mb:0.8}],error:null} }
      if(fn==="admin_set_blocked"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); bl[p.p_email]=p.p_blocked; localStorage.setItem("__tblock",JSON.stringify(bl)); window.__sbLog.push("block:"+p.p_email+":"+p.p_blocked); return {data:null,error:null} }
      if(fn==="claim_student"){ const s=D.students.find(s=>s.number===p.p_number.trim() && s.name.replace(/ /g,"")===p.p_name.replace(/ /g,"") && s.code.toUpperCase()===p.p_code.trim().toUpperCase()); if(!s) return {data:null}; D.sess2=D.sess2||{}; D.sess2[uid]={...sess(), [tidOf(s)]:s.id}; D.sessions[uid]=s.id; save(); return {data:{id:s.id,name:(s.school ? s.school+" " : "")+s.number+" "+s.name}} }
      if(fn==="my_student_id") return {data: isT ? null : (D.sessions[uid]||null)};
      if(fn==="doc_merge"){ const k=p.p_col+"/"+p.p_id, ex=D.docs[k]; if(!ex) return {error:null}; const row={...ex,data:{...ex.data,...p.p_patch}}; if(!isT && !mySids().includes(ex.owner)) return {error:null}; if(!canWrite(row)) return deny(); D.docs[k]=row; save(); notify("UPDATE",row); return {error:null} }
    },
    functions:{ invoke: async (name, {body}) => { await new Promise(r=>setTimeout(r,20)); if(name==="suggest"){ window.__sbLog.push("suggest:"+JSON.stringify(body)); const k=localStorage.getItem("__aikey"); if(!isT) return {data:{error:"denied"},error:null}; if(!k) return {data:{error:"no_key"},error:null}; if(k.startsWith("BAD")) return {data:{error:"bad_key"},error:null}; if(body.test) return {data:{ok:true,model:"gemini-3.5-flash-lite"},error:null};
        return {data:{items:[{q:"["+body.keywords+"] 콜럼버스의 항해는 발견인가 침략인가?", a:"발견", b:"침략", why:"관점 차이"},{q:"두 번째 논제?", a:"가", b:"나", why:"이유"}], model:"gemini-3.5-flash-lite"},error:null} }
      if(name==="notify"){ window.__sbLog.push("notify:"+body.title+"|"+body.body+"|"+body.url+"|course="+(body.course||"")+(body.groups?"|groups="+body.groups.join("+"):"")+(body.students?"|students="+body.students.length:"")+(body.post?"|post="+body.post:"")); if(body.students||body.post) return {data:{sent:1,gone:0,failed:0,total:1},error:null}; if(!body.course) return {data:{error:"no_course",sent:0,total:0},error:null}; return {data:{sent:2,gone:0,failed:0,total:2},error:null} }
      window.__sbLog.push("fn:"+name+":"+(body.op||"chat"));
      if(body.op==="status") return {data:{ready: q.get("ai")!=="0"}, error:null};
      const last = body.history[body.history.length-1]?.content || "";
      if(last.includes("!!quota")) return {data:{error:"quota"}, error:null};
      if(body.history[0]?.content?.includes("너는 한국 학교")) return {data:{error:"bad_request"}, error:null};
      window.__lastHist = body.history;
      return {data:{text:"(AI가 연기하는 가상 인물) 질문 고마워요. '"+last.slice(0,20)+"'에 대해 말하자면…", remaining:3}, error:null} } },
    from: qb,
    storage:{ from:(bucket)=> bucket==="materials" ? ({
      upload: async (path, blob) => { if(!isT) return {error:{message:"denied"}}; const d = await new Promise(ok=>{const fr=new FileReader(); fr.onload=()=>ok(fr.result); fr.readAsDataURL(blob)}); const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); st["m/"+path]=d; localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("mupload:"+path); return {data:{path},error:null} },
      getPublicUrl: (path) => ({data:{publicUrl: JSON.parse(localStorage.getItem("__sbstore")||"{}")["m/"+path]}}) }) : ({
      upload: async (path, blob, o) => { const sid=path.split("/")[1]; if(isT || !mySids().includes(sid)) return {error:{message:"new row violates row-level security policy"}};
        const d = await new Promise(ok=>{const fr=new FileReader(); fr.onload=()=>ok(fr.result); fr.readAsDataURL(blob)});
        const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); if(st[path]) return {error:{message:"exists"}}; st[path]=d; localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("upload:"+path); return {data:{path},error:null} },
      createSignedUrls: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); window.__sbLog.push("sign:"+paths.length);
        return {data: paths.map(p => { const sid=p.split("/")[1], rm = D.docs["rooms/"+p.split("/")[0]], ok = isT || mySids().includes(sid) || (!!rm && (rm.data.reveal||"teacher") !== "teacher" && !!sidFor(tidOf(rm))); return {path:p, signedUrl: ok && st[p] ? st[p] : null, error: ok ? null : "denied"} })} },
      remove: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); paths.forEach(p=>{ const sid=p.split("/")[1]; if(isT || mySids().includes(sid)) delete st[p] }); localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("remove:"+paths.length); return {error:null} }
    })},
    channel(){ const subs=[]; const c={ on(type,f,cb){ subs.push([f,cb]); return c }, subscribe(){ ch.push((ev,row)=>{ for(const [f,cb] of subs){ if(f.event!==ev) continue; if(f.filter && f.filter!=="col=eq."+row.col) continue; if(!canRead(row) && ev!=="DELETE") continue; cb(ev==="DELETE"?{old:row}:{new:{id:row.id,data:row.data,col:row.col}}) } }); return c } }; return c }
  };
  rpcImpl = client._rpc;
  window.supabase={createClient:()=>client};
})();
