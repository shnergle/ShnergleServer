import cherrypy
from sql import *
from sql.aggregate import *
from sql.conditionals import *


def decorate(func):
    def decorator(*args, **kwargs):
        if kwargs.pop('app_secret', False) != os.environ['APP_SECRET']:
            raise cherrypy.HTTPError(401)
        cursor = cherrypy.thread_data.db.cursor()
        data = cherrypy.request.json
        try:
            return staticmethod(
                       cherrypy.expose(
                           cherrypy.tools.json_in()(
                               cherrypy.tools.json_out()(
                                   func(cursor, data, *args, **kwargs)
                               )
                           )
                       )
                   )
        finally:
            cursor.commit()
            cursor.close()
    return decorator
    

def one(cursor, query):
    res = cursor.execute(*query).fetchone()
    return {d[0]: v for d, v in zip(cursor.description, res)}
    
    
def none(cursor, query):
    return cursor.execute(*query).rowcount
    

def all(cursor, query):
    res = cursor.execute(*query).fetchall()
    return [{d[0]: v for d, v in zip(cursor.description, row)} for row in res]


class images:
    
    @decorate
    def get():
        return 'Have an image!'
        
        
class users:
    
    users = Table('users')
    
    @decorate
    def get(cursor, data):
        query = users.select(where = users.id == data['id'])
        return one(cursor, query)
       
    @decorate
    def login(cursor, data):
        query = users.update(data.keys(), data.values())
        query.where = user.facebook_id == data['facebook_id']
        if none(cursor, query) == 0:
            query = users.insert(data.keys(), data.values())
            none(cursor, query)
        query = users.select(where = users.facebook_id == data['facebook_id'])
        return one(cursor, query)
        
    @decorate
    def set(cursor, data):
        query = users.update(data.keys(), data.values())
        query.where = user.facebook_id == data['facebook_id']
        return none(cursor, query)
        
    @cherrypy.expose
    @staticmethod
    @cherrypy.tools.json_in
    @cherrypy.tools.json_out
    def index():
        return 'Hi!'
        
@cherrypy.expose
def index():
    return 'Hi!'
