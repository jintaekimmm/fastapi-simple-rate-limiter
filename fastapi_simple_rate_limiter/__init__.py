from .limiter import RateLimiter, RateLimitException

rate_limiter = RateLimiter

__all__ = [
    "rate_limiter",
    "RateLimitException"
]

__version__ = "0.0.2"
