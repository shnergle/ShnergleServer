#!/usr/bin/env python
import server
import sys
from cherrypy import wsgiserver

port = int(sys.argv[1]) if 1 in sys.argv else 8080
wsgiserver.CherryPyWSGIServer(('0.0.0.0', port), server.app).start()
