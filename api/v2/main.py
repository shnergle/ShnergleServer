import cherrypy

class Image:
    
    @staticmethod
    @cherrypy.expose
    def get():
        return 'Have an image!'


@cherrypy.expose
def index():
    return 'Hi'
