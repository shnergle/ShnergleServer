import json

import falcon


def auth(req, resp, params):
    pass


def json(req, resp, params):
    resp.body = json.dumps(resp.body)


class User():

    def __init__(self, db):
        self.db = db
    
    def on_get(self, req, resp, _id):
        resp.status = falcon.HTTP_200
        resp.body = {'success': True}
        
        
app = falcon.API(before=[auth], after=[json])
db = None
app.add_route('/users', User(db))
app.add_route('/1/users/{_id}', User(db))
