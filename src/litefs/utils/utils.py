#!/usr/bin/env python
# coding: utf-8

import logging
from time import time, strftime, gmtime
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


def gmt_date(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(timestamp))


def make_logger(name, log=None, level=logging.DEBUG):
    logger = logging.getLogger(name)
    fmt = logging.Formatter(
        ("%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message"
         ")s"),
        datefmt=date_format
    )
    logger.setLevel(level)
    if log:
        handler = logging.FileHandler(log)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger
