import requests

class MongoRest:
    _apikeyp = 'apiKey'
    _apikey = 'O7VCBY3vn25Qpa3byNmRFN920L7KOPIj'
    _url = 'https://api.mongolab.com/api/1/databases/'
    
    def __init__(self, db='shnergle'):
        self.db = db
        
    def url(self, collection='', id=''):
        if collection:
            collection = '/' + collection
        if id:
            id = '/' + str(id)
        return self._url + self.db + '/collections' + collection + id
