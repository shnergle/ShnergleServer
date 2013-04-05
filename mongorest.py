import requests
import json

class MongoRest:
    _apikeyp = 'apiKey'
    _url = 'https://api.mongolab.com/api/1/databases/'
    
    def __init__(self, db='shnergle'):
        self.db = db
        with open('config.json') as config:
            self._apikey = json.load(config)['mongoApiKey']
        
    def url(self, collection='', id=''):
        if collection:
            collection = '/' + collection
        if str(id):
            id = '/' + str(id)
        return self._url + self.db + '/collections' + collection + id
    
    def secure(self, data):
        data.pop(self._apikeyp, True)
        data.pop('_id', True)
        return json.dumps(data)
        
    def get(self, collection='', id=''):
        return requests.get(self.url(collection, id), params={self._apikeyp: self._apikey}).json()
        
    def put(self, collection='', id='', data={}):
        return requests.put(self.url(collection, id), params={self._apikeyp: self._apikey}, headers={'content-type': 'application/json'}, data=self.secure(data)).json()
        
    def post(self, collection='', data={}):
        return requests.post(self.url(collection), params={self._apikeyp: self._apikey}, headers={'content-type': 'application/json'}, data=self.secure(data)).json()
