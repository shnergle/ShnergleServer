import json
import os
from datetime import datetime
from functools import wraps

import cherrypy
import mysql.connector

from config import config


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
        cnx = mysql.connector.connect(**config)
        cnx.set_converter_class(MySQLConverterJSON)
        cursor = cnx.cursor(cursor_class=MySQLCursorDict)
        kwargs.update(cursor=cursor)
        try:
            res = func(*args, **kwargs)
        finally:
            cursor.close()
            cnx.close()
        return res
    return decorator


def implode(glue, list):
    return list if isinstance(list, str) else glue.join(list)


def query(select=None, table=None, left_join=None, on=None, where=None,
          limit=None):
    if select:
        qry = 'SELECT ' + implode(', ', select)
    if table:
        qry += ' FROM ' + implode(', ', table)
    if left_join:
        qry += ' LEFT JOIN (' + implode(', ', left_join) + ')'
    if on:
        qry += ' ON (' + implode(' AND ', on) + ')'
    if where:
        qry += ' WHERE ' + implode(' AND ', where)
    if limit:
        qry += ' LIMIT ' + str(limit)
    return qry


class User:

    @cherrypy.expose
    @mysqli
    @jsonp
    def get(self, cursor=None, **kwargs):
        cond = False
        if 'id' in kwargs:
            cond = 'users.id = %s'
            token = kwargs['id']
        elif 'facebook_token' in kwargs:
            cond = 'users.facebook_token = %s'
            token = kwargs['facebook_token']
        elif 'twitter_token' in kwargs:
            cond = 'users.twitter_token = %s'
            token = kwargs['twitter_token']
        qry = {'select':    ('users.id',
                             'users.facebook_token',
                             'users.twitter_token',
                             'users.facebook',
                             'users.twitter',
                             'users.forename',
                             'users.surname',
                             'users.age',
                             'users.birth_day',
                             'users.birth_month',
                             'users.birth_year',
                             'users.gender',
                             'users.image',
                             'users.staff',
                             'users.manager',
                             'users.venue_id',
                             'users.promotion_perm',
                             'users.rank',
                             'users.employee',
                             'users.joined',
                             'countries.code as country',
                             'lc.code as language_country',
                             'languages.code as language'),
               'table':      'users',
               'left_join': ('countries', 'countries lc', 'languages'),
               'on':        ('users.country_id = countries.id',
                             'users.language_id = languages.id',
                             'languages.country_id = lc.id')}
        if cond:
            qry.update({'where': cond, 'limit': 1})
            cursor.execute(query(**qry), token)
            res = cursor.fetchone()
        else:
            cursor.execute(query(**qry))
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


def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message},
                      separators=(',', ':'))


current_dir = os.path.dirname(os.path.abspath(__file__))
cp_config = {'/':            {'error_page.default': error},
             '/favicon.ico': {'tools.staticfile.on': True,
                              'tools.staticfile.filename':
                              os.path.join(current_dir, 'favicon.ico')}}
app = cherrypy.Application(ShnergleServer(), '/', cp_config)
