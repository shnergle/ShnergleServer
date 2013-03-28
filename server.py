import controller

import cherrypy
import json


def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message},
                      separators=(',', ':'))


config = {'/': {'error_page.default': error}}
app = cherrypy.Application(controller.ShnergleServer(), '/', config)
