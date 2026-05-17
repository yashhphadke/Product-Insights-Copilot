from groq import Groq
from dotenv import load_dotenv
import pandas as pd
import os
import json
from pulse_generation.clustering import get_clusters

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"


# ── Load & prepare data ───────────────────────────────────────────────────────
def get_pulse(week,min_rate,max_rate):
  df = get_clusters(week,min_rate,max_rate)

  # Top 3 clusters (exclude noise cluster -1)
  top_3_ids = (df[df["cluster"] != -1]["cluster"].value_counts().head(3).index.tolist())

  cluster_payload = [
      {
          "cluster_id": int(cid),
          "review_count": int(len(df[df["cluster"] == cid])),
          "reviews": (
              df[df["cluster"] == cid]
              .sort_values("cluster_confidence", ascending=False)["review"]
              .dropna()
              .astype(str)
              .head(15)
              .tolist()
          ),
      }
      for cid in top_3_ids
  ]

  # Fee-related reviews
  FEE_KEYWORDS = [
      "fee", "fees", "charge", "charges", "brokerage",
      "exit load", "deduction", "deducted", "commission",
      "hidden charges", "cost", "pricing", "extra money", "tax", "gst",
  ]
  fee_reviews = (
      df[df["review"].str.lower().str.contains("|".join(FEE_KEYWORDS), na=False)]
      [["review", "rating"]]
      .head(30)
      .to_dict(orient="records")
  )

  # Pricing reference data
  with open("./data/groww_pricing.json", "r", encoding="utf-8") as f:
      pricing_data = json.load(f)


  # ── Single unified prompt ─────────────────────────────────────────────────────

  prompt = f"""
  You are an expert Principal Product Analyst and User Intelligence Specialist.

  Analyse the provided customer reviews and pricing data, then produce a single
  structured report covering three sections.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SECTION 1 — THEME INTELLIGENCE
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  From the cluster data:
  - Identify the TOP 3 themes by frequency and negative severity.
  - Calculate each theme's percentage of total reviews.
  - Extract EXACTLY 3 verbatim quotes that support those themes.
    Rules: no PII (names, emails, phone numbers, account IDs),
    do NOT alter spelling, punctuation, or casing.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SECTION 2 — WEEKLY PRODUCT PULSE  (≤250 words total)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Using the themes from Section 1 write a concise executive brief:

  - summary      : overall sentiment + top 3 themes with % breakdowns
  - observation  : WHY this trend is occurring — structural, UX, pricing,
                  or system failures
  - action_ideas : EXACTLY 3 engineering-ready, implementation-specific
                  product improvements (no vague suggestions)

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SECTION 3 — FEE EXPLAINER  (derived directly from user confusion)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Using the fee reviews AND the official pricing data:
  - Identify the SINGLE most recurring fee-related confusion users have.
  - Write ≤6 bullet points that clarify the fee in a neutral, facts-only tone.
  - Use the pricing data to ground every fact — do NOT invent numbers.
  - Add 2 official source links relevant to the confusion.
  - Add a last_checked field with today's date (2026-05-17).
  - Extract 2 verbatim supporting quotes from the fee reviews (no PII).

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OUTPUT RULES
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Return ONLY a single valid JSON object. No markdown, no code fences,
  no explanations outside the JSON.

  JSON SCHEMA:
  {{
    "theme_intelligence": {{
      "top_3_themes": [
        {{"name": "Theme A", "review_count": 0, "pct_of_total": "0%"}},
        {{"name": "Theme B", "review_count": 0, "pct_of_total": "0%"}},
        {{"name": "Theme C", "review_count": 0, "pct_of_total": "0%"}}
      ],
      "supporting_quotes": [
        {{"text": "verbatim quote 1", "star_rating": 1}},
        {{"text": "verbatim quote 2", "star_rating": 2}},
        {{"text": "verbatim quote 3", "star_rating": 1}}
      ]
    }},
    "weekly_pulse": {{
      "summary": "≤250-word executive summary",
      "observation": "Root-cause explanation",
      "action_ideas": [
        "Engineering-ready improvement 1",
        "Engineering-ready improvement 2",
        "Engineering-ready improvement 3"
      ]
    }},
    "fee_explainer": {{
      "identified_issue": "Single most recurring fee confusion",
      "explanation_bullets": [
        "Bullet 1",
        "Bullet 2",
        "Bullet 3",
        "Bullet 4",
        "Bullet 5",
        "Bullet 6"
      ],
      "supporting_quotes": [
        "verbatim fee quote 1",
        "verbatim fee quote 2"
      ],
      "sources": [
        "https://official-link-1.com",
        "https://official-link-2.com"
      ],
      "last_checked": "2026-05-17"
    }}
  }}

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INPUT DATA
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ### CLUSTER DATA
  {json.dumps(cluster_payload, indent=2)}

  ### FEE-RELATED REVIEWS
  {json.dumps(fee_reviews, indent=2)}

  ### OFFICIAL PRICING DATA
  {json.dumps(pricing_data, indent=2)}
  """


  # ── Single LLM call ───────────────────────────────────────────────────────────

  response = client.chat.completions.create(
      model=MODEL_NAME,
      temperature=0.2,
      response_format={"type": "json_object"},
      messages=[
          {
              "role": "system",
              "content": (
                  "You are an expert product intelligence analyst. "
                  "Return only valid JSON with no extra text."
              ),
          },
          {"role": "user", "content": prompt},
      ],
  )

  result = json.loads(response.choices[0].message.content)

  final = json.dumps(result, indent=2)

  print("Prompt tokens:", response.usage.prompt_tokens)
  print("Completion tokens:", response.usage.completion_tokens)
  print("Total tokens:", response.usage.total_tokens)
  return final