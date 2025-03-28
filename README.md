# FastAPI Simple RateLimiter

This package contains the API Rate limit decorator for use in FastAPI.

It is easy to use, can only be specified in a specific API URL Path, and can be used without special storage (in memory).

Additionally, you can use redis to properly share and control the API rate limit value even in multi-instance situations.

When the rate limit reaches the set limit, a specified exception or user-specified exception class can be generated.

The format of the user-specified exception class is fixed, but the response format can be set somewhat freely.

## Dependencies

- Python >= 3.10 or higher environment
- [redis-py](https://github.com/redis/redis-py)
- [FastAPI (with Asynchronous Code): Code written with async def](https://fastapi.tiangolo.com/async/)

## Installation

### pip

```shell
$ pip install fastapi-simple-rate-limiter
```
### poetry

```shell
$ poetry add fastapi-simple-rate-limiter
```

### Github

Installing the latest version from Github:

```shell
$ git clone https://github.com/jintaekimmm/fastapi-simple-rate-limiter
$ cd fastapi-simple-rate-limiter
$ python setup.py install
```

## Usage

To use this package, please add rate_limiter decorator to the FastAPI api route function.

You must set the Request argument in the FastAPI API function to properly check the Client IP address and API URL Path.

```python
from fastapi import FastAPI
from fastapi.requests import Request

from fastapi_simple_rate_limiter import rate_limiter

app = FastAPI()


@app.get("/test")
@rate_limiter(limit=3, seconds=60)
async def test_list_api(request: Request):
    ...
```

This API route can only be called 3 times per 60 seconds.

Limit and seconds must be set to Decorator, and you can enter the number of calls and limit time.

If the set limit is reached, a FastAPI HTTPException is thrown. If the call is made in an environment where FastAPI is not installed, fastapi_rate_limiter.RateLimitException will occur.

When using redis, you can create a redis session and pass it as an argument as shown below.

```python
from fastapi import FastAPI
from fastapi.requests import Request

from fastapi_simple_rate_limiter import rate_limiter
from fastapi_simple_rate_limiter.database import create_redis_session

app = FastAPI()

redis_session = create_redis_session()


@app.get("/test")
@rate_limiter(limit=3, seconds=30, redis=redis_session)
async def test_list_api(request: Request):
    ...
```

You can pass basic connection information to `create_redis_session`

```python
redis_session = create_redis_session(host='localhost', port=6379, db=0, password='')
```

### rate limit exceed response

If the rate limit excced is reached, the result will be returned as `HTTPException`.

```shell
HTTP: 429
{
    "detail": "Rate Limit Exceed
}
```

If you want to change the HTTP Status or details, you can do so through the `exception_status` and `exception_message` arguments.

```python
@app.get("/test")
@rate_limiter(limit=3, seconds=30, exception_status=400, exception_message="Oh..! Too many Request!")
async def test_list_api(request: Request):
    ...
```

### custom exception and response format

If you want to return a limit exceed result in a user-defined response format rather than an HTTPException, you can create and use a custom exception class as follows.

```python
from fastapi import FastAPI
from fastapi.requests import Request

from fastapi_simple_rate_limiter import rate_limiter

app = FastAPI()

class CustomException(Exception):
    def __init__(self, status_code: int, message: Any):
        self.status_code = status_code
        self.message = message


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    content = {
        "success": False, 
        "error": {
            "message": exc.message
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


@app.get("/test")
@rate_limiter(limit=3, seconds=30, exception=CustomException)
async def test_list_api(request: Request):
    ...
```

You can return results as a JSONResponse in the desired format via a custom exception.

However, when creating a custom exception, there is a limitation that only `status_code` and `message` can be used. Since the limits of the structure are not checked within `message`, it seems that it can have a free form.


## FailedLimiter

This limiter has the ability to restrict access after a certain number of failures.

For example, you might want to limit indiscriminate access to an authentication function like login (e.g., you might want to block a user for 30 minutes after 5 incorrect password entries).

```python
from fastapi import FastAPI
from fastapi.requests import Request

from fastapi_simple_rate_limiter import FailedLimiter

failed_limiter = FailedLimiter(limit=3, seconds=300, redis=r)


@app.get("/login")
@failed_limiter
async def test_login_api(request: Request):
    if auth_ok:
        # After successful login, reset the failure count
        await failed_limiter.reset(request)
    else:
        # If login fails, increment the number of failures
        await failed_limiter.fail_up(request)
```
This API route restricts access for 300 seconds after three failures

The decorator requires limit and seconds to be set, and allows you to enter the number of failures to limit and the time to limit access

Otherwise, the available options can be set the same as for rate_limiter

Both custom exception and redis storage can be used


## Get client real IP Address

When checking the API rate limit, use a key combining the client's IP address and API url path.

If all client IP addresses are the same, the rate limit will be shared by all users rather than individual users.

Here we introduce a method to check the actual IP address of the client when using uvicorn and gunicorn.

### uvicorn

uvicorn uses `--proxy-headers` and `--forwarded-allow-ips`

Detailed information about options can be found in the [uvicorn](https://www.uvicorn.org/deployment/) document.

```shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"
```

### gunicorn

gunicorn uses the `--forwarded-allow-ips` option

Detailed information about the option can be found in the [gunicorn](https://docs.gunicorn.org/en/stable/settings.html#forwarded-allow-ips) document.

```shell
gunicorn app.main:app --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --forwarded-allow-ips "*"
```

## License

This project is licensed under the terms of the MIT license.