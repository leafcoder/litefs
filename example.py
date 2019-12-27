#!/usr/bin/env python

import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '..')

import litefs
port = 8080
if len(sys.argv) > 1:
    port = int(sys.argv[1])
litefs = litefs.Litefs(
    address='0.0.0.0:%s' % port, webroot='./site', debug=True
)
litefs.run(timeout=2.)
