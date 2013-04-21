import json
import os

import cherrypy
import mysql.connector

import util


class User:

    @util.expose
    @util.mysqli
    @util.jsonp
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
            cursor.execute(util.query(**qry), token)
            res = cursor.fetchone()
        else:
            cursor.execute(util.query(**qry))
            res = [row for row in cursor]
        return res


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
