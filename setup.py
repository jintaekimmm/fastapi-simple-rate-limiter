from setuptools import setup, find_packages


setup(
    name="fastapi_simple_rate_limiter",
    version="0.0.3",
    description="Rate limiter to limit the number of API requests in FastAPI",
    author="jintaekimmm",
    author_email="jintae.kimmm@gmail.com",
    url="https://github.com/jintaekimmm/fastapi-simple-rate-limiter",
    project_urls={
        'Github': 'https://github.com/jintaekimmm/fastapi-simple-rate-limiter',
    },
    install_requires=["redis"],
    packages=find_packages(exclude=[]),
    keywords=["fastapi-simple-rate-limiter", "fastapi_simple_rate_limiter", "rate limiter", "rate limit", "fastapi rate limit", "simple rate limit"],
    python_requires=">=3.10",
    package_data={},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)