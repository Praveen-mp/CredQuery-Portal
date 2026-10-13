# LangChain Learning

Learning LangChain by building a progressive series of small, runnable scripts —
each one introduces one concept on top of the last. Using Azure OpenAI as the model provider.

> **Note:** the multi-database agent work (formerly "Track B" below, in `app/`)
> has graduated into its own standalone, open-source-ready product at
> [`dbchat/`](dbchat/) — a self-hosted package with its own `pyproject.toml`,
> Docker image, and plugin architecture for database adapters. See
> [dbchat/README.md](dbchat/README.md). `app/` is kept here for reference but
> is superseded.

## Setup

```bash
uv sync
```

Credentials live in `.env` (gitignored, see `.env.example` for the shape):

```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=
```

Run any example with:

```bash
uv run python examples/01_hello_llm.py
```

## Roadmap

Reordered for interview prep — RAG and LCEL fundamentals first since they're the
most commonly probed LangChain/LLM-systems topics, deeper agent patterns later.

| # | File | Concept | Status |
|---|------|---------|--------|
| 01 | `01_hello_llm.py` | `init_chat_model`, custom `@tool`, `create_agent` (tool-calling agent) | ✅ done (out of order, kept as-is) |
| 02 | `02_prompt_templates.py` | `ChatPromptTemplate` + LCEL (`prompt \| llm \| parser`) | next |
| 03 | `03_document_loading_splitting.py` | Loaders + text splitters, chunking strategy tradeoffs | |
| 04 | `04_embeddings_vectorstore.py` | Embeddings + Chroma vector store, similarity search | |
| 05 | `05_rag.py` | Full retrieval-augmented generation pipeline + retriever chain | |
| 06 | `06_structured_output.py` | Structured/typed output with Pydantic (`with_structured_output`) | |
| 07 | `07_memory_state.py` | Multi-turn state via LangGraph checkpointer (not legacy `Memory` classes) | |
| 08 | `08_evaluation_observability.py` | LangSmith tracing + eval basics | |
| 09+ | stretch | Multi-agent / human-in-the-loop LangGraph patterns | later |

Each step: I explain the concept + relevant API, you write the script, I review.

## Track B: Multi-Database Agent

A separate capstone — a text-to-SQL/NoSQL agent that queries your actual
Postgres, MySQL, and MongoDB instances live, rather than retrieving from
pre-embedded content. Lives entirely under `app/`, structured as a small
layered application rather than flat scripts, since this track is meant to
grow (more DBs, more tools) and demonstrate production-ish practices.

```
app/
├── streamlit_app.py     # UI only — no business logic
├── core/
│   └── config.py        # typed settings (pydantic-settings), loads .env once
├── db/
│   └── postgres.py      # connection factory, one per data source (mysql.py, mongo.py later)
├── security/
│   ├── sql_guard.py      # rejects anything that isn't a single read-only SELECT/WITH
│   └── rate_limiter.py   # in-memory sliding-window limiter, per session
└── agents/
    └── postgres_agent.py # builds the agent + its guarded tools
```

| # | File | Concept | Status |
|---|------|---------|--------|
| B1 | `app/agents/postgres_agent.py` | `SQLDatabase` + custom guarded tools, single-DB SQL agent | ✅ done |
| B2 | `app/db/mysql.py` + `app/agents/mysql_agent.py` | Same pattern, second SQL source | next |
| B3 | `app/db/mongo.py` + `app/agents/mongo_agent.py` | Custom `pymongo` tools (list/sample/query) for a schemaless source | |
| B4 | `app/agents/orchestrator.py` | Router agent that delegates across all three sub-agents | |

**Safety for this track:**
- Every DB connection must use a read-only (`SELECT`-only) DB user — the agent never holds write credentials. This is the primary boundary.
- `security/sql_guard.py` is a defense-in-depth layer on top of that: every LLM-generated query is parsed and rejected unless it's a single `SELECT`/`WITH` statement with no mutating keywords and no stacked statements (`SELECT 1; DROP ...`). The agent's query tool calls this guard before touching the database — it never executes raw LLM output directly.
- `security/rate_limiter.py` caps requests per Streamlit session (`RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` in `.env`, default 10 per 60s). It's in-memory and process-local — correct for one running instance, but if this is ever deployed across multiple replicas, swap it for a shared store (Redis `INCR`+`EXPIRE`) since each replica would otherwise get its own independent counter.

### UI

`app/streamlit_app.py` is the primary way to interact with this track.

```bash
uv add streamlit
uv run streamlit run app/streamlit_app.py
```

### Debugging (VS Code)

`.vscode/launch.json` has three configs, reachable from the Run and Debug panel:
- **Debug: Current file** — runs whatever file is open, with breakpoints
- **Debug: Postgres agent (CLI)** — runs `app/postgres_agent.py` directly
- **Debug: Streamlit app** — launches Streamlit under the debugger

All three load `.env` automatically and use the project's `.venv` interpreter
(`.vscode/settings.json`). Breakpoints only stop in your own code by default
(`justMyCode: true`); set it to `false` in a config if you need to step into
LangChain's internals.
