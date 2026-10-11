// 생각이음 · 새 활동·공지 알림 보내기 (Web Push)
// - 교사만 보낼 수 있다: push_targets()/push_targets_for(과목)가 교사 확인 + 한 시간 30번 제한 + ‘내 학생(그 과목 수강 학생) 기기’만 돌려준다
// - 알림 열쇠(VAPID)는 app_secrets 표에만 있고, 서버(관리자 열쇠)만 읽는다
// - 암호화는 표준(RFC 8291 aes128gcm)과 서명(RFC 8292 VAPID)을 Web Crypto로 직접 한다
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });

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

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  let body: any;
  try { body = await req.json(); } catch { return json({ error: "bad_request" }, 400); }
  const payload = JSON.stringify({
    title: String(body?.title ?? "생각이음").slice(0, 80),
    body: String(body?.body ?? "").slice(0, 200),
    url: String(body?.url ?? "").slice(0, 200),
    tag: String(body?.tag ?? "").slice(0, 60),
  });
  const URL_ = Deno.env.get("SUPABASE_URL")!;
  const user = createClient(URL_, Deno.env.get("SUPABASE_ANON_KEY")!, { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } });
  const admin = createClient(URL_, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const course = String(body?.course ?? "").slice(0, 80);              // 과목 공지·과목 활동이면 그 과목 수강 학생에게만
  const { data: targets, error } = course ? await user.rpc("push_targets_for", { p_course: course }) : await user.rpc("push_targets");
  if (error) return json({ error: "denied" });
  const list = (targets ?? []) as { endpoint: string; p256dh: string; auth: string }[];
  if (!list.length) return json({ sent: 0, total: 0 });
  const { data: sec } = await admin.from("app_secrets").select("k,v").in("k", ["vapid_private", "vapid_public"]);
  const get = (k: string) => (sec ?? []).find((x: any) => x.k === k)?.v;
  const vapid = { publicKey: get("vapid_public"), privateKey: get("vapid_private"), subject: "https://taeneuu.github.io/thinklink/" };
  if (!vapid.publicKey || !vapid.privateKey) return json({ error: "not_configured" });
  let sent = 0, gone = 0, failed = 0;
  await Promise.all(list.map(async (s) => {
    try {
      const r = await sendPush(s, payload, vapid);
      if (r.ok) sent++;
      else if (r.status === 404 || r.status === 410) { gone++; await user.rpc("push_drop", { p_endpoint: s.endpoint }); }
      else failed++;
    } catch { failed++; }
  }));
  return json({ sent, gone, failed, total: list.length });
});
