import cherrypy

class Main:
    @cherrypy.expose
    def index(self):
        return 'Hi'
