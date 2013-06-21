import calendar
import datetime
import json
import math
import os

import cherrypy

import azureutil
import util


class Image:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    def get(self, entity=None, entity_id=None, **kwargs):
        if not entity or not entity_id:
            raise cherrypy.HTTPError(404)
        image = azureutil.retrieve(entity, entity_id)
        if image:
            cherrypy.response.headers['Content-Type'] = 'image/jpg'
            return image
        raise cherrypy.HTTPError(404)
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, image=None, entity=None, entity_id=None,
            **kwargs):
        if not entity_id or entity not in ('user', 'venue', 'post'):
            raise cherrypy.HTTPError(403)
        return azureutil.store(image.file, entity, entity_id)
        

class Ranking:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, thresholds=None, **kwargs):
        if util.to_bool(thresholds):
            return self.thresholds(cursor)
        posts = {'select': 'COUNT(id) AS count',
                 'table': 'posts',
                 'where': 'user_id = ?'}
        cursor.execute(util.query(**posts), (user_id,))
        posts = cursor.fetchone()['count']
        for threshold in self.thresholds(cursor):
            if posts < threshold:
                res = 0
                break
        else:
            res = 3
        return res
    
    def thresholds(self, cursor):
        users = {'select': 'COUNT(id) AS count', 'table': 'users'}
        cursor.execute(util.query(**users))
        users = cursor.fetchone()['count']
        thresholds = []
        for percent in (0.8, 0.95, 0.99):
            number = math.floor(percent * users)
            thresholdqry = {'select':    ('COUNT(id) AS count',
                                          'user_id'),
                            'table':     'posts',
                            'group_by':  'user_id',
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
    def get(self, cursor=None, user_id=None, getall=None, facebook_id=None,
            **kwargs):
        qry = {'select':    ['id',
                             'facebook',
                             'twitter',
                             'forename',
                             'surname',
                             'age',
                             'birth_day',
                             'birth_month',
                             'birth_year',
                             'gender',
                             'staff',
                             'manager',
                             'venue_id',
                             'promotion_perm',
                             'employee',
                             'joined',
                             'country',
                             'language',
                             'email',
                             'top5'
                             ],
               'table':     'users',
               'order_by':  'id'}
        if util.to_bool(getall):
            cursor.execute(util.query(**qry))
            return [util.row_to_dict(cursor, row) for row in cursor]
        else:
            qry['select'].append('twitter_id')
            qry['select'].append('twitter_token')
            qry['select'].append('twitter_secret')
            qry.update({'where': 'id = ?', 'limit': 1})
            cursor.execute(util.query(**qry), (user_id,))
            res = cursor.fetchone()
            return util.row_to_dict(cursor, res)
    
    @util.expose
    @util.protect
    @util.db
    @util.jsonp
    def set(self, cursor=None, facebook_id=None, twitter_token=None,
            facebook=None, twitter=None, forename=None, surname=None, age=None,
            birth_day=None, birth_month=None, birth_year=None, gender=None,
            staff=None, manager=None, promotion_perm=None, employee=None,
            venue_id=None, country=None, language=None, email=None, top5=None,
            twitter_id=None, twitter_secret=None, **kwargs):
        if not facebook_id:
            raise cherrypy.HTTPError(403)
        qry = {'select':   'COUNT(id) AS count',
               'table':    'users',
               'where':    'facebook_id = ?'}
        cursor.execute(util.query(**qry), (facebook_id,))
        res = cursor.fetchone()['count']
        data = {'twitter_id':     twitter_id,
                'twitter_token':  twitter_token,
                'twitter_secret': twitter_secret,
                'facebook':       facebook,
                'twitter':        twitter,
                'forename':       forename,
                'surname':        surname,
                'age':            util.to_int(age),
                'birth_day':      util.to_int(birth_day),
                'birth_month':    util.to_int(birth_month),
                'birth_year':     util.to_int(birth_year),
                'gender':         gender,
                'staff':          (datetime.datetime.utcnow()
                                   if util.to_bool(staff) else None),
                'manager':        util.to_bool(manager),
                'promotion_perm': util.to_bool(promotion_perm),
                'employee':       util.to_bool(employee),
                'venue_id':       venue_id,
                'country':        country,
                'language':       language,
                'email':          email,
                'top5':           util.to_bool(top5)}
        columns = []
        values = []
        for key, val in data.iteritems():
            if val != None:
                columns.append(key)
                values.append(val)
        values.append(facebook_id)
        if res:
            qry = {'update':     'users',
                   'set_values': columns,
                   'where':      'facebook_id = ?'}
            cursor.execute(util.query(**qry), values)
        else:
            columns.append('facebook_id')
            columns.append('joined')
            values.append(calendar.timegm(
                datetime.datetime.utcnow().utctimetuple()))
            qry = {'insert_into': 'users',
                   'columns':     columns}
            cursor.execute(util.query(**qry), values)
        return True


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
            cursor.execute(util.query(**qry), (calendar.timegm(
                datetime.datetime.utcnow().utctimetuple()),
                                               user_id))
        else:
            qry = {'insert_into': 'user_searches',
                   'columns':     ('user_id', 'term', 'time')}
            cursor.execute(util.query(**qry), (user_id, term, calendar.timegm(
                datetime.datetime.utcnow().utctimetuple())))
        return True
class Category:

    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, id=None, **kwargs):
        qry = {'select':   ('id', 'type'),
            'table':    'venue_categories',
            'where':    '',
            'order_by': 'type DESC'}
        cursor.execute(util.query(**qry), (id,))
        return [row for row in cursor]
    


class Venue:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, id=None, **kwargs):
        qry = {'select':   ('id', 'name'),
            'table':    'venues',
            'where':    '',
            'order_by': 'name DESC'}
        cursor.execute(util.query(**qry), (id,))
        return [row for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, venue_id=None, name=None, address=None, country_id=None, phone=None, email=None, email_verified=None, category_id=None, tooltip=None, tonight=None, website=None, facebook=None, twitter=None, facebook_token=None, twitter_token=None, lat=None, lon=None, timezone=None, image=None, official=None, verified=None, costumer_spend=None, authenticated=None, **kwargs):
        '''Make this work later.
        qry = {'select':    'id', 
                'table':    'venues', 
                'where':    'id = ?', 
                'order_by': 'id', 
                'limit':    1}
        cursor.execute(util.query(**qry),(venue_id))
        res = cursor.fetchone()
        if res:
            # UPDATE THE VENUE
        else:
            # TEST IF ANY OF THE FIELDS REQUIRED ARE 'None' - THEN INSERT
       ''' 
        return True



class ShnergleServer:
    images = Image()
    rankings = Ranking()
    users = User()
    venues = Venue()
    user_searches = UserSearch()
    categories = Category()
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
