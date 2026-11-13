from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from logging import getLogger
from time import perf_counter
from typing import ParamSpec, TypeVar
from uuid import uuid4

L = getLogger(__name__)
_request_id: ContextVar[str] = ContextVar("performance_request_id", default="-")
_Params = ParamSpec("_Params")
_Result = TypeVar("_Result")


@contextmanager
def timed_stage(stage: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        L.info(
            "performance request_id=%s stage=%s duration_ms=%.3f",
            _request_id.get(),
            stage,
            (perf_counter() - start) * 1000,
        )


@contextmanager
def timed_request() -> Iterator[None]:
    token = _request_id.set(uuid4().hex)
    try:
        with timed_stage("request_total"):
            yield
    finally:
        _request_id.reset(token)


def timed_call(
    stage: str,
    function: Callable[_Params, _Result],
    *args: _Params.args,
    **kwargs: _Params.kwargs,
) -> _Result:
    with timed_stage(stage):
        return function(*args, **kwargs)