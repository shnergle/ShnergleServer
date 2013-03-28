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
        if id:
            id = '/' + str(id)
        return self._url + self.db + '/collections' + collection + id
