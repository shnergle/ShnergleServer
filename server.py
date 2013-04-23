import json
import os

import cherrypy
import mysql.connector

import util


class User:

    @util.expose
    @util.mysqli
    @util.jsonp
    def get(self, cursor, id=None, facebook_token=None, **kwargs):
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
        if facebook_token:
            qry.update({'where': 'users.facebook_token = %s', 'limit': 1})
            cursor.execute(util.query(**qry), (facebook_token,))
            res = cursor.fetchone()
        else:
            cursor.execute(util.query(**qry))
            res = [row for row in cursor]
        return res
        
    @util.expose
    @util.mysqli
    @util.jsonp
    def set(self, cursor, facebook_token=None, twitter_token=None,
            forename=None, surname=None, **kwargs):
        if not facebook_token:
            raise cherrypy.HTTPError(403)
        qry = {'select': 'COUNT(users.id) as count',
               'table': 'users',
               'where': 'users.facebook_token = %s'}
        cursor.execute(util.query(**qry), (facebook_token,))
        res = cursor.fetchone()['count']
        columns = []
        values = []
        if twitter_token:
            columns.append('users.twitter_token')
            values.append(twitter_token)
        if forename:
            columns.append('users.forename')
            values.append(forename)
        if surname:
            columns.append('users.surname')
            values.append(surname)
        values.append(facebook_token)
        if res:
            qry = {'update':     'users',
                   'set_values': columns,
                   'where':      'users.facebook_token = %s'}
            cursor.execute(util.query(**qry), values)
        else:
            columns.append('users.facebook_token')
            qry = {'insert_into': 'users',
                   'columns':     columns}
            cursor.execute(util.query(**qry), values)


class ShnergleServer:
    users = User()

    def __init__(self):
        self.v1 = self

    @staticmethod
    def error(status, message, traceback, version):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({'status': status, 'message': message},
                          separators=(',', ':'))


current_dir = os.path.dirname(os.path.abspath(__file__))
cp_config = {'/':            {'error_page.default': ShnergleServer.error},
             '/favicon.ico': {'tools.staticfile.on': True,
                              'tools.staticfile.filename':
                              os.path.join(current_dir, 'favicon.ico')}}
app = cherrypy.Application(ShnergleServer(), '/', cp_config)
