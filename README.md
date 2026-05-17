# Product Insights Copilot

An AI-powered workflow that turns raw customer reviews into structured product intelligence, a weekly internal pulse, and a fee clarification — then lets a human approve before logging insights to Google Docs and creating a Gmail draft via MCP (Model Context Protocol).

Built for the **Groww** investing app as the target product, using public Play Store reviews and official pricing pages as grounding data.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Component Reference](#component-reference)
   - [Frontend](#frontend)
   - [Backend API](#backend-api)
   - [Pulse Generation](#pulse-generation)
   - [Data Ingestion](#data-ingestion)
   - [MCP Layer](#mcp-layer)
   - [Data Assets](#data-assets)
5. [Human Approval Gate](#human-approval-gate)
6. [Prerequisites](#prerequisites)
7. [Setup](#setup)
8. [How to Run](#how-to-run)
9. [API Reference](#api-reference)
10. [Environment Variables](#environment-variables)
11. [Google OAuth (MCP Tools)](#google-oauth-mcp-tools)
12. [Typical Workflow](#typical-workflow)
13. [Fee Issue Detection](#fee-issue-detection)
14. [Troubleshooting](#troubleshooting)
15. [Related Documents](#related-documents)

---

## What It Does

| Step | Capability |
|------|------------|
| **1. Review intelligence** | Clusters reviews into themes (UMAP + HDBSCAN), surfaces top 3 themes, extracts quotes, detects fee-related confusion |
| **2. Weekly product pulse** | LLM generates ≤250-word executive brief: summary, observation, 3 action ideas |
| **3. Fee explainer** | Neutral, facts-only bullets grounded in official pricing JSON + user quotes |
| **4. Approval-gated MCP** | User reviews output in UI, then explicitly triggers Doc append or Gmail draft |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         frontend/ (Browser UI)                          │
│  Weeks slider · Rating filters · Insight panel · Doc / Gmail actions    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP (127.0.0.1:8000)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      backend/main.py (FastAPI)                          │
│  POST /get_pulse_data  ·  POST /mcp/append_to_doc  ·  POST /mcp/...     │
└───────┬─────────────────────────────────────┬───────────────────────────┘
        │                                     │ stdio MCP transport
        ▼                                     ▼
┌───────────────────────┐           ┌───────────────────────┐
│ pulse_generation/     │           │ mcp/server.py         │
│ clustering + LLM      │           │ FastMCP tools         │
└───────────┬───────────┘           └───────────┬───────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────┐           ┌───────────────────────┐
│ data/review.csv       │           │ Google Docs + Gmail   │
│ data/embeddings.npy   │           │ APIs (OAuth)          │
│ data/groww_pricing.json│          └───────────────────────┘
└───────────────────────┘
            ▲
            │ produced by
┌───────────────────────┐
│ ingestion/            │
│ scrape · embed        │
└───────────────────────┘
```

**LLM provider:** [Groq](https://groq.com/) (`meta-llama/llama-4-scout` for pulse, `openai/gpt-oss-120b` for MCP chat routing).

---

## Project Structure

```
Product Insights Copilot/
├── frontend/                 # Static web UI
│   ├── index.html            # Layout, controls, insight panel
│   ├── style.css             # Minimalist design system
│   └── script.js             # API calls, JSON → paragraph formatter
│
├── backend/                  # FastAPI application
│   └── main.py               # REST endpoints, MCP client, CORS
│
├── pulse_generation/         # Core intelligence pipeline
│   ├── clustering.py         # UMAP + HDBSCAN on review embeddings
│   └── pulsegenerator.py     # LLM prompt + structured JSON output
│
├── ingestion/                # Offline data preparation
│   ├── ingestor.py           # Orchestrates scrape → embed pipeline
│   ├── review_scraper.py     # Google Play reviews → review.csv
│   └── fee_scrape.py         # Groww pricing pages → groww_pricing.json
│
├── mcp/                      # Model Context Protocol tools
│   ├── server.py             # FastMCP server (add, Gmail, Docs)
│   ├── client.py             # Standalone LLM → MCP demo script
│   ├── doc_append.py         # Standalone Google Docs append utility
│   └── mail_draft.py         # Standalone Gmail draft utility
│
├── data/                     # Runtime data (generated or committed)
│   ├── review.csv            # Cleaned reviews (date, rating, review, …)
│   ├── embeddings.npy        # Sentence-transformer vectors per row
│   └── groww_pricing.json    # Scraped official fee/pricing text
│
├── architecture.md           # High-level design document
├── problemstatement.md       # Milestone requirements
├── credentials.json          # Google OAuth client secrets (not committed)
├── token.pkl                 # Cached OAuth token (generated locally)
├── .env                      # API keys (GROQ_API_KEY)
└── README.md                 # This file
```

---

## Component Reference

### Frontend

The UI is a **vanilla HTML/CSS/JS** app opened directly in the browser (no build step). It talks to the FastAPI backend at `http://127.0.0.1:8000`.

| File | Role |
|------|------|
| **`index.html`** | Page structure: header, two-column workspace (sidebar + insight panel), three action cards |
| **`style.css`** | Design tokens, glass cards, slider/select styling, responsive grid |
| **`script.js`** | All client logic |

#### UI sections

| Section | Controls | Behavior |
|---------|----------|----------|
| **Pulse Calculator** | Weeks slider (1–8), Max ratings dropdown (1–5), Min ratings dropdown (1–5) | Calls `POST /get_pulse_data` with `{ num1, num2, num3 }` |
| **Insight panel** (right) | Read-only `#result` | Displays a single paragraph parsed from the API JSON |
| **Append to Google Doc** | Document ID input | Sends current insight text to `POST /mcp/append_to_doc` |
| **Create Gmail Draft** | Recipient email | Sends insight as body to `POST /mcp/create_email_draft` |

#### Key JavaScript functions

| Function | Purpose |
|----------|---------|
| `setResult(id, text, state)` | Updates an `<output>` element; applies `loading` / `success` / `error` CSS classes |
| `normalizePulseSum(sum)` | Parses `data.sum` whether it arrives as a JSON object or string |
| `formatPulseParagraph(sum)` | Flattens `theme_intelligence`, `weekly_pulse`, and `fee_explainer` into one readable paragraph |
| `flatten(result)` | Converts MCP tool result blocks to plain text for doc/mail status messages |

#### Layout

- **Left column (~340px):** All interactive cards
- **Right column (flex):** Sticky **Insight** panel with the formatted pulse paragraph
- On screens &lt; 860px, the insight panel stacks above the controls

---

### Backend API

**File:** `backend/main.py`

FastAPI app that exposes the pulse pipeline and proxies MCP tool calls.

| Responsibility | Details |
|----------------|---------|
| **CORS** | Allows all origins so the static frontend can call the API from `file://` or a local server |
| **Pulse endpoint** | Accepts `num1` (weeks), `num2`, `num3` (rating bounds) → calls `get_pulse()` |
| **MCP client** | Spawns `mcp/server.py` via `PythonStdioTransport` for each MCP request |
| **NL chat** | `POST /mcp/chat` uses Groq to pick a tool + args, then invokes it (optional; not wired in current UI) |

#### Pydantic models

| Model | Fields | Used by |
|-------|--------|---------|
| `Numbers` | `num1`, `num2`, `num3` | `/get_pulse_data` |
| `DocRequest` | `document_id`, `text` | `/mcp/append_to_doc` |
| `EmailRequest` | `to`, `body` | `/mcp/create_email_draft` |
| `ChatRequest` | `message` | `/mcp/chat` |

---

### Pulse Generation

The intelligence core: filter reviews → cluster → LLM → structured JSON.

#### `pulse_generation/clustering.py`

| Function | `get_clusters(week, min_rating, max_rating)` |
|----------|---------------------------------------------|
| **Input** | Lookback window in weeks; star-rating inclusive range |
| **Data** | Reads `data/review.csv`, slices rows by `date` and `rating` |
| **Embeddings** | Loads precomputed `data/embeddings.npy`, indexes by filtered row positions |
| **Clustering** | UMAP (5D, cosine) → HDBSCAN (`min_cluster_size=5`) |
| **Output** | DataFrame with `cluster`, `cluster_confidence`, and original columns |

Cluster `-1` is noise and excluded when picking top themes.

#### `pulse_generation/pulsegenerator.py`

| Function | `get_pulse(week, min_rate, max_rate)` |
|----------|----------------------------------------|
| **Step 1** | Calls `get_clusters()` |
| **Step 2** | Builds payload: top 3 clusters (up to 15 reviews each) + fee-keyword reviews |
| **Step 3** | Loads `data/groww_pricing.json` for grounded fee facts |
| **Step 4** | Single Groq LLM call (`meta-llama/llama-4-scout-17b-16e-instruct`, `response_format: json_object`) |
| **Output** | JSON string with three top-level keys (see schema below) |

#### API response schema (`data.sum`)

```json
{
  "theme_intelligence": {
    "top_3_themes": [
      { "name": "High Charges", "review_count": 11, "pct_of_total": "34%" }
    ],
    "supporting_quotes": [
      { "text": "verbatim user quote", "star_rating": 2 }
    ]
  },
  "weekly_pulse": {
    "summary": "Executive summary (≤250 words)",
    "observation": "Root-cause / trend analysis",
    "action_ideas": ["Action 1", "Action 2", "Action 3"]
  },
  "fee_explainer": {
    "identified_issue": "Most recurring fee confusion",
    "explanation_bullets": ["Bullet 1", "…", "Bullet 6"],
    "supporting_quotes": ["quote 1", "quote 2"],
    "sources": ["https://groww.in/pricing/stocks", "…"],
    "last_checked": "2026-05-17"
  }
}
```

The frontend’s `formatPulseParagraph()` turns this into one continuous paragraph for the Insight panel and for Doc/Gmail actions.

---

### Data Ingestion

Offline pipeline to refresh reviews, pricing, and embeddings. Run from the **project root** when you need fresh data.

#### `ingestion/ingestor.py`

Orchestrator entry point:

1. `review_scraper()` → writes `data/review.csv`
2. `fee_scraper()` → writes `data/groww_pricing.json`
3. Embeds all reviews with `sentence-transformers/all-MiniLM-L6-v2` → `data/embeddings.npy`

```bash
python -m ingestion.ingestor
# or, from ingestion/ directory:
python ingestor.py
```

#### `ingestion/review_scraper.py`

| Detail | Value |
|--------|-------|
| **Source** | Google Play (`google-play-scraper`) |
| **App** | `com.nextbillion.groww` |
| **Volume** | Up to ~15,000 newest reviews |
| **Cleaning** | English-only (`langdetect`), min 6 words, emoji removal, URL strip, lowercase |
| **Output columns** | `user`, `rating`, `review`, `date` |

#### `ingestion/fee_scrape.py`

| Detail | Value |
|--------|-------|
| **Sources** | Groww pricing pages (stocks, F&O, mutual funds) |
| **Method** | `requests` + BeautifulSoup, noise filtering via regex |
| **Output** | `data/groww_pricing.json` — structured pricing snippets for LLM grounding |

---

### MCP Layer

[MCP](https://modelcontextprotocol.io/) exposes tools that the backend (or `mcp/client.py`) can invoke after human approval.

#### `mcp/server.py` — FastMCP server

| Tool | Arguments | Action |
|------|-----------|--------|
| `add` | `a`, `b` | Demo arithmetic tool |
| `create_email_draft` | `to`, `subject`, `body` | Creates an **unsent** Gmail draft via Gmail API |
| `append_to_doc` | `document_id`, `text` | Inserts text at end of a Google Doc |

**Auth:** Shared `get_creds()` loads/refreshes OAuth from `credentials.json` + `token.pkl`.

**Scopes:**

- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/documents`

Run standalone for debugging:

```bash
python mcp/server.py
```

#### `mcp/client.py`

Standalone script demonstrating the full **LLM → parse tool JSON → MCP call** flow without the web UI. Edit `user_input` at the bottom of `main()` to test different intents.

#### `mcp/doc_append.py` & `mcp/mail_draft.py`

Earlier standalone utilities for Google Docs and Gmail. Functionality is consolidated into `mcp/server.py`; these files remain as reference implementations.

---

### Data Assets

| File | Description |
|------|-------------|
| **`data/review.csv`** | Historical Play Store reviews; required for clustering |
| **`data/embeddings.npy`** | NumPy array of shape `(n_reviews, 384)` — must align with CSV row order |
| **`data/groww_pricing.json`** | Scraped pricing/fee text used to prevent hallucinated numbers in the fee explainer |

> **Important:** If you regenerate `review.csv`, you must re-run embedding generation so `embeddings.npy` row indices still match the CSV.

---

## Human Approval Gate

The system **never** auto-appends to Docs or auto-sends email.

1. User clicks **Generate Insights** and reads the full paragraph in the Insight panel.
2. User explicitly clicks **Append to doc** or **Create draft** — this is the approval step.
3. Only then does the backend invoke MCP tools against Google APIs.

There is no background automation; partial failures are shown in the small status boxes under each action card.

---

## Prerequisites

- **Python 3.11+** (project tested with 3.11)
- **Groq API key** — [console.groq.com](https://console.groq.com/)
- **Google Cloud project** with Gmail + Google Docs APIs enabled (for MCP tools)
- **OAuth client** — download `credentials.json` to the project root
- Modern browser (Chrome, Edge, Firefox)

---

## Setup

### 1. Clone and create a virtual environment

```bash
cd "Product Insights Copilot"
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

If you have an existing `venv`, activate it. Otherwise install the packages used by the project:

```bash
pip install fastapi uvicorn groq fastmcp python-dotenv pandas numpy \
  umap-learn hdbscan sentence-transformers google-play-scraper \
  langdetect presidio-analyzer beautifulsoup4 requests emoji \
  google-auth-oauthlib google-api-python-client
```

### 3. Configure environment

Create `.env` in the project root (or `backend/.env` depending on where you run the server):

```env
GROQ_API_KEY=your_groq_api_key_here
```

`pulse_generation/pulsegenerator.py` loads `.env` from the current working directory; run the backend from the **project root** so paths like `./data/review.csv` resolve correctly.

### 4. Prepare data (first time or refresh)

Ensure `data/review.csv` and `data/embeddings.npy` exist. To rebuild from scratch:

```bash
python ingestion/ingestor.py
```

### 5. Google OAuth

1. Place `credentials.json` (OAuth 2.0 Desktop client) in the project root.
2. The first MCP tool call opens a browser window to authorize.
3. A `token.pkl` file is created for subsequent runs.

---

## How to Run

### Terminal 1 — Backend

From the **project root**:

```bash
venv\Scripts\activate          # Windows
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Verify: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI).

### Terminal 2 — Frontend

Open `frontend/index.html` in your browser:

- Double-click the file, or
- `start frontend/index.html` (Windows), or
- Serve statically: `python -m http.server 5500` then visit `http://localhost:5500/frontend/`

The footer shows `Connected to 127.0.0.1:8000` — the API must be running first.

### Optional — MCP client demo

```bash
python mcp/client.py
```

---

## API Reference

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/get_pulse_data` | `{ "num1": 4, "num2": 3, "num3": 5 }` | `{ "sum": "<JSON string>" }` |
| `GET` | `/mcp/tools` | — | List of registered MCP tools |
| `POST` | `/mcp/chat` | `{ "message": "…" }` | `{ "tool", "arguments", "result" }` |
| `POST` | `/mcp/append_to_doc` | `{ "document_id": "…", "text": "…" }` | `{ "result": […] }` |
| `POST` | `/mcp/create_email_draft` | `{ "to": "…", "body": "…" }` | `{ "result": […] }` |

### Request field mapping (Pulse Calculator)

| UI control | JSON field | Backend parameter | Effect |
|------------|------------|-------------------|--------|
| Weeks slider (1–8) | `num1` | `week` | Reviews from the last N weeks |
| Max ratings dropdown | `num2` | `min_rating` | Lower bound on star rating (inclusive) |
| Min ratings dropdown | `num3` | `max_rating` | Upper bound on star rating (inclusive) |

Only reviews with `min_rating ≤ rating ≤ max_rating` are included in clustering.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | API key for Groq LLM calls (pulse + MCP chat) |

---

## Google OAuth (MCP Tools)

| File | Purpose |
|------|---------|
| `credentials.json` | OAuth client ID/secret from Google Cloud Console |
| `token.pkl` | Cached refresh token (auto-generated; add to `.gitignore`) |

**Enable APIs:** Gmail API, Google Docs API.

**Redirect:** Desktop app flow (`InstalledAppFlow.run_local_server`).

**Gmail draft subject** is set server-side to: `Weekly Pulse Report + Fee Clarification`.

---

## Typical Workflow

1. **Start** `uvicorn` backend.
2. **Open** `frontend/index.html`.
3. Set **Weeks** (e.g. 4), **Max/Min ratings** to focus on low-star feedback (e.g. 1–3).
4. Click **Generate Insights** — wait for the LLM (may take 15–60 seconds).
5. **Read** the Insight panel (summary, actions, fee explanation in one paragraph).
6. *(Optional)* Paste a Google Doc ID → **Append to doc**.
7. *(Optional)* Enter recipient email → **Create draft** (check Gmail Drafts folder).

---

## Fee Issue Detection

Fee confusion is identified in two ways before the LLM runs:

1. **Keyword filter** in `pulsegenerator.py` — reviews containing terms like `fee`, `brokerage`, `charges`, `GST`, etc.
2. **LLM synthesis** — `fee_explainer.identified_issue` must reflect the most recurring confusion in those reviews, with bullets grounded in `groww_pricing.json`.

Example output from real review data:

- **Theme:** High Charges (~34% of filtered reviews)
- **Fee issue:** Users confused about brokerage and depository charges on stock trades
- **Sources:** [groww.in/pricing/stocks](https://groww.in/pricing/stocks), [groww.in/pricing/futures-and-options](https://groww.in/pricing/futures-and-options)

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| `Failed to fetch` in browser | Backend not running | Start `uvicorn` on port 8000 |
| `FileNotFoundError: review.csv` | Missing data | Run `ingestion/ingestor.py` or add CSV manually |
| Embedding index mismatch | CSV changed without re-embedding | Re-run `ingestor.py` |
| MCP / Google auth errors | Missing or expired `token.pkl` | Delete `token.pkl`, re-authorize |
| Empty clusters / poor themes | Too few reviews after filters | Widen weeks or rating range |
| CORS issues | Rare with current config | Backend already sets `allow_origins=["*"]` |
| `GROQ_API_KEY` errors | Missing `.env` | Add key and restart uvicorn |

---

## Related Documents

| File | Contents |
|------|----------|
| [`architecture.md`](architecture.md) | Layered system design, sequence diagram, JSON schemas |
| [`problemstatement.md`](problemstatement.md) | Milestone requirements and deliverables checklist |

---

## License

Academic / milestone project — adjust license as needed for your submission.
