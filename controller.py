import cherrypy
import json

from datetime import datetime
from functools import wraps

def dont_cache():
    cherrypy.response.headers['Expires'] = datetime.utcnow().strftime(
        '%a, %d %b %Y %H:%M:%S GMT')
    cherrypy.response.headers['Cache-Control'] = ('no-store, '
                                                  'no-cache, '
                                                  'must-revalidate, '
                                                  'post-check=0, '
                                                  'pre-check=0')

def jsonp(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        dont_cache()
        res = json.dumps(func(*args, **kwargs), separators=(',', ':'))
        callback = kwargs.pop('callback', False)
        if callback:
            cherrypy.response.headers['Content-Type'] = ('text/javascript; '
                                                         'charset=utf-8')
            res = callback + '(' + res + ');'
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

class Venue:
    _name = 'venues'
        
    @cherrypy.expose
    @jsonp
    def get(self, **kwargs):
        return {}
        
    @cherrypy.expose
    @jsonp
    def set(self, **kwargs):
        return {}
        
    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        return {}


class ShnergleServer:
    users = User()
    venues = Venue()

    def __init__(self):
        self.v1 = self

    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        res = {}
        res['Function'] = 'Overview'
        return res
