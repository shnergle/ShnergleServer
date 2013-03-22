#!/usr/bin/env python
import controller

import cherrypy
import json
from google.appengine.ext.webapp.util import run_wsgi_app
from datetime import datetime


def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

if __name__ == '__main__':
    config = {'/': {'error_page.default': error}}
    app = cherrypy.tree.mount(controller.ShnergleServer(), "/", config)
    run_wsgi_app(app)
