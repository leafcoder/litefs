#!/usr/bin/env python

import sys
sys.dont_write_bytecode = True

import litefs
try:
    port = int(sys.argv[1])
except IndexError:
    port = 9090
litefs = litefs.Litefs(
    address='0.0.0.0:%s' % port,
    webroot='./site',
    debug=True
)
litefs.run(timeout=2.)
