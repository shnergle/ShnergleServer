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


class User:
    @cherrypy.expose
    @jsonp
    def add(self, **kwargs):
        res = {}
        res['Function'] = 'Test'
        return {'res': res, 'kwargs': **kwargs}


class ShnergleServer:
    users = controller.User()

    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        res = {}
        res['Function'] = 'Overview'
        return {'res': res, 'kwargs': **kwargs}
