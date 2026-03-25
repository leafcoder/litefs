#!/usr/bin/env python
# coding: utf-8

import logging
from time import time, strftime, gmtime
from mako import exceptions

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
    return exceptions.html_error_template().render()


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
