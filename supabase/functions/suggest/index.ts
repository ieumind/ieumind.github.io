// 생각이음 · 🪄 AI 질문 추천 (Google Gemini API)
// - 선생님만 쓸 수 있다: ai_key_status()로 교사인지 확인
// - API 키는 선생님이 넣은 것을 teacher_ai 표에서 서버(관리자 열쇠)로만 꺼내 쓴다. 화면으로는 돌려주지 않는다
// - AI에게는 키워드·과목·학년·질문 유형만 보낸다 (학생 이름·글은 보내지 않음)
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const clip = (v: unknown, n: number) => String(v ?? "").replace(/[\u0000-\u001f]/g, " ").trim().slice(0, n);

// 새 모델이 나오면 앞쪽에 더한다. 키로 쓸 수 없는 모델(404)이면 다음 모델을 시도하고, 되는 모델을 기억한다
const MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3-flash-preview", "gemini-2.5-flash-lite", "gemini-2.5-flash"];

const SYSTEM = `너는 한국 중·고등학교 선생님의 수업 설계를 돕는 도우미야. 학생에게 던질 '생각 질문'을 만든다.
규칙:
- 한국어로, 학생이 바로 이해할 수 있게 한 문장으로 쓴다 (60자 안팎).
- 키워드와 과목의 핵심을 짚고, 외워서 답하는 질문보다 생각을 넓히고 깊게 하는 질문을 만든다.
- 역사적 사실을 왜곡하지 않는다. 확실하지 않은 수치·인용은 넣지 않는다.
- 특정 정당·현직 정치인을 지지하거나 반대하도록 유도하지 않는다. 혐오·차별·폭력을 부추기는 표현을 쓰지 않는다.
- 학생 개인정보를 묻는 질문은 만들지 않는다.
- 서로 겹치지 않게, 관점과 형식을 다양하게 만든다.`;

const QT: Record<string, string> = {
  fact: "사실적 질문 — 자료를 찾아 확인하면 답할 수 있지만, 핵심을 짚게 하는 질문",
  concept: "개념적 질문 — 여러 사례나 정보를 연결해 의미·원리를 생각하게 하는 질문",
  debate: "논쟁적 질문 — 사람마다 다른 답을 할 수 있고 근거를 들어 주장하게 하는 질문",
};

function buildPrompt(b: any) {
  const kw = clip(b.keywords, 200), subj = clip(b.subject, 30), grade = clip(b.grade, 10), kind = clip(b.kind, 20);
  const ctx = `키워드: ${kw}\n과목: ${subj || "(정하지 않음)"}\n학년: ${grade || "(정하지 않음)"}`;
  if (kind === "debate2" || kind === "debateN")
    return `${ctx}\n\n학생들이 찬반으로 나뉘어 근거를 들어 토론할 수 있는 '토론 논제'를 5개 만들어.
- 한쪽이 뻔히 옳은 논제는 피하고, 양쪽 모두 그럴듯한 근거가 있는 논제로.
- "~해야 할까?", "~인가, ~인가?"처럼 입장을 고를 수 있는 질문으로.
- a와 b에는 두 입장의 짧은 이름(각 12자 이내, '찬성/반대'보다 구체적으로)을 넣어.
- why에는 이 논제로 토론하면 좋은 점을 25자 안팎으로.`;
  if (kind === "relay")
    return `${ctx}\n\n학생들이 스스로 질문을 만들어 볼 '탐구 주제'를 5개 만들어. 호기심을 자극하고 여러 질문이 나올 수 있는 주제로, "~에 대해 궁금한 것을 질문으로 만들어 보자" 같은 형식도 좋아.
- why에는 이 주제에서 나올 수 있는 질문의 예를 25자 안팎으로.`;
  const qt = QT[clip(b.qtype, 10)] || "생각을 깊게 하는 질문";
  return `${ctx}\n질문 유형: ${qt}\n\n이 유형에 맞으면서 통찰을 이끌어 내는 질문을 5개 만들어. 당연한 답이 나오는 질문은 피하고, 원인·의미·관점의 차이를 생각하게 해.
- why에는 이 질문이 무엇을 생각하게 하는지 25자 안팎으로.`;
}

async function callGemini(key: string, model: string, body: unknown) {
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body),
  });
  let j: any = null; try { j = await r.json(); } catch { /* */ }
  return { status: r.status, j };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  let b: any;
  try { b = await req.json(); } catch { return json({ error: "bad_request" }, 400); }
  const URL_ = Deno.env.get("SUPABASE_URL")!;
  const user = createClient(URL_, Deno.env.get("SUPABASE_ANON_KEY")!, { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } });
  const { data: st } = await user.rpc("ai_key_status");
  if (!st?.teacher) return json({ error: "denied" });
  if (!st.has) return json({ error: "no_key" });
  const { data: u } = await user.auth.getUser();
  const admin = createClient(URL_, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: row } = await admin.from("teacher_ai").select("gemini_key, model").eq("uid", u?.user?.id ?? "").maybeSingle();
  if (!row?.gemini_key) return json({ error: "no_key" });

  const test = b?.test === true;
  if (!test && clip(b?.keywords, 200).length < 1) return json({ error: "empty" });
  const req_ = test
    ? { contents: [{ role: "user", parts: [{ text: "연결 확인입니다. OK라고만 답하세요." }] }], generationConfig: { maxOutputTokens: 20 } }
    : {
      systemInstruction: { parts: [{ text: SYSTEM }] },
      contents: [{ role: "user", parts: [{ text: buildPrompt(b) }] }],
      generationConfig: {
        temperature: 1, responseMimeType: "application/json",
        responseSchema: { type: "ARRAY", items: { type: "OBJECT", properties: { q: { type: "STRING" }, a: { type: "STRING" }, b: { type: "STRING" }, why: { type: "STRING" } }, required: ["q"] } },
      },
    };
  const order = [...new Set([row.model, ...MODELS].filter(Boolean))] as string[];
  let last = "ai_error", lastMsg = "";
  for (const m of order) {
    const { status, j } = await callGemini(row.gemini_key, m, req_);
    if (status === 200) {
      if (m !== row.model) await admin.from("teacher_ai").update({ model: m }).eq("uid", u!.user!.id);
      if (test) return json({ ok: true, model: m });
      const text = (j?.candidates?.[0]?.content?.parts ?? []).map((p: any) => p.text ?? "").join("");
      let items: any[] = [];
      try { items = JSON.parse(text.replace(/^```(json)?|```$/g, "").trim()); } catch { /* */ }
      items = (Array.isArray(items) ? items : []).map((x: any) => ({ q: clip(x?.q, 160), a: clip(x?.a, 20), b: clip(x?.b, 20), why: clip(x?.why, 80) })).filter((x) => x.q).slice(0, 6);
      if (!items.length) { last = "ai_error"; continue; }
      return json({ items, model: m });
    }
    const reason = JSON.stringify(j?.error ?? "");
    lastMsg = clip(j?.error?.message, 200);
    if (/API_KEY_INVALID|API key not valid|API_KEY_SERVICE_BLOCKED/i.test(reason)) return json({ error: "bad_key", message: lastMsg });
    if (status === 403) { last = "forbidden"; continue; }
    if (status === 429) { last = "quota"; continue; }
    if (status === 404 || status === 400) { last = last === "quota" ? "quota" : "ai_error"; continue; }
    last = "ai_error";
  }
  return json({ error: last, message: lastMsg });
});
