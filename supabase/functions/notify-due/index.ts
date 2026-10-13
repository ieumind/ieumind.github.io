// 생각이음 · ⏰ 예약 알림 보내기 (그룹 공개 시각이 되면)
// - pg_cron이 1분마다, 때가 된 예약이 있을 때만 부른다 (x-cron-key = app_secrets.cron_key 일 때만 실행)
// - push_due_take()가 때가 된 예약을 꺼내 ‘보냄’으로 표시하고, 보낼 기기(그 과목·그룹 학생)를 함께 돌려준다
// - 알림 열쇠(VAPID)·cron 열쇠는 app_secrets 표에만 있고, 서버(관리자 열쇠)만 읽는다
import { createClient } from "jsr:@supabase/supabase-js@2";

const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { "Content-Type": "application/json" } });

// Web Push (RFC 8291 aes128gcm) + VAPID (RFC 8292), Web Crypto only
const enc = new TextEncoder();
const b64u = (buf: any) => { const b = buf instanceof Uint8Array ? buf : new Uint8Array(buf); let s = ""; for (const x of b) s += String.fromCharCode(x); return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
const unb64u = (s: string) => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; const bin = atob(s); return Uint8Array.from(bin, c => c.charCodeAt(0)); };
const cat = (...a: Uint8Array[]) => { const n = a.reduce((t, x) => t + x.length, 0), o = new Uint8Array(n); let i = 0; for (const x of a) { o.set(x, i); i += x.length; } return o; };
async function hkdf(salt: Uint8Array, ikm: Uint8Array, info: Uint8Array, len: number) {
  const k = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, k, len * 8));
}
async function vapidAuth(endpoint: string, pubB64u: string, privD: string, subject: string) {
  const pub = unb64u(pubB64u);
  const jwk = { kty: "EC", crv: "P-256", d: privD, x: b64u(pub.slice(1, 33)), y: b64u(pub.slice(33, 65)), ext: true };
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const head = b64u(enc.encode(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const body = b64u(enc.encode(JSON.stringify({ aud: new URL(endpoint).origin, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: subject })));
  const sig = new Uint8Array(await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc.encode(head + "." + body)));
  return `vapid t=${head}.${body}.${b64u(sig)}, k=${pubB64u}`;
}
async function encryptPayload(p256dhB64u: string, authB64u: string, payload: string) {
  const ua = unb64u(p256dhB64u), authSecret = unb64u(authB64u);
  const eph = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const asPub = new Uint8Array(await crypto.subtle.exportKey("raw", eph.publicKey));
  const uaKey = await crypto.subtle.importKey("raw", ua, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const ecdh = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: uaKey }, eph.privateKey, 256));
  const ikm = await hkdf(authSecret, ecdh, cat(enc.encode("WebPush: info\0"), ua, asPub), 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, enc.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, enc.encode("Content-Encoding: nonce\0"), 12);
  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, cat(enc.encode(payload), new Uint8Array([2]))));
  const rs = new Uint8Array([0, 0, 16, 0]);   // 4096
  return cat(salt, rs, new Uint8Array([asPub.length]), asPub, ct);
}
async function sendPush(sub: any, payload: string, vapid: any) {
  const body = await encryptPayload(sub.p256dh, sub.auth, payload);
  const auth = await vapidAuth(sub.endpoint, vapid.publicKey, vapid.privateKey, vapid.subject);
  return fetch(sub.endpoint, { method: "POST", headers: { Authorization: auth, "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", TTL: "86400", Urgency: "normal" }, body });
}

const same = (a: string, b: string) => { if (!a || !b || a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ error: "method" }, 405);
  const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: sec } = await admin.from("app_secrets").select("k,v").in("k", ["cron_key", "vapid_private", "vapid_public"]);
  const get = (k: string) => (sec ?? []).find((x: any) => x.k === k)?.v ?? "";
  if (!same(req.headers.get("x-cron-key") ?? "", get("cron_key"))) return json({ error: "denied" }, 401);
  const vapid = { publicKey: get("vapid_public"), privateKey: get("vapid_private"), subject: "https://ieumind.github.io/" };
  if (!vapid.publicKey || !vapid.privateKey) return json({ error: "not_configured" });
  const { data: jobs, error } = await admin.rpc("push_due_take", { p_limit: 50 });
  if (error) return json({ error: "take_failed" }, 500);
  let sent = 0, gone = 0, failed = 0;
  for (const j of (jobs ?? []) as any[]) {
    const payload = JSON.stringify({ title: String(j.title ?? "생각이음").slice(0, 80), body: String(j.body ?? "").slice(0, 200), url: String(j.url ?? "").slice(0, 200), tag: String(j.tag ?? "").slice(0, 60) });
    await Promise.all(((j.targets ?? []) as any[]).map(async (s) => {
      try {
        const r = await sendPush(s, payload, vapid);
        if (r.ok) sent++;
        else if (r.status === 404 || r.status === 410) { gone++; await admin.from("push_subs").delete().eq("endpoint", s.endpoint); }
        else failed++;
      } catch { failed++; }
    }));
  }
  return json({ jobs: (jobs ?? []).length, sent, gone, failed });
});
