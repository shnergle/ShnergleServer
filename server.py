import datetime
import json
import os

import cherrypy
import mysql.connector

import util


class User:

    @util.expose
    @util.protect
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
                             'CONCAT(LOWER(languages.code), "_",'
                                    'UPPER(lc.code)) as language'),
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
    @util.protect
    @util.mysqli
    @util.jsonp
    def set(self, cursor, facebook_token=None, twitter_token=None,
            facebook=None, twitter=None, forename=None, surname=None, age=None,
            birth_day=None, birth_month=None, birth_year=None, gender=None,
            staff=None, manager=None, promotion_perm=None, employee=None,
            venue_id=None, country=None, language=None, **kwargs):
        if not facebook_token:
            raise cherrypy.HTTPError(403)
        qry = {'select': 'COUNT(users.id) as count',
               'table':  'users',
               'where':  'users.facebook_token = %s',
               'limit':  1}
        cursor.execute(util.query(**qry), (facebook_token,))
        res = cursor.fetchone()['count']
        data = {'users.twitter_token':  twitter_token,
                'users.facebook':       facebook,
                'users.twitter':        twitter,
                'users.forename':       forename,
                'users.surname':        surname,
                'users.age':            util.to_int(age),
                'users.birth_day':      util.to_int(birth_day),
                'users.birth_month':    util.to_int(birth_month),
                'users.birth_year':     util.to_int(birth_year),
                'users.gender':         gender,
                'users.staff':          (datetime.datetime.utcnow()
                                         if util.to_bool(staff) else False),
                'users.manager':        util.to_bool(manager),
                'users.promotion_perm': util.to_bool(promotion_perm),
                'users.employee':       util.to_bool(employee),
                'users.venue_id':       venue_id}
        columns = []
        values = []
        for key, val in data.iteritems():
            if val:
                columns.append(key)
                values.append(val)
        if country:
            subqry = {'select': 'id',
                      'table':  'countries',
                      'where':  'countries.code = %s',
                      'limit':  1}
            cursor.execute(util.query(**subqry), (country.lower(),))
            subres = cursor.fetchone()['id']
            if subres:
                columns.append('users.country_id')
                values.append(subres)
        if language:
            lang = language.split('_')
            subqry = {'select': 'id',
                      'table':  'countries',
                      'where':  'countries.code = %s',
                      'limit':  1}
            cursor.execute(util.query(**subqry), (lang[1].lower(),))
            subres = cursor.fetchone()['id']
            if subres:
                subqry = {'select': 'id',
                          'table':  'languages',
                          'where':  ('languages.code = %s',
                                     'languages.country_id = %s'),
                          'limit':  1}
                cursor.execute(util.query(**subqry), (lang[0].lower(), subres))
                subres = cursor.fetchone()['id']
                if subres:
                    columns.append('users.language_id')
                    values.append(subres)
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
