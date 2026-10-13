import pytest

from dbchat.security.sql_guard import UnsafeQueryError, ensure_safe_select


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM users",
        "WITH t AS (SELECT 1) SELECT * FROM t",
        "SELECT created_at FROM logs",  # keyword-looking column name must not false-positive
        "SELECT * FROM users WHERE name = 'a'; -- trailing comment",
    ],
)
def test_allows_read_only_queries(sql):
    ensure_safe_select(sql)  # must not raise


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM users; DROP TABLE users;",
        "DROP TABLE users",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "INSERT INTO users VALUES (1)",
        "",
        "   ",
    ],
)
def test_rejects_unsafe_queries(sql):
    with pytest.raises(UnsafeQueryError):
        ensure_safe_select(sql)
