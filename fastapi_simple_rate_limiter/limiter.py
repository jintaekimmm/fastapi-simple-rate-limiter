import time
from functools import wraps
from typing import Any, Type

from redis import asyncio as aioredis

from fastapi_simple_rate_limiter.exception import RateLimitException


class RateLimiter:
    def __init__(
        self,
        limit: int,
        seconds: int,
        redis: aioredis.Redis | None = None,
        exception: Type[Exception] | None = None,
        exception_status: int = 429,
        exception_message: Any = "Rate Limit Exceed",
    ):
        self.limit = limit
        self.seconds = seconds
        self.local_session = {}
        self.redis = redis
        self.exception_cls = exception
        self.exception_status = exception_status
        self.exception_message = exception_message

        # Set a default exception when the rate limit is reached
        # If 'HTTPException' cannot be used because fastapi is not installed, RateLimitException is thrown.
        try:
            from fastapi import HTTPException
            self.http_exception_module = HTTPException
        except ModuleNotFoundError:
            self.http_exception_module = None

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request", None)
            key = self.__get_key(request)

            if self.redis:
                await self.__check_in_redis(key)
            else:
                await self.__check_in_memory(key)

            return await func(*args, **kwargs)

        return wrapper

    @staticmethod
    def __get_key(request):
        """
        Creates and returns a RateLimit Key
        Create a key and count the limit according to the Client IP Address and API URL Path.

        :param request: FastAPI.Request Object
        :return:
        """
        if request:
            return f"default:{request.client.host}:{request.url.path}"
        return ""

    def __raise_exception(self):
        """
        An exception is raised when the rate limit reaches the limit.

        If there is an exception class passed by the user, the exception passed by the user is generated.
        If the exception class passed by the user does not exist and FastAPI is installed, an HTTPException is thrown.
        If the exception class passed by the user does not exist and FastAPI is not installed, a RateLimitException is thrown.
        :return:
        """
        if not self.exception_cls and self.http_exception_module:
            raise self.http_exception_module(
                status_code=self.exception_status, detail=self.exception_message
            )
        elif not self.exception_cls:
            raise RateLimitException(self.exception_message)
        else:
            raise self.exception_cls(
                status_code=self.exception_status, message=self.exception_message
            )

    async def __check_in_memory(self, key: str):
        """
        This is a check function used when memory is used as rate limit storage.
        Use a dictionary in memory to check usage based on key.

        :param key: RateLimit Key
        :return:
        """
        current_time = time.time()
        last_request_time, request_count = self.local_session.get(key, (0, 0))

        if (
            current_time - last_request_time
        ) < self.seconds and request_count >= self.limit:
            self.__raise_exception()
        else:
            new_count = 1 if request_count >= self.limit else request_count + 1
            self.local_session[key] = (current_time, new_count)

    async def __check_in_redis(self, key: str):
        """
        This is a check function used when using Redis as rate limit storage.
        Check usage by storing 'last_request_time' and 'request_count' values based on key in redis.

        :param key: RateLimit Key
        :return:
        """
        current_time = time.time()
        stored_data = await self.redis.hmget(
            key, ["last_request_time", "request_count"]
        )
        last_request_time = float(stored_data[0] or 0)
        request_count = int(stored_data[1] or 0)

        if (
            current_time - last_request_time
        ) < self.seconds and request_count >= self.limit:
            self.__raise_exception()
        else:
            new_count = 1 if request_count >= self.limit else request_count + 1

            p = await self.redis.pipeline()
            await p.hset(key, "last_request_time", current_time)
            await p.hset(key, "request_count", new_count)
            await p.execute()
