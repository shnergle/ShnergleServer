import datetime
import json
import math
import os

import cherrypy
import mysql.connector

import util


class User:

    @util.expose
    @util.protect
    @util.mysqli
    @util.auth
    @util.jsonp
    def get(self, cursor, user_id, getall=None, facebook_token=None, **kwargs):
        qry = {'select':    ['users.id',
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
                             'countries.code AS country',
                             'CONCAT(LOWER(languages.code), "_",'
                                    'UPPER(lc.code)) AS language',
                             'COUNT(posts.id) AS post_count'],
               'table':      'users',
               'left_join': ('countries',
                             'countries lc',
                             'languages',
                             'posts'),
               'on':        ('users.country_id = countries.id',
                             'users.language_id = languages.id',
                             'languages.country_id = lc.id',
                             'posts.user_id = users.id'),
               'group_by':   'users.id'}
                             
        users = {'select': 'COUNT(users.id) AS count', 'table': 'users'}
        cursor.execute(util.query(**users))
        users = cursor.fetchone()['count']
        thresholds = []
        for percent in (0.8, 0.95, 0.99):
            number = math.floor(percent * users)
            thresholdqry = {'select':    'COUNT(posts.id) AS count',
                            'table':     'posts',
                            'group_by':  'posts.id',
                            'order_by':  'count',
                            'limit':     (number - 1, number)}
            cursor.execute(util.query(**thresholdqry))
            count = cursor.fetchone()
            thresholds.append(count['count'] if count else 0)

        if util.to_bool(getall):
            cursor.execute(util.query(**qry))
            res = []
            for row in cursor:
                posts = row.pop('post_count')
                for threshold in thresholds:
                    if posts < threshold:
                        row['ranking'] = 0
                        break
                else:
                    row['ranking'] = len(thresholds)
                res.append(row)
        else:
            qry['select'].append('users.facebook_token')
            qry['select'].append('users.twitter_token')
            qry.update({'where': 'users.id = %s', 'limit': 1})
            cursor.execute(util.query(**qry), (user_id,))
            res = cursor.fetchone()
            posts = res.pop('post_count')
            for threshold in thresholds:
                if posts < threshold:
                    res['ranking'] = 0
                    break
            else:
                res['ranking'] = len(thresholds)
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
        qry = {'select': 'COUNT(users.id) AS count',
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
            subres = cursor.fetchone()
            if subres:
                columns.append('users.country_id')
                values.append(subres['id'])
        if language:
            lang = language.split('_')
            subqry = {'select': 'id',
                      'table':  'countries',
                      'where':  'countries.code = %s',
                      'limit':  1}
            cursor.execute(util.query(**subqry), (lang[1].lower(),))
            subres = cursor.fetchone()
            if subres:
                subqry = {'select': 'id',
                          'table':  'languages',
                          'where':  ('languages.code = %s',
                                     'languages.country_id = %s'),
                          'limit':  1}
                cursor.execute(util.query(**subqry), (lang[0].lower(),
                                                      subres['id']))
                subres = cursor.fetchone()
                if subres:
                    columns.append('users.language_id')
                    values.append(subres['id'])
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
        return cursor.lastrowid


class UserSearch:
    
    @util.expose
    @util.protect
    @util.mysqli
    @util.auth
    @util.jsonp
    def get(self, cursor, user_id, **kwargs):
        qry = {'select':   ('id', 'term', 'time'),
               'table':    'user_searches',
               'where':    'user_id = %s',
               'order_by': 'time DESC'}
        cursor.execute(util.query(**qry), (user_id,))
        return [row for row in cursor]
    
    @util.expose
    @util.protect
    @util.mysqli
    @util.auth
    @util.jsonp
    def set(self, cursor, user_id, term=None, **kwargs):
        qry = {'select': 'id',
               'table':  'user_searches',
               'where':  ('user_id = %s', 'term = %s'),
               'limit':  1}
        cursor.execute(util.query(**qry), (user_id, term))
        res = cursor.fetchone()
        if res:
            qry = {'update':  'user_searches',
                   'columns': ('time'),
                   'where':   'user_id = %s'}
            cursor.execute(util.query(**qry), (datetime.datetime.utcnow(),
                                               user_id))
        else:
            qry = {'insert_into': 'user_searches',
                   'columns':     ('user_id', 'term')}
            cursor.execute(util.query(**qry), (user_id, term))
        return cursor.lastrowid


class ShnergleServer:
    users = User()
    user_searches = UserSearch()

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
