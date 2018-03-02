#!/usr/bin/python

import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '..')

import litefs
litefs = litefs.Litefs(
    address='localhost:8080', webroot='./site', debug=True
)
litefs.run(timeout=2.)
