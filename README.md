# LangChain Learning

Learning LangChain by building a progressive series of small, runnable scripts —
each one introduces one concept on top of the last. Using Azure OpenAI as the model provider.

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
