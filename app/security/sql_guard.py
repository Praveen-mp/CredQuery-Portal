import re


class UnsafeQueryError(ValueError):
    """Raised when a generated SQL query fails the read-only safety guard."""


_FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "CALL", "COPY",
    "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX", "REPLACE",
]

_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_ALLOWED_START_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_KEYWORD_RE = {kw: re.compile(rf"\b{kw}\b") for kw in _FORBIDDEN_KEYWORDS}


def _strip_comments(sql: str) -> str:
    sql = _BLOCK_COMMENT_RE.sub(" ", sql)
    sql = _LINE_COMMENT_RE.sub(" ", sql)
    return sql


def ensure_safe_select(sql: str) -> str:
    """Validates that `sql` is a single, read-only SELECT/CTE statement.

    Raises UnsafeQueryError (and never executes anything) if the query:
    - isn't a SELECT/WITH statement,
    - contains more than one statement (stacked queries, e.g. "SELECT 1; DROP ..."),
    - contains any data- or schema-mutating keyword.

    This is a defense-in-depth, application-level check that runs on every
    LLM-generated query before it reaches the database. It is NOT the
    primary safety boundary — the database user this app connects as must
    also be SELECT-only, so that even a bypass of this guard can't mutate data.
    """
    cleaned = _strip_comments(sql).strip()

    if not cleaned:
        raise UnsafeQueryError("Empty query.")

    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if len(statements) != 1:
        raise UnsafeQueryError(f"Only a single statement is allowed, got {len(statements)}.")

    statement = statements[0]

    if not _ALLOWED_START_RE.match(statement):
        raise UnsafeQueryError("Only SELECT/WITH (read-only) queries are allowed.")

    upper = statement.upper()
    for keyword, pattern in _KEYWORD_RE.items():
        if pattern.search(upper):
            raise UnsafeQueryError(f"Forbidden keyword detected: {keyword}")

    return statement
