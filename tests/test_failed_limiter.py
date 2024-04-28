import pytest

from fastapi_simple_rate_limiter import RateLimitException
from fastapi_simple_rate_limiter.limiter import FailedLimiter


@pytest.fixture
def limiter():
    return FailedLimiter(limit=3, seconds=60)


@pytest.mark.asyncio
async def test_failed_limiter_in_memory(limiter):
    limiter.local_session.clear()
    for _ in range(3):
        await limiter._FailedLimiter__check_in_memory("test_key")

    with pytest.raises(RateLimitException):
        await limiter._FailedLimiter__check_in_memory("test_key")
