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
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def get():
        cursor = cherrypy.thread_data.db.cursor()
        try:
            cursor.execute('SELECT TOP(1) * FROM users WHERE id = 1')
            res = {t[0]: val for t, val in zip(cursor.description, cursor.fetchone())}
        finally:
            cursor.commit()
            cursor.close()
        return res
       
    @staticmethod
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def login():
        cursor = cherrypy.thread_data.db.cursor()
        try:
            cursor.execute('SELECT TOP(1) * FROM users WHERE facebook_id = ?', cherrypy.request.json['facebook_id'])
            res = {t[0]: val for t, val in zip(cursor.description, cursor.fetchone())}
        finally:
            cursor.commit()
            cursor.close()
        return res


@cherrypy.expose
def index():
    return 'Hi'
