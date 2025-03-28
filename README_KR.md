# FastAPI Simple RateLimiter

이 패키지에는 FastAPI에서 사용할 수 있는 API Rate limit 데코레이터가 포함되어 있습니다

쉽게 사용할 수 있고, 특정 API URL Path에서만 지정할 수 있으며 특별한 스토리지 없이도(in memory) 사용할 수 있습니다

또한, redis를 사용하여 multi instance 상황에서도 api rate limit 값을 올바르게 공유하여 제어할 수도 있습니다

rate limit가 설정된 한계에 도달했을 경우에는 지정된 exception 또는 사용자가 지정한 exception class를 발생시킬 수 있습니다

사용자 지정의 exception class의 형태는 고정되어 있지만 response format은 어느정도 자유롭게 설정할 수 있습니다

## Dependencies

- Python >= 3.10 or higher environment
- [redis-py](https://github.com/redis/redis-py)
- [FastAPI(with Asynchronous Code): async def로 작성된 코드](https://fastapi.tiangolo.com/async/)


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

이 패키지를 사용할려면 FastAPI api route 함수에 rate_limiter decorator를 추가해주세요

FastAPI API 함수에 Request 인자를 설정해야 Client IP 주소와 API URL Path를 올바르게 체크할 수 있습니다 

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

이 API route는 60초에 3번만 호출할 수 있습니다

Decorator에는 limit와 seconds를 필수로 설정해야하며, 호출 가능한 횟수와 제한 시간을 입력할 수 있습니다

만약, 설정된 한계에 도달한다면 FastAPI HTTPException이 발생합니다. 만약, FastAPI가 설치되지 않은 환경에서 호출하였다면, fastapi_rate_limiter.RateLimitException이 발생하게 됩니다

redis를 사용하는 경우에는 아래와 같이 redis session을 생성 후 인자로 전달하여 사용할수 있습니다

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

`create_redis_session`에는 기본적인 연결 정보를 전달할 수 있습니다

```python
redis_session = create_redis_session(host='localhost', port=6379, db=0, password='')
```

### rate limit exceed response

rate limit excced에 도달한 경우에는 `HTTPException`으로 결과를 반환하게 됩니다

```shell
HTTP: 429
{
    "detail": "Rate Limit Exceed
}
```

HTTP Status나 detail의 내용을 변경하고 싶은 경우에는 `exception_status`와 `exception_message` 인자를 통해 변경할 수 있습니다

```python
@app.get("/test")
@rate_limiter(limit=3, seconds=30, exception_status=400, exception_message="Oh..! Too many Request!")
async def test_list_api(request: Request):
    ...
```


### custom exception and response format

만약, HTTPException이 아닌 사용자가 정의한 response format으로 limit exceed 결과를 반환하고 싶다면 다음과 같이 사용자 정의 exception class를 생성하여 사용할 수 있습니다

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

사용자 정의 exception을 통해 원하는 형태의 JSONResponse으로 결과를 반환할 수 있습니다

그러나, 사용자 정의 exception을 만들 때는 반드시 `status_code`와 `message`만을 사용할 수 있는 한계가 있습니다. `message`내에는 구조의 한계를 체크하고 있지 않으므로 그나마 자유로운 형태를 가질 수 있을 것으로 보입니다


## FailedLimiter

이 Limiter는 특정 실패 횟수를 넘어선다면 접근을 제한하는 기능을 가지고 있습니다

예를 들어, 로그인과 같은 인증 함수에 무분별한 접근을 제한하고 싶은 경우(예: 비밀번호 입력을 5번 틀린다면 30분간 차단하고 싶은 경우)에 사용할 수 있습니다

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
이 API route는 실패 횟수가 3번이 되면, 300초간 접근을 제한합니다

Decorator에는 limit와 seconds를 필수로 설정해야하며, 실패 제한 횟수와 접근 제한 시간을 입력할 수 있습니다

그외에 사용 가능한 옵션은 rate_limiter와 동일하게 설정할 수 있습니다

custom exception과 redis storage 모두 사용할 수 있습니다

## Get client real IP Address(X-Forwarded-For)

API Rate limit를 체크할 때에 client의 ip address와 api url path를 혼합하여 키를 사용합니다

만약 client ip address를 모두 동일하게 본다면 개별 사용자가 아닌 전체 모든 사용자가 rate limit 한계를 공유하게 될 것입니다

여기에는 uvicorn와 gunicorn을 사용하는 경우에 client의 실제 IP Address를 확인할 수 있는 방법을 소개합니다

### uvicorn

uvicorn은 `--proxy-headers`와 `--forwarded-allow-ips`를 사용합니다

옵션의 자세한 정보는 [uvicorn](https://www.uvicorn.org/deployment/) 문서에서 확인할 수 있습니다

```shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"
```

### gunicorn

gunicorn은 `--forwarded-allow-ips` 옵션을 사용합니다

옵션의 자세한 정보는 [gunicorn](https://docs.gunicorn.org/en/stable/settings.html#forwarded-allow-ips) 문서에서 확인할 수 있습니다

```shell
gunicorn app.main:app --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --forwarded-allow-ips "*"
```


## License

This project is licensed under the terms of the MIT license.
