# dbchat

Self-hosted, natural-language chat over your own databases. Your team brings
its own database credentials and its own LLM provider credentials, deploys
this on infrastructure you control, and lets non-technical teams (customer
success, support, ops) ask questions about live data without filing a ticket
with a dev team.

> `dbchat` is a placeholder project name — rename it before you publish.

## Why

Every "chat with your database" demo online assumes you, the developer, are
the one running it. `dbchat` is built the other way around: a team that
*isn't* technical deploys it once, points it at a read-only database user
through a setup wizard, and then just... asks questions.

## Status

Early (v0.1). One database adapter (PostgreSQL) is implemented behind a
plugin interface designed so new adapters (MySQL, MongoDB, Snowflake,
BigQuery, ...) can be added without touching the agent or UI code — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Architecture

```
src/dbchat/
├── core/        # bootstrap config (one encryption key, read once at deploy time)
├── storage/     # encrypted metadata store (SQLite) for connections + LLM config
├── adapters/    # BaseDBAdapter plugin interface + concrete adapters (postgres.py, ...)
├── security/    # sql_guard (read-only query enforcement) + rate_limiter
├── agent/       # adapter-agnostic LangChain agent builder
└── ui/          # Streamlit app: Setup wizard, Connections manager, Chat
```

Two kinds of configuration, deliberately kept apart:
- **Bootstrap config** (`core/config.py`): one encryption key + where to store
  app metadata. Set once, by whoever deploys the container, via environment
  variables.
- **Everything else** — database connections, LLM provider credentials — is
  entered through the in-app **Setup** wizard after first launch, encrypted,
  and stored in the app's own local SQLite metadata database. No file editing,
  no redeploys, no dev team involved after initial rollout.

### Safety model

1. **Database-level**: every connection must use a `SELECT`-only DB user.
   This is the real boundary — everything else is defense in depth.
2. **Application-level**: `security/sql_guard.py` parses every LLM-generated
   query and rejects anything that isn't a single read-only
   `SELECT`/`WITH` statement — no stacked statements, no mutating keywords.
3. **Rate limiting**: `security/rate_limiter.py` caps chat requests per
   session. In-memory by default (fine for one instance); swap in a
   Redis-backed implementation behind the same interface if you deploy
   multiple replicas.

## Quickstart (Docker)

```bash
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste the output into .env as APP_SECRET_KEY

docker compose up --build
```

Open `http://localhost:8501`. The Setup page walks you through adding your
LLM provider credentials and your first database connection.

## Quickstart (local dev)

```bash
uv sync
cp .env.example .env
# fill in APP_SECRET_KEY as above

uv run streamlit run src/dbchat/ui/streamlit_app.py
```

## Adding a database adapter

See [CONTRIBUTING.md](CONTRIBUTING.md) — in short: implement `BaseDBAdapter`
in `adapters/`, decorate it with `@register`, add one import line to
`adapters/__init__.py`. The agent and UI pick it up automatically.

## License

MIT — see [LICENSE](LICENSE).
