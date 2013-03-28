import requests

class MongoRest:
    _apikeyp = 'apiKey'
    _apikey = 'O7VCBY3vn25Qpa3byNmRFN920L7KOPIj'
    _url = 'https://api.mongolab.com/api/1/databases/'
    
    def __init__(self, db='shnergle'):
        self.db = db
        
    def url(self, collection='', id='', args={}):
        if collection:
            collection = '/' + collection
        if id:
            id = '/' + str(id)
        args[self._apikeyp] = self._apikey
        args_str = '&'.join(
            [key + '=' + value for key, value in args.iteritems()])
        if args_str:
            args_str = '?' + args_str
        return self._url + self.db + '/collections' + collection + id + args_str
