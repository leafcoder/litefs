#!/usr/bin/env python
# coding: utf-8


class HttpError(Exception):
    def __init__(self, status_code=500, message="Internal Server Error"):
        self.status_code = status_code
        self.message = message
        super(HttpError, self).__init__(f"{status_code} {message}")

    def __str__(self):
        return f"{self.status_code} {self.message}"
