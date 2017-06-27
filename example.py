#!/usr/bin/python

import sys
sys.dont_write_bytecode = True

import litefs
litefs = litefs.Litefs(
    address='localhost:9090', webroot='./site', debug=True
)
litefs.run(timeout=2.)
