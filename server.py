#!/usr/bin/env python

import cherrypy
import json
import wsgiref.handlers
from datetime import datetime

def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

def jsonp(func):
    def decorator():
        cherrypy.response.headers['Expires'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        cherrypy.response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        funcres = func()
        jsonres = json.dumps(funcres['res'])
        if 'callback' in funcres['kwargs']:
            cherrypy.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
            jsonres = funcres['kwargs']['callback'] + '(' + jsonres + ');'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/json'
        return jsonres
    return decorator
        
class Common:
    pass

class User(Common):
    @cherrypy.expose
    @jsonp
    def add(self, **kwargs):
        res = {}
        res['Function'] = 'Test'
        return {'res': res, 'kwargs': **kwargs}

class ShnergleServer(Common):
    users = User()

    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        res = {}
        res['Function'] = 'Overview'
        return {'res': res, 'kwargs': **kwargs}

if __name__ == '__main__':
    config = {'global': {'server.socket_host': '0.0.0.0',
                         'server.socket_port': 80,
                        },
              '/':      {'error_page.default': error}
             }
    app = cherrypy.tree.mount(ShnergleServer(), "/", config)
    wsgiref.handlers.CGIHandler().run(app)
