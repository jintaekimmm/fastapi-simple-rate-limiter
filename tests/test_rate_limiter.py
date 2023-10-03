import pytest
from fastapi_simple_rate_limiter import rate_limiter, RateLimitException


@pytest.fixture
def limiter():
    return rate_limiter(limit=3, seconds=60)


@pytest.mark.asyncio
async def test_rate_limiter_in_memory(limiter):
    limiter.local_session.clear()
    for _ in range(3):
        await limiter._RateLimiter__check_in_memory("test_key")

    with pytest.raises(RateLimitException):
        await limiter._RateLimiter__check_in_memory("test_key")
