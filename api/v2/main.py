import cherrypy

class Image:
    
    @cherrypy.expose
    def get():
        return 'Have an image!'


@cherrypy.expose
def index():
    return 'Hi'
