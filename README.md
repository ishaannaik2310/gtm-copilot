# GTM Ops Copilot

### AI that shows its work.

Type a company. Get a sales brief and cold outreach. Every sentence audited against a source. Every weak claim flagged.

[Try the live demo →](https://gtm-copilot-nine.vercel.app) · [Watch the 90-second walkthrough →](YOUR_VIDEO_URL)

---

## Here's the problem

Any AI can write a sales email. That's not impressive anymore. Everyone has that.

The problem is you can't trust it.

A made-up funding number. A pain point the company doesn't have. A "fact" the model invented because it sounded right. One of those in front of a real buyer and your rep looks like an idiot.

Most AI sales tools ignore this. They generate, you hope.

This one doesn't ask for your trust. It earns it.

---

## What you get

Two steps. One connected flow.

1. **Research & Qualify.** Give it a company name and URL. Four agents research the company, score it against your Ideal Customer Profile, and write the account brief: pain points, talk tracks, objection handling.
2. **Grounded Outreach.** One click carries the brief forward. Four email tones and a follow-up cadence, personalized to your contact. No re-typing.

Then the part nobody else does.

Every claim gets audited. Click any sentence and see the exact source text behind it. Each claim is labeled one of three ways:

| Label | Meaning |
|---|---|
| **Direct quote** | It's literally in the source. |
| **Reasonable inference** | Not stated, but it follows from cited facts. |
| **Unsupported** | No basis in the source. Flagged. |

No black box. You see what's true, what's inferred, and what isn't.

---

## Proof it works

Claims are cheap. Here's what the system actually caught while I built it:

- **It caught its own hallucination.** The research agent extracted the company name *"Notion Labs, Inc."* It looked precise and correct. The fact-checker proved that string wasn't in the scraped page. The model pulled it from memory. A generator can't catch that. A separate auditor can.
- **It exposed a bug I'd never have found by reading output.** First run: 43.8% faithfulness. The fact-checker was flagging real product names as unsupported. The cause wasn't the AI. I was silently truncating the evidence to 400 characters before the auditor saw it. Fixed the pipeline, changed zero prompts, same brief hit 100%.
- **It caught an email exaggerating a real number.** Source said reps lose 45 minutes per account. The email said "hours of manual research." The auditor flagged it as unsupported. A human proofreader would have missed it.

### It refuses to rubber-stamp

| Company | ICP verdict |
|---|---|
| **GitHub** | Poor fit (30%): too large, too mature for the target profile |
| **Notion** | Out of ICP (35%): late-stage market leader |

Ask it about a famous company and it won't flatter you. It tells you the account doesn't match, and why.

---

## The numbers

| Metric | Measurement |
|---|---|
| **Agents in the pipeline** | 4 (Research, ICP Classifier, Synthesis, Fact-Check) + Outreach |
| **Retrieval** | Hybrid: BM25 + vector search, fused with RRF, cross-encoder reranked |
| **Fact-check labels** | 3-way (direct, inference, unsupported) |
| **Faithfulness, first run** | 43.8% (a real bug) |
| **Faithfulness, after the fix** | 100% on the same brief |
| **Outreach audit (live run)** | 94.7% across 19 substantive claims, 1 correctly flagged |
| **Automated tests** | 80, every LLM call mocked, zero API cost to run |
| **CI** | GitHub Actions on Python 3.10, 3.11, 3.12 |
| **Secrets ever committed** | 0, verified across full git history |

---

## How it works

```
Company name + URL
      │
      ▼
Research Agent ---> scrapes the site, pulls playbook context
      │
      ▼
ICP Classifier ---> scores fit against your playbook, explains why
      │
      ▼
Synthesis Agent --> writes the account brief
      │
      ▼
Fact-Check Agent -> audits every claim, scores faithfulness
      │
      ▼ (you add a contact)
Outreach Agent ---> 4 tones + follow-up cadence
      │
      ▼
Fact-Check Agent -> audits the emails against the same evidence
```

**Failure is honest.** If a stage breaks, the system says so. If classification fails, the fit label reads "unknown," not a guessed score. If synthesis fails, the pipeline stops. It never fills a gap with a plausible fake.

**Retrieval is hybrid on purpose.** Vector search misses exact terms like product names and figures. Keyword search misses meaning. Fuse both with Reciprocal Rank Fusion, then rerank with a cross-encoder. Better than either alone.

---

## Who this is for

- Sales reps who need to trust what they send.
- RevOps teams who want AI output they can audit.
- Anyone who's been burned by a confident, wrong AI answer.

---

## What this is not

Not a CRM. Not a replacement for your judgment. Not a finished commercial product with paying customers. It's a working system built to prove one idea: **AI output should come with receipts.**

---

## Tech stack

- **Backend:** Python, FastAPI, ChromaDB, BM25, sentence-transformers, Gemini API
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Deploy:** Render (API) + Vercel (frontend)
- **Quality:** pytest, GitHub Actions

---

## Honest limits

Better you hear it from me.

- **The auditor checks facts, not logic.** A "reasonable inference" can pass because it cites real facts, even when the leap between them is weak. Judging reasoning quality is a hard, open problem in LLM evaluation. It's documented, not hidden.
- **No JavaScript rendering.** Heavily client-rendered sites return thin content. The system reports partial results and says so. It doesn't invent the rest.
- **Free-tier limits.** Each run makes several sequential LLM calls, and the free Gemini quota allows only a handful of full runs per day. The free Render instance also sleeps when idle, so the first request can take 30-60 seconds to wake up.
- **Scores vary run to run.** LLM output isn't deterministic. The numbers above are real measurements, not guarantees.

---

## Run it yourself

```bash
# Backend
pip install -e .
cp .env.example .env # add GEMINI_API_KEY (free: aistudio.google.com/apikey)
python run_dev.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

```bash
pytest tests/ -v # 80 tests, fully mocked, costs nothing
```

---

## The point

Making AI generate content is easy. Making it prove that content is true is the work.

That's what this is.

---

Built by Ishaan Naik. [GitHub](https://github.com/ishaannaik2310) · [LinkedIn](YOUR_LINKEDIN_URL)
