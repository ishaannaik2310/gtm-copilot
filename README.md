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

---

## 🧩 Data Models (Pydantic v2)
- **`Document`**: Represents a raw ingested document (`source_type`: `playbook`, `account_data`, or `web`).
- **`Chunk`**: Represents an indexed text chunk with metadata and optional embedding vector.
- **`Account`**: Represents a target account profile with domain, company name, and industry attributes.
