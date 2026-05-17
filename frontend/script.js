const BASE = "https://product-insights-copilot-production.up.railway.app";

// ── helpers ────────────────────────────────────────────────────────────────
function setResult(id, text, state = "") {
  const el = document.getElementById(id);
  el.innerText = text;
  el.classList.remove("loading", "error", "success");
  if (state) el.classList.add(state);
}

function flatten(result) {
  // result is an array of content blocks from the MCP tool
  // each block may be { type:"text", text:"…" } or a plain string
  if (!Array.isArray(result)) return JSON.stringify(result, null, 2);
  return result
    .map(b => (typeof b === "string" ? b : b.text ?? JSON.stringify(b)))
    .join("\n");
}

function normalizePulseSum(sum) {
  if (sum == null) return null;
  if (typeof sum === "object") return sum;
  if (typeof sum !== "string") return null;

  const trimmed = sum.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const match = trimmed.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
}

function formatPulseParagraph(sum) {
  const data = normalizePulseSum(sum);
  if (!data) return typeof sum === "string" ? sum.replace(/^Sum:\s*/i, "").trim() : "";

  const parts = [];
  const { theme_intelligence: themes, weekly_pulse: pulse, fee_explainer: fees } = data;

  if (pulse?.summary) parts.push(pulse.summary.trim());
  if (pulse?.observation) parts.push(pulse.observation.trim());

  if (!pulse?.summary && themes?.top_3_themes?.length) {
    const themeLine = themes.top_3_themes
      .map(t => `${t.name} (${t.pct_of_total}, ${t.review_count} reviews)`)
      .join(", ");
    parts.push(`Leading themes this period: ${themeLine}.`);
  }

  if (pulse?.action_ideas?.length) {
    const actions = pulse.action_ideas.map(a => a.replace(/\.\s*$/, "").trim()).join("; ");
    parts.push(`Recommended actions include ${actions}.`);
  }

  if (fees?.identified_issue) parts.push(fees.identified_issue.trim());

  if (fees?.explanation_bullets?.length) {
    parts.push(fees.explanation_bullets.join(" "));
  }

  if (fees?.sources?.length) {
    parts.push(`Sources: ${fees.sources.join(", ")}.`);
  }

  if (fees?.last_checked) {
    parts.push(`Fee information last checked ${fees.last_checked}.`);
  }

  return parts.join(" ");
}

// ── Weeks slider display ─────────────────────────────────────────────────────
const weeksInput = document.getElementById("weeks");
const weeksValue = document.getElementById("weeksValue");
weeksInput.addEventListener("input", () => {
  weeksValue.textContent = weeksInput.value;
});

// ── 1. Pulse / Adder ───────────────────────────────────────────────────────
document.getElementById("addBtn").addEventListener("click", async () => {
  const num1 = Number(document.getElementById("weeks").value);
  const num2 = Number(document.getElementById("maxRating").value);
  const num3 = Number(document.getElementById("minRating").value);

  setResult("result", "Calculating…", "loading");
  try {
    const res  = await fetch(`${BASE}/get_pulse_data`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ num1, num2, num3 }),
    });
    const data = await res.json();
    const paragraph = formatPulseParagraph(data.sum);
    setResult("result", paragraph || "No insights returned.", "success");
  } catch (err) {
    setResult("result", `Error: ${err.message}`, "error");
  }
});

// ── 2. Append to Google Doc ────────────────────────────────────────────────
document.getElementById("docBtn").addEventListener("click", async () => {
  const document_id = document.getElementById("docId").value.trim();
  const text = document.getElementById("result").innerText.trim();
  console.log(text)

  if (!document_id) {
    setResult("docResult", "Please enter a Doc ID.", "error");
    return;
  }

  setResult("docResult", "Appending…", "loading");
  try {
    const res  = await fetch(`${BASE}/mcp/append_to_doc`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ document_id, text }),
    });
    const data = await res.json();
    setResult("docResult", flatten(data.result), "success");
  } catch (err) {
    setResult("docResult", `Error: ${err.message}`, "error");
  }
});

// ── 3. Create Gmail Draft ──────────────────────────────────────────────────
document.getElementById("mailBtn").addEventListener("click", async () => {
  const to      = document.getElementById("emailTo").value.trim();
  const body = document.getElementById("result").innerText.trim();

  if (!to) {
    setResult("mailResult", "Please enter a recipient email.", "error");
    return;
  }

  setResult("mailResult", "Creating draft…", "loading");
  try {
    const res  = await fetch(`${BASE}/mcp/create_email_draft`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ to, body }),
    });
    const data = await res.json();
    setResult("mailResult", flatten(data.result), "success");
  } catch (err) {
    setResult("mailResult", `Error: ${err.message}`, "error");
  }
});
