import cherrypy

@cherrypy.expose
def index():
    return 'Hi'
