# GTM Ops Copilot

> An AI sales intelligence pipeline that doesn't just generate answers — it proves them.

Give it a company name or URL. It researches the company, scores it against your ICP, drafts a fact-checked account brief, and generates personalized outreach — with every claim traceable to a source and audited for whether it's actually true.

[**Live Demo →**](#) · [**Video Walkthrough →**](#)

---

## The Problem

Any LLM can write a plausible-sounding sales email or account summary. That's not the interesting problem anymore.

**The hard problem is: how do you know if any of it is true?**

Ungrounded LLM output for sales teams is a liability, not a tool — a hallucinated funding number or a fabricated pain point can embarrass a rep on a real call. Most "AI for sales" demos never address this at all.

This project is built around a different question: instead of just generating sales content, **can the system verify its own output, claim by claim, against real source evidence — and be honest when it can't?**

---

## What It Does

A two-stage connected funnel:

**1. Research & Qualify**

Given a company name or URL, a 4-agent pipeline:
- Researches the company via live web scraping and internal playbook grounding (hybrid retrieval)
- Scores it against your Ideal Customer Profile with an explained rationale
- Synthesizes a full account brief — pain points, talk tracks, objection handling
- Fact-checks every claim against source evidence before it's shown to you

**2. Grounded Outreach**

One click carries the verified brief forward — no re-entering data — into:
- 4 tonally distinct cold email variants
- A multi-touch follow-up cadence personalized to a specific contact
- Independent fact-checking of every outreach claim against the same source evidence

Every claim in every output is auditable in an interactive **Grounding Inspector** — see exactly which source text supports each sentence, and whether it's a direct quote, a reasoned inference, or (rarely, and always disclosed) unsupported.

---

## Architecture

```
Company Input
      │
      ▼
┌─────────────────┐    ┌──────────────────┐
│  Research Agent │───▶│  ICP Classifier  │
│  (live scrape + │    │  (scored against │
│  hybrid RAG)    │    │  playbook rules) │
└─────────────────┘    └──────────────────┘
      │
      ▼
┌──────────────────┐
│  Synthesis Agent │
│  (account brief) │
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Fact-Check Agent│──▶  Faithfulness score
│  (3-way audit)   │     + flagged claims
└──────────────────┘
      │
      ▼  (user selects a contact)
      │
      ▼
┌──────────────────┐
│  Outreach Agent  │───▶  Fact-Check Agent
│  (grounded email)│      (same 3-way audit)
└──────────────────┘
```

### Retrieval: Hybrid Search

Dense vector search (ChromaDB) + BM25 keyword search, fused via **Reciprocal Rank Fusion**, then re-ranked with a cross-encoder. Pure embedding similarity misses exact-term matches — product names, specific figures — that keyword search catches. RRF fusion + reranking consistently outperforms either method alone on retrieval-quality benchmarks.

### Fact-Checking: 3-Way Classification, Not Binary Pass/Fail

| Status | Meaning |
|---|---|
| `directly_supported` | Explicitly stated in source text |
| `reasonable_inference` | Not a direct quote, but a logical deduction from specific cited facts |
| `unsupported` | No basis in source material — the real hallucination signal |

This distinction exists because an earlier binary version conflated "not a literal quote" with "fabricated," which incorrectly flagged reasonable synthesis (e.g., inferring enterprise-sales complexity from evidence that a company is scaling upmarket) as if it were a hallucination.

---

## Why This Is Harder Than It Looks

The naive version is: "prompt an LLM to write a sales brief." That took an afternoon. The actual engineering work was making the output **trustworthy** — and testing revealed that trustworthiness is not a solved problem you get for free.

**Three real examples from development:**

### 1. A hallucinated legal entity name slipped past extraction — until fact-checking caught it
The Research Agent confidently extracted *"Notion Labs, Inc."* Fact-checking proved this specific string never appeared in the scraped source text — a subtle hallucination that looked like a great, precise extraction. This is exactly why verification exists as a separate, **adversarial** step rather than trusting the generator's own confidence.

### 2. A silent data-truncation bug was manufacturing false hallucination flags
Early runs showed a **43.8% faithfulness score** — the fact-checker was flagging real, correct facts as "unsupported." Root cause: the traceability data being fed to the fact-checker was silently truncated to 400 characters, while the generator had seen the full page. Fixing this took the same brief from **43.8% → 100% faithfulness with zero prompt changes** — the bug was in the pipeline, not the model.

### 3. A category-confusion bug had the system inventing pain points that weren't about the target company
The Synthesis Agent was pulling from the wrong section of the internal playbook — presenting "objections a buyer might raise about our tool" as if they were "pain points the target company experiences." Both were present in the source text, so the claims passed fact-checking as "supported." A good reminder that **faithfulness-to-source and conceptual-correctness are different properties**, and a system needs both.

---

## Tech Stack

| Layer | Stack |
|---|---|
| **Backend** | Python, FastAPI |
| **Retrieval** | ChromaDB (dense vector), BM25 (keyword), RRF fusion, sentence-transformers (cross-encoder reranking) |
| **LLM** | Gemini API |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **Testing / CI** | pytest (80+ tests, all LLM calls mocked), GitHub Actions across Python 3.10–3.12 |

---

## Known Limitations

Being upfront about what this system doesn't yet do well is part of the design, not an afterthought.

**Fact-checking validates fact presence, not logical soundness of inferences.** A `reasonable_inference` claim can pass if it cites real source facts, even if the logical connection between those facts and the conclusion is weak. Judging reasoning quality — not just fact presence — is a substantially harder problem and a known open challenge in LLM-as-judge evaluation.

**Web extraction doesn't render JavaScript.** Sites that are heavily client-rendered will return sparse or empty content. The system degrades gracefully — reporting partial results with explicit errors — rather than failing silently or hallucinating to fill the gap.

**Free-tier API rate limits constrain live usage.** The pipeline makes 4–5 sequential LLM calls per request. The current provider's free tier limits this to a small number of full runs per day. Production use would need a paid tier or response caching.

---

## Running Locally

```bash
# Backend
pip install -e .
cp .env.example .env          # add your GEMINI_API_KEY
python run_dev.py             # API on http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                   # UI on http://localhost:3000
```

Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

### Testing

```bash
pytest tests/ -v              # 80+ tests, fully mocked — no API calls, no cost
```

---

## Background

Built as a from-scratch exploration of RAG evaluation and multi-agent orchestration. The goal was to deeply understand retrieval, grounding, and verification — not to compete with production tools like RAGAS or DeepEval — and to find out what it actually takes to ship an LLM system where you'd trust the output on a live sales call.

---

<div align="center">
  <sub>Made with rigour, not vibes.</sub>
</div>
