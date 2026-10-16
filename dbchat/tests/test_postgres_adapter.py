import pytest

from dbchat.adapters.postgres import _interpret_read_only_check, _timeout_connect_args


def test_timeout_connect_args_converts_seconds_to_milliseconds():
    assert _timeout_connect_args(10.0) == {"options": "-c statement_timeout=10000"}


def test_timeout_connect_args_handles_fractional_seconds():
    assert _timeout_connect_args(0.5) == {"options": "-c statement_timeout=500"}


def test_timeout_connect_args_handles_zero_as_no_timeout():
    # Postgres treats statement_timeout=0 as "disabled" — matches libpq's own
    # convention, so passing 0 through isn't a bug, it's how you opt out.
    assert _timeout_connect_args(0) == {"options": "-c statement_timeout=0"}


def _row(is_superuser=False, has_write_grant=False, owns_tables=False) -> dict:
    return {"is_superuser": is_superuser, "has_write_grant": has_write_grant, "owns_tables": owns_tables}


def test_interpret_read_only_check_passes_when_all_signals_clean():
    ok, message = _interpret_read_only_check(_row())
    assert ok is True
    assert "No write privileges" in message


def test_interpret_read_only_check_fails_for_superuser():
    ok, message = _interpret_read_only_check(_row(is_superuser=True))
    assert ok is False
    assert "superuser" in message


def test_interpret_read_only_check_fails_for_table_owner():
    ok, message = _interpret_read_only_check(_row(owns_tables=True))
    assert ok is False
    assert "owns" in message


def test_interpret_read_only_check_fails_for_explicit_write_grant():
    ok, message = _interpret_read_only_check(_row(has_write_grant=True))
    assert ok is False
    assert "INSERT" in message


@pytest.mark.parametrize(
    "row",
    [
        _row(is_superuser=True, has_write_grant=True, owns_tables=True),
        _row(is_superuser=True, owns_tables=True),
    ],
)
def test_interpret_read_only_check_fails_when_multiple_signals_present(row):
    ok, _ = _interpret_read_only_check(row)
    assert ok is False
