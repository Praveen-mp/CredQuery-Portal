from dbchat.security.rate_limiter import RateLimiter


def test_allows_up_to_max_then_blocks():
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    results = [limiter.allow("session-a") for _ in range(5)]

    assert results == [True, True, True, False, False]


def test_different_keys_have_independent_limits():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("session-a") is True
    assert limiter.allow("session-b") is True
    assert limiter.allow("session-a") is False
