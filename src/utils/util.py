import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import logging

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def log_time(
    *,
    task: str | None = None,
    args: list[str] | Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def _fn(fn: Callable[P, R]) -> Callable[P, R]:
        def _post_process(
            fn_args: tuple[Any, ...],
            fn_kwargs: dict[str, Any],
            *,
            start_time: float,
            end_time: float,
        ):
            nonlocal args, task
            if not task:
                task = fn.__name__
            if not args:
                args = []

            arg_names = inspect.getfullargspec(fn).args
            named_fn_args = dict(zip(arg_names, fn_args, strict=False))
            default_fn_kwargs = {
                k: v.default
                for k, v in inspect.signature(fn).parameters.items()
                if v.default is not v.empty
            }
            all_log_args = named_fn_args | default_fn_kwargs | fn_kwargs
            if callable(args):
                log_kwargs = args(all_log_args)
            else:
                log_kwargs = {x: all_log_args[x] for x in args}

            duration = end_time - start_time
            logger.info(
                f"Execute time - Task: {task}, Duration: {duration:.3f}s, Start: {start_time}, End: {end_time}"
                + (f", Args: {log_kwargs}" if log_kwargs else "")
            )

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def _async_wrapper(*fn_args: P.args, **fn_kwargs: P.kwargs) -> R:
                start_time = time.time()
                response = await fn(*fn_args, **fn_kwargs)
                end_time = time.time()

                _post_process(
                    fn_args,
                    fn_kwargs,
                    start_time=start_time,
                    end_time=end_time,
                )

                return response

            return _async_wrapper

        @functools.wraps(fn)
        def _wrapper(*fn_args: P.args, **fn_kwargs: P.kwargs) -> R:
            start_time = time.time()
            response = fn(*fn_args, **fn_kwargs)
            end_time = time.time()

            _post_process(
                fn_args,
                fn_kwargs,
                start_time=start_time,
                end_time=end_time,
            )

            return response

        return _wrapper

    return _fn