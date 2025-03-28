from unittest.mock import MagicMock

import pytest

from fastapi_simple_rate_limiter import RateLimitException
from fastapi_simple_rate_limiter.limiter import FailedLimiter


@pytest.fixture
def limiter():
    return FailedLimiter(limit=3, seconds=60)


@pytest.mark.asyncio
async def test_failed_limiter_in_memory(limiter):
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    limiter._local_session.clear()

    for _ in range(3):
        await limiter.fail_up(mock_request)

    with pytest.raises(RateLimitException):
        await limiter._FailedLimiter__check_in_memory('failed:127.0.0.1')
