#!/usr/bin/env python

import sys
sys.dont_write_bytecode = True

# uwsgi --http :9090 --wsgi-file wsgi_example.py

import litefs
print(litefs)
app = litefs.Litefs()
application = app.wsgi()
