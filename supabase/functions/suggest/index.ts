// 생각이음 · 🪄 AI 질문 추천 (Google Gemini API)
// - 선생님만 쓸 수 있다: ai_key_status()로 교사인지 확인
// - API 키는 선생님이 넣은 것을 teacher_ai 표에서 서버(관리자 열쇠)로만 꺼내 쓴다. 화면으로는 돌려주지 않는다
// - AI에게는 키워드·과목·학년·질문 유형만 보낸다 (학생 이름·글은 보내지 않음)
// - op:"persona" — 가상 인물 대화의 ‘AI용 인물 자료’ 초안 (인물 이름·대화 장면·인물 소개만 보낸다). 선생님이 확인하고 고쳐 쓴다
// - op:"guide" — 가상 인물 대화의 ‘AI 대화 지시문’ 다듬기 (선생님이 고른 항목과 화면이 만든 기본 지시문만 보낸다). 선생님이 확인하고 적용한다
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

const SYSTEM_P = `너는 한국 중·고등학교 선생님의 수업 준비를 돕는 도우미야. 학생이 AI 역할극으로 대화할 인물에 대해, 역할극 AI가 근거로 삼을 '인물 자료'를 만든다.
규칙:
- 역사적으로 널리 확인된 사실만 쓴다. 조금이라도 불확실한 이름·날짜·숫자·단체는 쓰지 않는다.
- 실제 발언을 인용하지 않는다(직접 인용문 금지). 성격·일화도 널리 알려진 것만 쓴다.
- 평가가 엇갈리는 일은 "평가가 엇갈린다"고 밝히고 여러 시각을 짧게 적는다. 가해·범죄가 있는 인물은 그 사실과 피해를 분명히 적는다.
- 특정 정당·현직 정치인을 지지하거나 반대하지 않는다.
- 한국어 개조식 문장으로, 꾸밈(굵은 글씨·표) 없이 쓴다.`;
function buildPersonaPrompt(b: any) {
  const name = clip(b.name, 30), scene = clip(b.scene, 300), about = clip(b.about, 200), subj = clip(b.subject, 30);
  return `인물: ${name}\n대화 장면(시점): ${scene || "(정하지 않음 — 이 인물의 생애 전체)"}\n선생님이 쓴 인물 소개: ${about || "(없음)"}\n과목: ${subj || "(정하지 않음)"}

아래 여섯 묶음으로, 각 줄은 "- "로 시작하는 한 문장으로 써. 전체 1,800자 안팎.
[생애와 활동] 대화 장면 시점까지의 확인된 사실 6~10개(연도 포함). 장면보다 뒤에 일어난 일은 쓰지 않는다.
[생각과 가치관] 이 인물이 중요하게 여긴 생각 3~5개
[성격과 기질] 기록과 일화로 알려진 성격·기질·감정 표현·취미나 습관 3~5개 (역할극에서 살아 있는 사람처럼 연기할 수 있게 구체적으로)
[장면 속 상황] 그 시점에 이 인물이 처한 상황과 고민, 그때의 감정 2~3개
[관계] 대화에 나올 만한 다른 인물·세력과의 관계와 그들에 대한 감정 2~4개
[말투] 이 인물다운 말투·말버릇·호칭 1~3개 (학생이 알아들을 수 있게, 예: 학생을 부르는 말, 자주 쓰는 표현)`;
}

const GUIDE_HEADS = ["1. 활동 개요", "2. 가상 인물의 설정과 성격", "3. 학생의 역할과 활동 목표", "4. 대화 진행 규칙", "5. 단계별 대화 진행 방식",
  "6. 학생의 발언에 대한 대응 원칙", "7. 학습 목표 달성 기준", "8. 대화 종료 조건", "9. 최종 피드백 및 결과 제시 방식", "10. 교과 내용의 정확성을 위한 유의 사항"];
const SYSTEM_G = `너는 한국 중·고등학교 선생님의 AI 역할극 수업 설계를 돕는 프롬프트 설계 도우미야. 선생님이 고른 설정과 '기본 지시문'을 바탕으로, 대화형 AI가 그대로 따를 수 있는 완성된 지시문을 쓴다.
규칙:
- 기본 지시문의 열 개 제목([1. 활동 개요] ~ [10. 교과 내용의 정확성을 위한 유의 사항])을 같은 순서, 같은 글자로 모두 남긴다.
- 각 항목을 이 인물·상황·학습 목표에 맞게 구체화한다. 예: 인물의 시대적 배경·이해관계·고민·예상 반론, 협상 쟁점과 양보할 수 있는 선, 핵심 개념과 흔한 오개념, 판정 기준의 구체적인 예.
- 기본 지시문의 규칙(학생이 먼저 말하게 하기, 대화 횟수와 단계, 지어내지 않기, 종료 조건, 최종 피드백 형식, 학생 지원 방식)은 빼거나 약하게 바꾸지 않는다.
- 확실하지 않은 사실(이름·날짜·수치·조약 조항·실험값)은 쓰지 않거나 '(선생님 확인 필요)'를 붙인다. 실제 발언을 인용하지 않는다.
- 특정 정당·현직 정치인을 지지하거나 반대하지 않는다. 혐오·차별·폭력을 부추기지 않는다.
- 각 항목은 '- '로 시작하는 개조식 문장으로 쓴다. 굵은 글씨·표·# 제목 같은 꾸밈은 쓰지 않는다.
- 전체 4,500자 이내. 지시문만 출력한다(머리말·맺음말·설명 없이).`;
function buildGuidePrompt(b: any) {
  return `[선생님이 고른 설정]
활동 유형: ${clip(b.type, 40)}
교과: ${clip(b.subject, 20)} / 대상 학생: ${clip(b.grade, 20)}
가상 인물 또는 역할: ${clip(b.role, 120)}${clip(b.name, 30) ? ` (화면 이름: ${clip(b.name, 30)})` : ""}
인물 소개: ${clip(b.about, 200) || "(없음)"}
대화 상황: ${clip(b.situation, 400)}
핵심 질문(학생 화면): ${clip(b.question, 300) || "(없음)"}
학생의 학습 목표: ${clip(b.goal, 400)}
최대 대화 횟수: 학생 발언 ${Math.max(1, Math.min(30, Number(b.turns) || 8))}회 / 학생 지원 방식: ${clip(b.support, 30)}

[기본 지시문 — 구조와 규칙은 지키고 내용을 이 수업에 맞게 구체화한다]
${String(b.base ?? "").slice(0, 7000)}`;
}

async function callGemini(key: string, model: string, body: unknown) {
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(20000),                    // 모델 하나가 20초 넘게 걸리면 다음으로
  }).catch(() => null);
  if (!r) return { status: 504, j: null };
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

  const test = b?.test === true, persona = b?.op === "persona", guide = b?.op === "guide";
  if (guide && (clip(b?.role, 120).length < 1 || String(b?.base ?? "").length < 100)) return json({ error: "empty" });
  if (persona && clip(b?.name, 30).length < 1) return json({ error: "empty" });
  if (!test && !persona && !guide && clip(b?.keywords, 200).length < 1) return json({ error: "empty" });
  const req_ = guide
    ? { systemInstruction: { parts: [{ text: SYSTEM_G }] }, contents: [{ role: "user", parts: [{ text: buildGuidePrompt(b) }] }], generationConfig: { temperature: b?.regen ? 0.9 : 0.5, maxOutputTokens: 8000 } }
    : persona
    ? { systemInstruction: { parts: [{ text: SYSTEM_P }] }, contents: [{ role: "user", parts: [{ text: buildPersonaPrompt(b) }] }], generationConfig: { temperature: 0.3, maxOutputTokens: 6000 } }
    : test
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
  const started = Date.now();
  for (const m of order) {
    if (Date.now() - started > 40000) { last = last === "ai_error" ? "timeout" : last; break; }   // 전체 40초 안에 끝낸다
    const { status, j } = await callGemini(row.gemini_key, m, req_);
    if (status === 200) {
      if (m !== row.model) await admin.from("teacher_ai").update({ model: m }).eq("uid", u!.user!.id);
      if (test) return json({ ok: true, model: m });
      if (guide) {
        const t = (j?.candidates?.[0]?.content?.parts ?? []).filter((p: any) => !p.thought).map((p: any) => p.text ?? "").join("").replace(/\*\*/g, "").replace(/^```\w*\n?|```$/g, "").trim().slice(0, 6000);
        if (!t || !GUIDE_HEADS.every((h) => t.includes(h))) { last = "ai_error"; continue; }   // 열 가지 제목이 빠지면 다음 모델로
        return json({ text: t, model: m });
      }
      if (persona) {
        const t = (j?.candidates?.[0]?.content?.parts ?? []).filter((p: any) => !p.thought).map((p: any) => p.text ?? "").join("").replace(/\*\*/g, "").trim().slice(0, 3000);
        if (!t) { last = "ai_error"; continue; }
        return json({ text: t, model: m });
      }
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
    if (status === 504) { last = "timeout"; continue; }
    if (status === 404 || status === 400) { last = last === "quota" ? "quota" : "ai_error"; continue; }
    last = "ai_error";
  }
  return json({ error: last, message: lastMsg });
});
