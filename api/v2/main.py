import cherrypy
import json

class image:
    
    @staticmethod
    @cherrypy.expose
    def get():
        return 'Have an image!'
        
        
class user:
    
    @staticmethod
    @cherrypy.expose
    def get():
        cursor = cherrypy.thread_data.db.cursor()
        try:
            cursor.execute('SELECT TOP(1) * FROM users WHERE id = 1')
            json.dumps({t[0]: val for t, val in zip(cursor.description, cursor.fetchone())})
        finally:
            cursor.commit()
            cursor.close()
        return res


@cherrypy.expose
def index():
    return 'Hi'
