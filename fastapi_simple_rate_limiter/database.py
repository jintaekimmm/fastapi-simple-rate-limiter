from redis import asyncio as aioredis


def create_redis_session(
        host: str = "localhost", port: int = 6379, db: int = 0, password: str = '', timeout: int = 2
) -> aioredis.Redis:
    """
    Creates and returns an async Redis session

    :param host: redis host address
    :param port: redis port number
    :param db: redis db number
    :param password: redis require password
    :param timeout: redis socket timeout(seconds)
    :return: returns aioredis
    """
    def create_dsn():
        if password:
            return f'redis://:{password}@{host}:{port}/{db}?encoding=utf-8'
        return f'redis://{host}:{port}/{db}?encoding=utf-8'

    redis_url = create_dsn()
    pool = aioredis.ConnectionPool.from_url(
        redis_url, decode_responses=True, socket_timeout=timeout
    )
    return aioredis.Redis(connection_pool=pool)
