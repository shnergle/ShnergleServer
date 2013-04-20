import cherrypy
import json

import mysql.connector

from datetime import datetime
from functools import wraps

def dont_cache():
    cherrypy.response.headers['Expires'] = datetime.utcnow().strftime(
        '%a, %d %b %Y %H:%M:%S GMT')
    cherrypy.response.headers['Cache-Control'] = ('no-store, '
                                                  'no-cache, '
                                                  'must-revalidate, '
                                                  'post-check=0, '
                                                  'pre-check=0')


def jsonp(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        dont_cache()
        res = json.dumps(func(*args, **kwargs), separators=(',', ':'))
        callback = kwargs.pop('callback', False)
        if callback:
            cherrypy.response.headers['Content-Type'] = ('text/javascript; '
                                                         'charset=utf-8')
            res = callback + '(' + res + ');'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/json'
        return res
    return decorator


class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
    def _row_to_python(self, rowdata, desc=None):
        row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
        if row:
            return dict(zip(self.column_names, row))
        return None


class MySQLConverterJSON(mysql.connector.conversion.MySQLConverter):
    _DATETIME_to_python =  mysql.connector.conversion.MySQLConverter._str
    _TIMESTAMP_to_python = _DATETIME_to_python


def mysqli(func):
    @wraps(func)
    def decorator(*args, **kwargs):
	def decode(data):
	    ret = {'raw': True}
	    for key, val in data.iteritems():
		ret[str(key)] = str(val)
	    return ret
        with open('config.json') as config:
	    cnx = mysql.connector.connect(**decode(json.load(config)))
        cnx.set_converter_class(MySQLConverterJSON)
        cursor = cnx.cursor(cursor_class=MySQLCursorDict)
        try:
	    res = func(*args, cursor=cursor, **kwargs)
	finally:
            cursor.close()
	    cnx.close()
	return res
    return decorator


class User:
    @cherrypy.expose
    @mysqli
    @jsonp
    def get(self, cursor=None, **kwargs):
	cond = False
	if 'id' in kwargs:
	    cond = 'users.id = %s'
	    id = kwargs['id']
	elif 'facebook_token' in kwargs:
	    cond = 'users.facebook_token = %s'
	    id = kwargs['facebook_token']
	elif 'twitter_token' in kwargs:
	    cond = 'users.twitter_token = %s'
	    id = kwargs['twitter_token']
	query = '''SELECT
		       users.id,
		       users.facebook_token,
		       users.twitter_token,
		       users.facebook,
		       users.twitter,
		       users.forename,
		       users.surname,
		       users.age,
		       users.birth_day,
		       users.birth_month,
		       users.birth_year,
		       users.gender,
		       users.image,
		       users.staff,
		       users.manager,
		       users.venue_id,
		       users.promotion_perm,
		       users.rank,
		       users.employee,
		       users.joined,
		       countries.code as country,
		       lc.code as language_country,
		       languages.code as language
		    FROM
		       users
		    LEFT JOIN (countries, countries lc, languages)
		    ON (
		       users.country_id = countries.id AND
		       users.language_id = languages.id AND
		       languages.country_id = lc.id
		    )'''
	if cond:
	    cursor.execute(query + ' WHERE ' + cond + ' LIMIT 1', (id))
	    res = cursor.fetchone()
	else:
	    cursor.execute(query)
	    res = [row for row in cursor]
        return res

class Venue:
    @cherrypy.expose
    @jsonp
    def get(self, **kwargs):
        return {}
        
    @cherrypy.expose
    @jsonp
    def set(self, **kwargs):
        return {}
        
    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        return {}


class ShnergleServer:
    users = User()
    venues = Venue()

    def __init__(self):
        self.v1 = self

    @cherrypy.expose
    @jsonp
    def index(self, **kwargs):
        res = {}
        res['Function'] = 'Overview'
        return res
