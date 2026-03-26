#!/usr/bin/env python
# coding: utf-8

from collections import UserDict


class Session(UserDict):

    def __init__(self, session_id):
        self.id = session_id
        self.data = {}

    def __str__(self):
        return "<Session Id=%s>" % self.id
