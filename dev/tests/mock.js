(function(){
  const KEY="__sbmock", q=new URLSearchParams(location.search), who=q.get("who")||"anon";
  const load=()=>JSON.parse(localStorage.getItem(KEY)||'{"docs":{},"students":[],"sessions":{}}');
  let D=load(); const save=()=>localStorage.setItem(KEY,JSON.stringify(D));
  const uid = who==="teacher" ? "T" : (sessionStorage.getItem("uid") || (()=>{const u="A"+Math.random().toString(36).slice(2,8); sessionStorage.setItem("uid",u); return u})());
  const isT = who==="teacher";
  const myStu = () => { const sid=D.sessions[uid]; return D.students.find(s=>s.id===sid) };
  const myName = () => { const s=myStu(); return s ? (s.school ? s.school+" " : "")+s.number+" "+s.name : null };
  const ch=[]; window.__sbLog=[];
  const notify=(ev,row)=>ch.forEach(c=>c(ev,row));
  window.addEventListener("storage",e=>{ if(e.key===KEY){ const old=D; D=JSON.parse(e.newValue); for(const k in D.docs) if(JSON.stringify(D.docs[k])!==JSON.stringify(old.docs[k])) notify(old.docs[k]?"UPDATE":"INSERT",D.docs[k]); for(const k in old.docs) if(!D.docs[k]) notify("DELETE",{col:old.docs[k].col,id:old.docs[k].id}) }});
  const courseOk = cid => { const c = cid && D.docs["courses/"+cid]; if(!c || !Array.isArray(c.data.members)) return true; return c.data.members.includes(D.sessions[uid]) };
  const roomOk = rid => { const r = D.docs["rooms/"+rid]; return !r || courseOk(r.data.courseId) };
  const canRead0 = r => isT || !!myStu() && (["config","treplies"].includes(r.col) || (r.col==="courses" && courseOk(r.id)) || (r.col==="rooms" && courseOk(r.data.courseId)) || (r.col==="posts" && (r.owner===D.sessions[uid] || ((D.docs["rooms/"+r.data.roomId]?.data?.reveal||"after")!=="teacher" && roomOk(r.data.roomId)))) || (r.col==="replies" && roomOk(r.data.roomId)));
  const canRead = r => canRead0(r);
  const canWrite = (r) => isT || (["posts","replies"].includes(r.col) && myStu() && r.data.author===myName() && !["teacher","class"].includes(r.data.kind||""));
  const deny = () => ({data:null, error:{message:"new row violates row-level security policy"}});
  function qb(table){
    const st={table, filters:[], op:"select", rng:null};
    const run = async () => {
      await new Promise(r=>setTimeout(r,5)); D=load();
      if(table==="docs"){
        if(st.op==="select"){ let rows=Object.values(D.docs).filter(r=>st.filters.every(([k,v])=>r[k]===v)).filter(canRead); if(st.rng) rows=rows.slice(st.rng[0],st.rng[1]+1); return {data:rows.map(r=>({id:r.id,data:r.data})),error:null} }
        if(st.op==="upsert"||st.op==="insert"){ const k=st.row.col+"/"+st.row.id, ex=D.docs[k];
          if(ex && st.op==="insert") return {error:{message:"duplicate"}};
          const row={...st.row, owner: ex ? ex.owner : (isT?null:D.sessions[uid]||null)};
          if(ex && !isT && ex.owner!==D.sessions[uid]) return deny();
          if(!canWrite(row)) return deny();
          D.docs[k]=row; save(); notify(ex?"UPDATE":"INSERT",row); return {data:null,error:null} }
        if(st.op==="delete"){ if(!isT) return {data:null,error:null}; const [c,i]=[st.filters.find(f=>f[0]==="col")[1],st.filters.find(f=>f[0]==="id")[1]]; delete D.docs[c+"/"+i]; save(); notify("DELETE",{col:c,id:i}); return {error:null} }
      }
      if(table==="students"){
        if(!isT) return {data:[],error:null};
        if(st.op==="select"){ return {data:[...D.students].sort((a,b)=>a.number.localeCompare(b.number)),error:null} }
        if(st.op==="insert"){ st.row.forEach(r=>D.students.push({id:"s"+Math.random().toString(36).slice(2,8),...r})); save(); return {error:null} }
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
    auth:{ getSession: async()=>({data:{session: {user:{is_anonymous: !isT}}}}), signInAnonymously: async()=>({data:{session:{user:{is_anonymous:true}}}}),
      signInWithOAuth: async(o)=>{ window.__oauth=o; return {data:{}} }, signOut: async()=>{ sessionStorage.removeItem("uid"); window.__signedOut=true; return {} } },
    rpc: (fn, p) => { const pr = rpcImpl(fn, p); return {then:(a,b) => pr.then(a,b)} },   // 실제 supabase-js처럼 .catch 없음
    rpcImpl_: 0,
    _rpc: async (fn, p) => { await new Promise(r=>setTimeout(r,5)); D=load(); window.__sbLog.push(fn);
      if(fn==="whoami") return {data:{teacher:isT, admin:isT, blocked:false, email:isT?"t@school.kr":null, student_name: isT?null:myName()}};
      if(fn==="teacher_checkin") return {data:null,error:null};
      if(fn==="ai_key_status"){ const k=localStorage.getItem("__aikey"); return {data:{teacher:isT, has:!!k && isT, tail:k?k.slice(-4):null, model:k?"gemini-3.5-flash-lite":null}} }
      if(fn==="ai_key_set"){ if(!isT) return {data:{ok:false,reason:"denied"}}; const k=(p.p_key||"").trim(); if(!k){ localStorage.removeItem("__aikey"); return {data:{ok:true,has:false}} } if(!/^[A-Za-z0-9_.-]{20,200}$/.test(k)) return {data:{ok:false,reason:"format"}}; localStorage.setItem("__aikey",k); return {data:{ok:true,has:true,tail:k.slice(-4)}} }
      if(fn==="my_student_ids") return {data: D.sessions[uid] ? [D.sessions[uid]] : [], error:null};
      if(fn==="push_save"){ window.__push=p; return {data:null,error:null} }
      if(fn==="feedback_send"){ if(!p.p_body||p.p_body.length<2) return {data:{ok:false,reason:"empty"}}; const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.push({id:fb.length+1, who: isT?"교사 t@school.kr":(myName()||"이름 없음"), kind:p.p_kind, body:p.p_body, page:p.p_page, done:false, created_at:new Date().toISOString()}); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:{ok:true},error:null} }
      if(fn==="admin_list_feedback") return {data:JSON.parse(localStorage.getItem("__fb")||"[]"),error:null};
      if(fn==="admin_feedback_done"){ const fb=JSON.parse(localStorage.getItem("__fb")||"[]"); fb.forEach(x=>{ if(x.id===p.p_id) x.done=p.p_done }); localStorage.setItem("__fb",JSON.stringify(fb)); return {data:null,error:null} }
      if(fn==="admin_list_teachers"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); return {data:[{email:"t@school.kr",name:"이태형",first_at:"2026-10-11T05:29:00Z",last_at:new Date().toISOString(),blocked:false,admin:true,rooms:3,students:30,photos:42,photo_mb:11.3},{email:"new@example.com",name:"새선생",first_at:"2026-10-11T07:00:00Z",last_at:"2026-10-11T07:10:00Z",blocked:!!bl["new@example.com"],admin:false,rooms:1,students:2,photos:3,photo_mb:0.8}],error:null} }
      if(fn==="admin_set_blocked"){ const bl=JSON.parse(localStorage.getItem("__tblock")||"{}"); bl[p.p_email]=p.p_blocked; localStorage.setItem("__tblock",JSON.stringify(bl)); window.__sbLog.push("block:"+p.p_email+":"+p.p_blocked); return {data:null,error:null} }
      if(fn==="claim_student"){ const s=D.students.find(s=>s.number===p.p_number.trim() && s.name.replace(/ /g,"")===p.p_name.replace(/ /g,"") && s.code.toUpperCase()===p.p_code.trim().toUpperCase()); if(!s) return {data:null}; D.sessions[uid]=s.id; save(); return {data:{id:s.id,name:(s.school ? s.school+" " : "")+s.number+" "+s.name}} }
      if(fn==="my_student_id") return {data: isT ? null : (D.sessions[uid]||null)};
      if(fn==="doc_merge"){ const k=p.p_col+"/"+p.p_id, ex=D.docs[k]; if(!ex) return {error:null}; const row={...ex,data:{...ex.data,...p.p_patch}}; if(!isT && ex.owner!==D.sessions[uid]) return {error:null}; if(!canWrite(row)) return deny(); D.docs[k]=row; save(); notify("UPDATE",row); return {error:null} }
    },
    functions:{ invoke: async (name, {body}) => { await new Promise(r=>setTimeout(r,20)); if(name==="suggest"){ window.__sbLog.push("suggest:"+JSON.stringify(body)); const k=localStorage.getItem("__aikey"); if(!isT) return {data:{error:"denied"},error:null}; if(!k) return {data:{error:"no_key"},error:null}; if(k.startsWith("BAD")) return {data:{error:"bad_key"},error:null}; if(body.test) return {data:{ok:true,model:"gemini-3.5-flash-lite"},error:null};
        return {data:{items:[{q:"["+body.keywords+"] 콜럼버스의 항해는 발견인가 침략인가?", a:"발견", b:"침략", why:"관점 차이"},{q:"두 번째 논제?", a:"가", b:"나", why:"이유"}], model:"gemini-3.5-flash-lite"},error:null} }
      if(name==="notify"){ window.__sbLog.push("notify:"+body.title+"|"+body.body+"|"+body.url+"|course="+(body.course||"")); return {data:{sent:2,gone:0,failed:0,total:2},error:null} }
      window.__sbLog.push("fn:"+name+":"+(body.op||"chat"));
      if(body.op==="status") return {data:{ready: q.get("ai")!=="0"}, error:null};
      const last = body.history[body.history.length-1]?.content || "";
      if(last.includes("!!quota")) return {data:{error:"quota"}, error:null};
      if(body.history[0]?.content?.includes("너는 한국 학교")) return {data:{error:"bad_request"}, error:null};
      window.__lastHist = body.history;
      return {data:{text:"(AI가 연기하는 가상 인물) 질문 고마워요. '"+last.slice(0,20)+"'에 대해 말하자면…", remaining:3}, error:null} } },
    from: qb,
    storage:{ from:(bucket)=>({
      upload: async (path, blob, o) => { const sid=path.split("/")[1]; if(isT || D.sessions[uid]!==sid) return {error:{message:"new row violates row-level security policy"}};
        const d = await new Promise(ok=>{const fr=new FileReader(); fr.onload=()=>ok(fr.result); fr.readAsDataURL(blob)});
        const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); if(st[path]) return {error:{message:"exists"}}; st[path]=d; localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("upload:"+path); return {data:{path},error:null} },
      createSignedUrls: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); window.__sbLog.push("sign:"+paths.length);
        return {data: paths.map(p => { const sid=p.split("/")[1], ok = isT || D.sessions[uid]===sid; return {path:p, signedUrl: ok && st[p] ? st[p] : null, error: ok ? null : "denied"} })} },
      remove: async (paths) => { const st=JSON.parse(localStorage.getItem("__sbstore")||"{}"); paths.forEach(p=>{ const sid=p.split("/")[1]; if(isT || D.sessions[uid]===sid) delete st[p] }); localStorage.setItem("__sbstore",JSON.stringify(st)); window.__sbLog.push("remove:"+paths.length); return {error:null} }
    })},
    channel(){ const subs=[]; const c={ on(type,f,cb){ subs.push([f,cb]); return c }, subscribe(){ ch.push((ev,row)=>{ for(const [f,cb] of subs){ if(f.event!==ev) continue; if(f.filter && f.filter!=="col=eq."+row.col) continue; if(!canRead(row) && ev!=="DELETE") continue; cb(ev==="DELETE"?{old:row}:{new:{id:row.id,data:row.data,col:row.col}}) } }); return c } }; return c }
  };
  rpcImpl = client._rpc;
  window.supabase={createClient:()=>client};
})();
