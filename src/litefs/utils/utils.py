#!/usr/bin/env python
# coding: utf-8

import logging
from functools import lru_cache
from time import gmtime, strftime, time
from traceback import format_exc

date_format = "%Y/%m/%d %H:%M:%S"


def log_error(logger, message=None):
    if message is None:
        message = "error occured"
    logger.error(message, exc_info=True)


def log_info(logger, message=None):
    if message is None:
        message = "info"
    logger.info(message)


def log_debug(logger, message=None):
    if message is None:
        message = "debug"
    logger.debug(message)


def render_error():
    import sys
    from io import StringIO

    output = StringIO()
    exc_type, exc_value, exc_traceback = sys.exc_info()
    output.write(f"<h1>Error: {exc_type.__name__}</h1>")
    output.write(f"<p>{exc_value}</p>")
    output.write("<h2>Traceback:</h2>")
    output.write("<pre>")
    output.write(format_exc())
    output.write("</pre>")
    return output.getvalue()


@lru_cache(maxsize=1024)
def format_gmt_date(timestamp):
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(timestamp))


def gmt_date(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return format_gmt_date(int(timestamp))


def make_logger(name, log=None, level=logging.INFO):
    FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
    logging.basicConfig(level=level, format=FORMAT, datefmt=date_format)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 禁止 watchdog 的 DEBUG 日志输出
    watchdog_logger = logging.getLogger('watchdog')
    watchdog_logger.setLevel(logging.INFO)
    watchdog_logger = logging.getLogger('watchdog.observers')
    watchdog_logger.setLevel(logging.INFO)
    
    if log:
        fmt = logging.Formatter(FORMAT, datefmt=date_format)
        handler = logging.FileHandler(log)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger
