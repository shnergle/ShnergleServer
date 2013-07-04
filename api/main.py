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
    def get(self, cursor=None, entity=None, entity_id=None, **kwargs):
        if not entity or not entity_id:
            raise cherrypy.HTTPError(404)
        if entity == 'venue':
            entity = 'post'
            qry = {'select':   ('id', 'venue_id', 'time'),
                   'table':    'posts',
                   'where':    'venue_id = ?',
                   'order_by': 'time DESC'}
            cursor.execute(util.query(**qry), (entity_id,))
            entity_id = str(cursor.fetchone()['id'])
        image = azureutil.retrieve(entity, entity_id)
        if image:
            cherrypy.response.headers['Content-Type'] = 'image/jpeg'
            return image
        raise cherrypy.HTTPError(404)
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, image=None, entity=None, entity_id=None,
            **kwargs):
        if not entity_id or entity != 'post':
            raise cherrypy.HTTPError(403)
        return azureutil.store(image.file, entity, entity_id)
     

class Post:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, venue_id=None, **kwargs):
        qry = {'select':   ('posts.id', 'user_id', 'posts.venue_id', 'lat',
                            'lon', 'caption', 'time', 'users.forename', 
                            'users.surname'),
               'left_join': 'users',
               'on':        'posts.user_id = users.id',
               'table':     'posts',
               'where':     'posts.venue_id = ?',
               'order_by':  'time DESC'}
        cursor.execute(util.query(**qry), (venue_id,))
        return [util.row_to_dict(cursor, row) for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, lat=None, lon=None,
            caption=None, **kwargs):
        qry = {'insert_into': 'posts',
               'columns':     ('user_id', 'venue_id', 'lat', 'lon', 'caption',
                               'time')}
        cursor.execute(util.query(**qry), (user_id, venue_id, lat, lon, caption,
                                           util.now()))
        cursor.execute(util.query(last_id=True))
        return int(cursor.fetchone()['identity'])
           

class PostShare:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, post_id=None, media_id=None,
            **kwargs):
        qry = {'insert_into': 'post_shares',
               'columns':     ('user_id', 'post_id', 'media_id', 'time')}
        cursor.execute(util.query(**qry), (user_id, venue_id, menu_id,
                                           util.now()))
        return True
        
        
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
                             'top5',
                             'save_locally'
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
            twitter_id=None, twitter_secret=None, save_locally=None, **kwargs):
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
                'staff':          (util.now() if util.to_bool(staff) else None),
                'manager':        util.to_bool(manager),
                'promotion_perm': util.to_bool(promotion_perm),
                'employee':       util.to_bool(employee),
                'venue_id':       venue_id,
                'country':        country,
                'language':       language,
                'email':          email,
                'top5':           util.to_bool(top5),
                'save_locally':   util.to_bool(save_locally)}
        columns = []
        values = []
        for key, val in data.iteritems():
            if val != None:
                columns.append(key)
                if val is not True and val is not False:
                    values.append(val)
                else:
                    if val:
                        values.append('1')
                    else:
                        values.append('0')
        values.append(facebook_id)
        if res:
            qry = {'update':     'users',
                   'set_values': columns,
                   'where':      'facebook_id = ?'}
            cursor.execute(util.query(**qry), values)
        else:
            columns.append('facebook_id')
            columns.append('joined')
            values.append(util.now())
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
        return [util.row_to_dict(cursor, row) for row in cursor]
    
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
            cursor.execute(util.query(**qry), (util.now(), user_id))
        else:
            qry = {'insert_into': 'user_searches',
                   'columns':     ('user_id', 'term', 'time')}
            cursor.execute(util.query(**qry), (user_id, term, util.now()))
        return True


class Category:

    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, **kwargs):
        qry = {'select':   ('id', 'type'),
            'table':    'venue_categories',
            'where':    '',
            'order_by': 'type ASC'}
        cursor.execute(util.query(**qry))
        return [util.row_to_dict(cursor, row) for row in cursor]
    

class Venue:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, term=None, **kwargs):
        if term:
            fields = ('id', 'name')
            where = ("name LIKE ?",)
        else:
            fields = ('id', 'name', 'address', 'country', 'phone', 'email',
                      'email_verified', 'category_id', 'tooltip', 'tonight',
                      'website', 'facebook', 'twitter', 'facebook_id',
                      'twitter_id', 'twitter_token', 'twitter_secret', 'lat',
                      'lon', 'timezone', 'offical', 'verified',
                      'customer_spend', 'authenticated', 'creator')
            where = ''
        qry = {'select':   fields,
            'table':    'venues',
            'where':    where,
            'order_by': 'name ASC'}
        if term:
            cursor.execute(util.query(**qry), ("%" + term + "%",))
            return [util.row_to_dict(cursor, row) for row in cursor]
        else:
            cursor.execute(util.query(**qry))
            rows = [util.row_to_dict(cursor, row) for row in cursor]
            for row in rows:
                row = self.promo(cursor, row)
            return rows
    
    def promo(self, cursor, row):
        promo_qry = {'select':   ('id', 'title', 'description',
                                  'passcode', 'start', '[end]', 'maximum',
                                  'creator'),
                     'table':    'promotions',
                     'where':    'venue_id = ?',
                     'order_by': 'id DESC',
                     'limit':    1}
        #cursor.execute(util.query(**promo_qry), (row['id'],))
        result = cursor.fetchone()
        if result:
            row['promotion'] = result
        return row
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, facebook_id=None, user_id=None, venue_id=None,
            name=None, address=None, country=None, phone=None, email=None,
            email_verified=None, category_id=None, tooltip=None, tonight=None,
            website=None, facebook=None, twitter=None, v_facebook_id=None,
            twitter_id=None, twitter_token=None, twitter_secret=None, lat=None,
            lon=None, timezone=None, offical=None, verified=None,
            customer_spend=None, authenticated=None, **kwargs):
        data = {'name':           name,
                'address':        address,
                'country':        country,
                'phone':          phone,
                'email':          email,
                'email_verified': util.to_bool(email_verified),
                'category_id':    util.to_int(category_id),
                'tooltip':        tooltip,
                'tonight':        tonight,
                'website':        website,
                'facebook':       facebook,
                'twitter':        twitter,
                'facebook_id':    v_facebook_id,
                'twitter_id':     twitter_id,
                'twitter_token':  twitter_token,
                'twitter_secret': twitter_secret,
                'lat':            util.to_float(lat),
                'lon':            util.to_float(lon),
                'timezone':       util.to_int(timezone),
                'offical':        util.to_bool(offical),
                'verified':       util.to_bool(offical),
                'customer_spend': util.to_float(customer_spend),
                'authenticated':  util.to_bool(authenticated),
                'creator':        user_id}
        columns = []
        values = []
        for key, val in data.iteritems():
            if val != None:
                columns.append(key)
                values.append(val)
        if venue_id:
            qry = {'update':     'venues',
                   'set_values': columns,
                   'where':      'id = ?'}
            values.append(venue_id)
            cursor.execute(util.query(**qry), values)
        else:
            qry = {'insert_into': 'venues',
                   'columns':     columns}
            cursor.execute(util.query(**qry), values)
        return True
    
 
class VenueFavourite:
    
    @util.expose
    @util.jsonp
    def get(self, **kwargs):
        return None
        
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, following=None,
            **kwargs):
        qry = {'select': 'COUNT(id) AS count',
               'table': 'venue_favourites',
               'where': ('user_id = ?', 'venue_id = ?')}
        cursor.execute(util.query(**qry), (user_id, venue_id))
        res = cursor.fetchone()['count']
        if util.to_bool(following) and not res:
            qry = {'insert_into': 'venue_favourites',
                   'columns':      ('user_id, venue_id')}
            cursor.execute(util.query(**qry), (user_id, venue_id))
        elif not util.to_bool(following) and res:
            #delete
            pass
        return True      


class VenueShare:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, media_id=None,
            **kwargs):
        qry = {'insert_into': 'venue_shares',
               'columns':     ('user_id', 'venue_id', 'media_id', 'time')}
        cursor.execute(util.query(**qry), (user_id, venue_id, menu_id,
                                           util.now()))
        return True
        

class ShnergleServer:
    images = Image()
    posts = Post()
    post_shares = PostShare()
    rankings = Ranking()
    users = User()
    venues = Venue()
    venue_favourites = VenueFavourite()
    venue_shares = VenueShare()
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
