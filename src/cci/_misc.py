"""
Helper functions
"""
import json
#from pydantic import BaseModel
import pprint
import logging
from typing import Any, Generator, Optional, Type, Iterable
from contextlib import contextmanager

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"



@contextmanager
def init_logging(verbose:bool)->Generator[None, None, None]:
    """
    Context manager to initialize logging for the application.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT
    )

    silence = ["httpcore",
               "httpx"]
    _silence_loggers(silence)

    try:
        yield
    finally:
        pass


def _silence_loggers(loggers:Iterable[str]) -> None:
    """
    Silence the specified loggers by setting their level to WARNING.
    """
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)


def dbg_log_data(obj:object,
             level:int=logging.DEBUG,
             logger_name:str=__name__)->None:
    """
    Log the given data object at the specified logging level.
    """
    logger = logging.getLogger(logger_name)


    if not logger.isEnabledFor(level):
        return

    data:Any
    #if isinstance(obj, BaseModel):
    #    data = obj.model_dump()
    #else:
    #    data = obj
    data = obj
    

    formatted_data = pprint.pformat(data, indent=4)
    for line in formatted_data.splitlines():
        logger.log(level, line)
