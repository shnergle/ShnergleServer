import cherrypy
import json

from datetime import datetime
from functools import wraps


def jsonp(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        cherrypy.response.headers['Expires'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        cherrypy.response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        res = json.dumps(func(*args, **kwargs))
        if 'callback' in kwargs:
            cherrypy.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
            res = kwargs['callback'] + '(' + res + ');'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/json'
        return res
    return decorator


class User:
    @cherrypy.expose
    @jsonp
    def add(self, **kwargs):
        res = {}
        res['Function'] = 'Test'
        return res


class ShnergleServer:
    users = User()

    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        res = {}
        res['Function'] = 'Overview'
        return res
