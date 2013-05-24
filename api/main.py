import datetime
import json
import math
import os

import cherrypy

import util


class Ranking:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, thresholds=None):
        if util.to_bool(thresholds):
            return self.thresholds()
        else:
            thresholds = self.thresholds()
            posts = {'select': 'COUNT(posts.id) AS count',
                     'table': 'posts',
                     'where': 'users.id = ?'}
            cursor.execute(util.query(**users), (user_id,))
            posts = cursor.fetchone()['count']
            for threshold in thresholds:
                if posts < threshold:
                    res = 0
                    break
            else:
                res = len(thresholds)
            return res
            
            
    def thresholds(self):
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
                            'limit':     (number - 1, 1)}
            cursor.execute(util.query(**thresholdqry))
            count = cursor.fetchone()
            thresholds.append(count['count'] if count else 0)
        return thresholds

class User:

    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, getall=None, facebook_token=None,
            **kwargs):
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
                             'users.country',
                             'users.language',
                             'users.email',
                             'users.top5'
                             ],
               'table':     'users',
               'left_join': 'posts',
               'on':        'posts.user_id = users.id',
               'order_by':  'users.id'}

        if util.to_bool(getall):
            cursor.execute(util.query(**qry))
            return [util.row_to_dict(cursor, row) for row in cursor]
        else:
            qry['select'].append('users.facebook_token')
            qry['select'].append('users.twitter_token')
            qry.update({'where': 'users.id = ?', 'limit': 1})
            cursor.execute(util.query(**qry), (user_id,))
            res = cursor.fetchone()
            return util.row_to_dict(cursor, row)
        
    @util.expose
    @util.protect
    @util.db
    @util.jsonp
    def set(self, cursor=None, facebook_token=None, twitter_token=None,
            facebook=None, twitter=None, forename=None, surname=None, age=None,
            birth_day=None, birth_month=None, birth_year=None, gender=None,
            staff=None, manager=None, promotion_perm=None, employee=None,
            venue_id=None, country=None, language=None, email=None, top5=None,
            **kwargs):
        if not facebook_token:
            raise cherrypy.HTTPError(403)
        qry = {'select':   'COUNT(users.id) AS count',
               'table':    'users',
               'where':    'users.facebook_token = ?',
               'order_by': 'users.id',
               'limit':    1}
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
                'users.venue_id':       venue_id,
                'users.country':        country,
                'users.language':       language,
                'users.email':          email,
                'users.top5':           util.to_bool(top5)}
        columns = []
        values = []
        for key, val in data.iteritems():
            if val:
                columns.append(key)
                values.append(val)
        values.append(facebook_token)
        if res:
            qry = {'update':     'users',
                   'set_values': columns,
                   'where':      'users.facebook_token = ?'}
            cursor.execute(util.query(**qry), values)
        else:
            columns.append('users.facebook_token')
            columns.append('users.joined')
            values.append(datetime.datetime.utcnow())
            qry = {'insert_into': 'users',
                   'columns':     columns}
            cursor.execute(util.query(**qry), values)
        return cursor.lastrowid


class UserSearch:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, **kwargs):
        qry = {'select':   ('id', 'term', 'time'),
               'table':    'user_searches',
               'where':    'user_id = ?',
               'order_by': 'time DESC'}
        cursor.execute(util.query(**qry), (user_id,))
        return [row for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, term=None, **kwargs):
        qry = {'select':   'id',
               'table':    'user_searches',
               'where':    ('user_id = ?', 'term = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, term))
        res = cursor.fetchone()
        if res:
            qry = {'update':  'user_searches',
                   'columns': ('time'),
                   'where':   'user_id = ?'}
            cursor.execute(util.query(**qry), (datetime.datetime.utcnow(),
                                               user_id))
        else:
            qry = {'insert_into': 'user_searches',
                   'columns':     ('user_id', 'term')}
            cursor.execute(util.query(**qry), (user_id, term))
        return cursor.lastrowid


class ShnergleServer:
    rankings = Ranking()
    users = User()
    user_searches = UserSearch()

    def __init__(self):
        self.v1 = self

    @staticmethod
    def error(status, message, traceback, version):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({'status': status,
                           'message': message,
                           'traceback': traceback},
                          separators=(',', ':'))


cherrypy.engine.subscribe('start_thread', util.connect)
current_dir = os.path.dirname(os.path.abspath(__file__))
cp_config = {'/':            {'error_page.default': ShnergleServer.error},
             '/favicon.ico': {'tools.staticfile.on': True,
                              'tools.staticfile.filename':
                              os.path.join(current_dir, 'favicon.ico')}}
app = cherrypy.Application(ShnergleServer(), '/', cp_config)
