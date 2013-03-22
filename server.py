#!/usr/bin/env python
import controller

import cherrypy
import json
import wsgiref.handlers
from datetime import datetime

def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

if __name__ == '__main__':
    config = {'global': {'server.socket_host': '0.0.0.0',
                         'server.socket_port': 80,
                        },
              '/':      {'error_page.default': error}
             }
    app = cherrypy.tree.mount(ShnergleServer(), "/", config)
    wsgiref.handlers.CGIHandler().run(app)
