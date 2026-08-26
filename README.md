# GTM Ops Copilot (v1)

An AI-powered tool that takes a target company URL and generates a researched, fact-checked account brief for sales reps, backed by a real RAG knowledge base of internal playbooks and sample account data.

---

## 🎯 Scope (v1)
- **Account Brief Generator**: Ingests playbooks and account data, chunks and indexes them in a local vector store, and performs grounded retrieval to assist sales representatives.
- Out of scope for v1: Outreach generation, automated call prep, and multi-agent workflow orchestration (deferred to later phases).

---

## 📁 Project Structure

```
gtm-copilot/
├── .github/workflows/ci.yml # CI pipeline
├── data/
│   ├── playbooks/           # Sales playbooks & battlecards (.md, .txt)
│   └── sample_accounts/     # Sample company profiles (.md, .txt)
├── gtm_copilot/
│   ├── __init__.py
│   ├── config.py            # Global settings & paths
│   ├── models.py            # Pydantic v2 data models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py        # Document loader for playbooks & accounts
│   │   └── chunker.py       # Text chunking with overlap & metadata
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── vector_store.py  # ChromaDB vector store wrapper
│   └── agents/              # Agent workflows (v1 placeholder)
├── tests/
│   ├── test_loader.py       # Unit tests for loader
│   └── test_chunker.py      # Unit tests for chunker
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install -e .
pip install pytest pytest-asyncio
```

### 2. Run Tests
```bash
pytest tests/ -v
```

### 3. Start Backend API Server
```bash
# Using development runner:
python run_dev.py

# Or via uvicorn directly:
uvicorn gtm_copilot.api.main:app --reload --port 8000
```
Interactive Swagger API documentation will be available at: `http://127.0.0.1:8000/docs`

### 4. Start Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```
The web dashboard will be available at: `http://localhost:3000`

---

## 🧩 Data Models (Pydantic v2)
- **`Document`**: Represents a raw ingested document (`source_type`: `playbook`, `account_data`, or `web`).
- **`Chunk`**: Represents an indexed text chunk with metadata and optional embedding vector.
- **`Account`**: Represents a target account profile with domain, company name, and industry attributes.

---

## Known Limitations

**Fact-checking catches fabrication, not weak reasoning.** The FactCheckAgent distinguishes three claim types: directly stated in source text, reasonable inference from grounded facts, and unsupported/fabricated. This reliably catches claims with no basis in the source material — during development it correctly flagged a hallucinated legal entity name and caught pain points that were actually mislabeled objection-handling content from the wrong section of the playbook.

However, it does not yet evaluate the *logical soundness* of an inference — only whether the cited supporting facts are real. A claim can pass as "reasonable_inference" if it cites genuine source facts, even if the logical connection between those facts and the conclusion is weak (e.g. "our playbook cares about X, therefore this company struggles with X" is a non-sequitur that can still pass because the cited facts are real). Judging reasoning quality, not just fact presence, is a substantially harder problem — this is a known open challenge in LLM-as-judge evaluation generally, not specific to this implementation.

**Future work:** a dedicated logical-consistency check, or a second-pass "steelman the opposite" prompt that tries to argue against each inference before accepting it.
