import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Type

from redis import asyncio as aioredis

from fastapi_simple_rate_limiter.exception import RateLimitException


@dataclass
class LimitTypeKey:
    RateLimit = 'default'
    FailedLimit = 'failed'


class DefaultLimiter:
    def __init__(
            self,
            limit,
            seconds: int,
            redis: aioredis.Redis | None = None,
            exception: Type[Exception] | None = None,
            exception_status: int = 429,
            exception_message: Any = "",
    ):
        self._limit = limit
        self._seconds = seconds
        self._local_session = {}
        self._redis = redis
        self._exception_cls = exception
        self._exception_status = exception_status
        self._exception_message = exception_message

        # Set a default exception when the rate limit is reached
        # If 'HTTPException' cannot be used because fastapi is not installed, RateLimitException is thrown.
        try:
            from fastapi import HTTPException
            self.http_exception_module = HTTPException
        except ModuleNotFoundError:
            self.http_exception_module = None

    def raise_exception(self):
        """
        An exception is raised when the rate limit reaches the limit.

        If there is an exception class passed by the user, the exception passed by the user is generated.
        If the exception class passed by the user does not exist and FastAPI is installed, an HTTPException is thrown.
        If the exception class passed by the user does not exist and FastAPI is not installed, a RateLimitException is thrown.
        :return:
        """
        if not self._exception_cls and self.http_exception_module:
            raise self.http_exception_module(
                status_code=self._exception_status, detail=self._exception_message
            )
        elif not self._exception_cls:
            raise RateLimitException(self._exception_message)
        else:
            raise self._exception_cls(
                status_code=self._exception_status, message=self._exception_message
            )


class FailedLimiter(DefaultLimiter):
    def __init__(
            self,
            limit,
            seconds: int,
            redis: aioredis.Redis | None = None,
            exception: Type[Exception] | None = None,
            exception_status: int = 429,
            exception_message: Any = "",
    ):
        self.exception_message = exception_message if exception_message else f"Access is limited for {seconds} seconds"
        super().__init__(limit, seconds, redis, exception, exception_status, self.exception_message)

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request", None)

            key = self.__get_key(request, LimitTypeKey.FailedLimit)

            if self._redis:
                await self.__check_in_redis(key)
            else:
                await self.__check_in_memory(key)

            return await func(*args, **kwargs)

        return wrapper

    @staticmethod
    def __get_key(request, key_name: str):
        """
        Creates and returns a Limit Key
        Create a key and count the limit according to the Client IP Address and API URL Path.

        :param request: FastAPI.Request Object
        :param key_name: Redis Key prefix name
        :return:
        """
        if request:
            return f"{key_name}:{request.client.host}"
        return ""

    async def reset(self, request):
        """
        Reset the failure count

        :param request: FastAPI.Request Object
        :return:
        """

        key = self.__get_key(request, LimitTypeKey.FailedLimit)
        if self._redis:
            if await self._redis.exists(key):
                await self._redis.delete(key)
        else:
            if key in self._local_session:
                del self._local_session[key]

    async def fail_up(self, request):
        """
        Increment the failure count if the request fails

        If limit storage is 'memory', use a dictionary of memory to check usage based on the key
        If limit storage is 'redis', store 'last_request_time' and 'failed_count' values in redis to check usage by key.

        :param request: FastAPI.Request Object
        :return:
        """

        key = self.__get_key(request, LimitTypeKey.FailedLimit)
        current_time = time.time()

        if self._redis:
            stored_data = await self._redis.hmget(
                key, ["last_request_time", "failed_count"]
            )
            failed_count = int(stored_data[1] or 0)

            if failed_count <= self._limit:
                new_count = failed_count if failed_count > self._limit else failed_count + 1

                p = await self._redis.pipeline()
                await p.hset(key, "last_request_time", current_time)
                await p.hset(key, "failed_count", new_count)
                if new_count == self._limit:
                    await p.expire(key, self._seconds)
                await p.execute()
        else:
            _, failed_count = self._local_session.get(key, (0, 0))

            new_count = failed_count if failed_count >= self._limit else failed_count + 1
            if failed_count <= self._limit:
                self._local_session[key] = (current_time, new_count)

    async def __check_in_memory(self, key: str):
        """
        This is a check function used when memory is used as rate failed storage.
        If the failure count exceeds a set limit, restrict access for a specified amount of time

        :param key: FailedLimit Key
        :return:
        """
        current_time = time.time()
        last_request_time, failed_count = self._local_session.get(key, (0, 0))

        if (current_time - last_request_time) < self._seconds and failed_count >= self._limit:
            self.raise_exception()

    async def __check_in_redis(self, key: str):
        """
        This is a check function used when using Redis as failed limit storage.
        If the failure count exceeds a set limit, restrict access for a specified amount of time

        :param key: FailedLimit Key
        :return:
        """
        current_time = time.time()

        stored_data = await self._redis.hmget(
            key, ["last_request_time", "failed_count"]
        )
        last_request_time = float(stored_data[0] or 0)
        failed_count = int(stored_data[1] or 0)

        if (current_time - last_request_time) < self._seconds and failed_count >= self._limit:
            self.raise_exception()


class RateLimiter(DefaultLimiter):
    def __init__(
        self,
        limit: int,
        seconds: int,
        redis: aioredis.Redis | None = None,
        exception: Type[Exception] | None = None,
        exception_status: int = 429,
        exception_message: Any = "Rate Limit Exceed",
    ):
        self.exception_message = exception_message
        super().__init__(limit, seconds, redis, exception, exception_status, self.exception_message)
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
            key = self.__get_key(request, LimitTypeKey.RateLimit)

            if self._redis:
                await self.__check_in_redis(key)
            else:
                await self.__check_in_memory(key)

            return await func(*args, **kwargs)

        return wrapper

    @staticmethod
    def __get_key(request, key_name: str):
        """
        Creates and returns a RateLimit Key
        Create a key and count the limit according to the Client IP Address and API URL Path.

        :param request: FastAPI.Request Object
        :param key_name: Redis Key prefix name
        :return:
        """
        if request:
            return f"{key_name}:{request.client.host}:{request.url.path}"
        return ""

    async def __check_in_memory(self, key: str):
        """
        This is a check function used when memory is used as rate limit storage.
        Use a dictionary in memory to check usage based on key.

        :param key: RateLimit Key
        :return:
        """
        current_time = time.time()
        last_request_time, request_count = self._local_session.get(key, (0, 0))

        if (
            current_time - last_request_time
        ) < self._seconds and request_count >= self._limit:
            self.raise_exception()
        else:
            new_count = 1 if request_count >= self._limit else request_count + 1
            self._local_session[key] = (current_time, new_count)

    async def __check_in_redis(self, key: str):
        """
        This is a check function used when using Redis as rate limit storage.
        Check usage by storing 'last_request_time' and 'request_count' values based on key in redis.

        :param key: RateLimit Key
        :return:
        """
        current_time = time.time()
        stored_data = await self._redis.hmget(
            key, ["last_request_time", "request_count"]
        )
        last_request_time = float(stored_data[0] or 0)
        request_count = int(stored_data[1] or 0)

        if (
            current_time - last_request_time
        ) < self._seconds and request_count >= self._limit:
            self.raise_exception()
        else:
            new_count = 1 if request_count >= self._limit else request_count + 1

            p = await self._redis.pipeline()
            await p.hset(key, "last_request_time", current_time)
            await p.hset(key, "request_count", new_count)
            await p.expire(key, self._seconds)
            await p.execute()
