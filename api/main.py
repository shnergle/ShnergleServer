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
    def get(self, cursor=None, user_id=None, entity=None, entity_id=None,
            **kwargs):
        if not entity or not entity_id:
            raise cherrypy.HTTPError(404)
        if entity == 'venue':
            entity = 'post'
            venue_id = entity_id
            subqry = {'select':   'COUNT(id)',
                      'table':    'post_reports',
                      'where':    ('post_id = posts.id')}
            qry = {'select':   ('id', 'venue_id', 'time'),
                   'table':    'posts',
                   'where':    ('venue_id = ?', 'hidden = 0',
                                '(' + util.query(**subqry) + ') < 3'),
                   'order_by': 'time DESC'}
            cursor.execute(util.query(**qry), (entity_id,))
            entity_id = str(cursor.fetchone().id)
            qry = {'insert_into': 'venue_loads',
                   'columns':     ('user_id', 'venue_id', 'time')}
            cursor.execute(util.query(**qry), (user_id, venue_id, util.now()))
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
    def get(self, cursor=None, user_id=None, venue_id=None, **kwargs):
        if (venue_id):
            subqry = {'select':   'COUNT(id)',
                      'table':    'post_reports',
                      'where':    ('post_id = posts.id')}
            qry = {'select':   ('posts.id', 'user_id', 'posts.venue_id', 'caption',
                                'time', 'hidden', 'users.forename',
                                'users.surname'),
                   'left_join': 'users',
                   'on':        'posts.user_id = users.id',
                   'table':     'posts',
                   'where':     ('posts.venue_id = ?', 'hidden = 0',
                                 '(' + util.query(**subqry) + ') < 3',
                                 'time > ' + str(util.now() - 691200)),
                   'order_by':  'time DESC'}
            cursor.execute(util.query(**qry), (venue_id,))
        else:
            qry = {'select':   ('posts.id', 'venues.name', 'posts.time'),
                   'left_join': 'venues',
                   'on':        'posts.venue_id = venues.id',
                   'table':     'posts',
                   'where':     ('posts.user_id = ?'),
                   'order_by':  'time DESC'}
            cursor.execute(util.query(**qry), (user_id,))
        return [util.row_to_dict(cursor, row) for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, caption=None,
            hide=None, post_id=None, **kwargs):
        if post_id and util.to_bool(hide):
            qry = {'update':     'posts',
                   'set_values': ('hidden'),
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), ('1', post_id))
            return post_id
        else:
            qry = {'insert_into': 'posts',
                   'columns':     ('user_id', 'venue_id', 'caption', 'time')}
            cursor.execute(util.query(**qry), (user_id, venue_id, caption,
                                               util.now()))
            cursor.execute(util.query(last_id=True))
            return int(cursor.fetchone().identity)


class PostLike:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, post_id=None, **kwargs):
        qry = {'select':   'id',
               'table':    'post_likes',
               'where':    ('user_id = ?', 'post_id = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, post_id))
        res = cursor.fetchone()
        if not res:
            qry = {'insert_into': 'post_likes',
                   'columns':     ('user_id', 'post_id')}
            cursor.execute(util.query(**qry), (user_id, post_id))
        return True


class PostReport:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, post_id=None, **kwargs):
        qry = {'select':   'id',
               'table':    'post_reports',
               'where':    ('user_id = ?', 'post_id = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, post_id))
        res = cursor.fetchone()
        if not res:
            qry = {'insert_into': 'post_reports',
                   'columns':     ('user_id', 'post_id')}
            cursor.execute(util.query(**qry), (user_id, post_id))
        return True


class PostShare:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, post_id=None, media_id=None,
            **kwargs):
        qry = {'insert_into': 'post_shares',
               'columns':     ('user_id', 'post_id', 'media_id')}
        cursor.execute(util.query(**qry), (user_id, post_id, media_id))
        return True
        

class PostView:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, post_id=None, **kwargs):
        qry = {'insert_into': 'post_views',
               'columns':     ('user_id', 'post_id')}
        cursor.execute(util.query(**qry), (user_id, post_id))
        return True
        

class Ranking:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, **kwargs):
        t = self.thresholds(cursor)
        posts = {'select': 'COUNT(id) AS count',
                 'table': 'posts',
                 'where': 'user_id = ?'}
        cursor.execute(util.query(**posts), (user_id,))
        posts = cursor.fetchone().count
        following = {'select': 'COUNT(id) AS count',
                     'table': 'venue_followers',
                     'where': 'user_id = ?'}
        cursor.execute(util.query(**following), (user_id,))
        following = cursor.fetchone().count
        redemptions = {'select': 'COUNT(id) AS count',
                       'table': 'promotion_redemptions',
                       'where': 'user_id = ?'}
        cursor.execute(util.query(**redemptions), (user_id,))
        redemptions = cursor.fetchone().count
        share_venue = {'select': 'COUNT(id) AS count',
                       'table': 'venue_shares',
                       'where': 'user_id = ?'}
        cursor.execute(util.query(**share_venue), (user_id,))
        share_venue = cursor.fetchone().count
        share_posts = {'select': 'COUNT(id) AS count',
                       'table': 'post_shares',
                       'where': 'user_id = ?'}
        cursor.execute(util.query(**share_posts), (user_id,))
        share_posts = cursor.fetchone().count
        for threshold in t:
            if posts < threshold:
                res = 0
                break
        else:
            res = 3
        return {'thresholds': t,
                'level': res,
                'posts': posts,
                'following': following,
                'redemptions': redemptions,
                'share': share_posts + share_venue}
    
    def thresholds(self, cursor):
        users = {'select': 'COUNT(id) AS count', 'table': 'users'}
        cursor.execute(util.query(**users))
        users = cursor.fetchone().count
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
            thresholds.append(count.count if count else 0)
        return thresholds


class User:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, getall=None, **kwargs):
        return self.retrieve(cursor=cursor, user_id=user_id, getall=getall)
    
    def retrieve(self, cursor=None, user_id=None, getall=None):
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
            employee=None, country=None, language=None, email=None, top5=None,
            twitter_id=None, twitter_secret=None, save_locally=None, **kwargs):
        if not facebook_id:
            raise cherrypy.HTTPError(403)
        qry = {'select':   'COUNT(id) AS count',
               'table':    'users',
               'where':    'facebook_id = ?'}
        cursor.execute(util.query(**qry), (facebook_id,))
        res = cursor.fetchone().count
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
                'employee':       util.to_bool(employee),
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
        qry = {'select':   'id',
               'table':    'users',
               'where':    'facebook_id = ?',
               'order_by': 'id',
               'limit':    1}
        cursor.execute(util.query(**qry), (facebook_id,))
        user_id = cursor.fetchone().id
        return self.retrieve(cursor=cursor, user_id=user_id)


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


class Venue:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, term=None, following_only=None,
            my_lat=None, my_lon=None, distance=None, own=None, quiet=None,
            trending=None, from_time=None, until_time=None, **kwargs):
        subqry = {'select':   'COUNT(id)',
                  'table':    'venue_followers',
                  'where':    ('user_id = ' + str(user_id),
                               'venue_id = venues.id')}
        managerqry = {'select':   'COUNT(id)',
                      'table':    'venue_managers',
                      'where':    ('user_id = ' + str(user_id),
                                  'venue_id = venues.id')}
        staffqry =  {'select':   'COUNT(id)',
                     'table':    'venue_staff',
                     'where':    ('user_id = ' + str(user_id),
                                  'venue_id = venues.id')}
        fields = ['id', 'name', 'address', 'country', 'phone', 'email',
                  'email_verified', 'category_id', 'headline', 'tonight',
                  'website', 'facebook', 'twitter', 'facebook_id',
                  'twitter_id', 'twitter_token', 'twitter_secret', 'lat',
                  'lon', 'official', 'verified', 'customer_spend',
                  'authenticated', 'creator',
                  '(' + util.query(**managerqry) + ') AS manager',
                  '(' + util.query(**staffqry) + ') AS staff',
                  "(" + util.query(**subqry) + ") AS following"]
        order_by = 'name ASC'
        if term:
            where = ("name LIKE ?",)
        elif util.to_bool(following_only):
            where = ("(" + util.query(**subqry) + ") > 0")
        elif own:
            where = ('(' + util.query(**managerqry) + ') = 1 OR (' + util.query(**staffqry) + ') = 1')
        elif my_lat and my_lon and distance:
            maybe = {'select':   'COUNT(id)',
                     'table':    'venue_rsvps',
                     'where':    ('maybe = 1', 'venue_id = venues.id', 'going = 0')}
            going = {'select':   'COUNT(id)',
                     'table':    'venue_rsvps',
                     'where':    ('going = 1', 'venue_id = venues.id')}
            if util.to_bool(quiet):
                order_by = ('(' + util.query(**maybe) +') + (' + util.query(**going) +') * 2 ASC',)
            elif util.to_bool(trending):
                order_by = ('(' + util.query(**maybe) +') + (' + util.query(**going) +') * 2 DESC',)
            else:
                order_by = ('((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?)) ASC',)
            where = ('((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?)) <= ? * ?',)
            if util.to_bool(quiet) or util.to_bool(trending):
                fields[0] = 'TOP(12) id'
                where += ('time >= ?', 'time < ?',)
        else:
            where = ''
        qry = {'select':   fields,
               'table':    'venues',
               'where':    where,
               'order_by': order_by}
        if term:
            cursor.execute(util.query(**qry), ("%" + term + "%",))
            return [util.row_to_dict(cursor, row) for row in cursor]
        else:
            values = tuple()
            if my_lat and my_lon and distance:
                values += (float(my_lat), float(my_lat), float(my_lon),
                           float(my_lon), float(distance), float(distance))
                if util.to_bool(quiet) is None and util.to_bool(trending) is None:
                    values += (float(my_lat), float(my_lat), float(my_lon),
                               float(my_lon))
                else:
                    values += (from_time, until_time)
            cursor.execute(util.query(**qry), values)
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
            email_verified=None, category_id=None, headline=None, tonight=None,
            website=None, facebook=None, twitter=None, v_facebook_id=None,
            twitter_id=None, twitter_token=None, twitter_secret=None, lat=None,
            lon=None, official=None, verified=None, customer_spend=None,
            authenticated=None, **kwargs):
        data = {'name':           name,
                'address':        address,
                'country':        country,
                'phone':          phone,
                'email':          email,
                'email_verified': util.to_bool(email_verified),
                'category_id':    util.to_int(category_id),
                'headline':       headline,
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
                'official':       util.to_bool(official),
                'verified':       util.to_bool(verified),
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
        cursor.execute(util.query(last_id=True))
        return int(cursor.fetchone().identity)


class VenueCategory:
    
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
        

class VenueComment:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, venue_id=None, **kwargs):
        nameqry = {'select': ('CONCAT(forename, \' \', surname)',),
                   'table':  'users',
                   'where':  ('users.id = venue_comments.user_id',)}
        fbidqry = {'select': ('facebook_id',),
                   'table':  'users',
                   'where':  ('users.id = venue_comments.user_id',)}
        qry = {'select':   ('id', 'user_id', 'venue_id', 'time', 'comment',
                            '(' + util.query(**nameqry) + ') AS name',
                            '(' + util.query(**fbidqry) + ') AS facebook_id'),
               'table':    'venue_comments',
               'where':    ('venue_id = ?',),
               'order_by': 'time DESC'}
        cursor.execute(util.query(**qry), (venue_id,))
        return [util.row_to_dict(cursor, row) for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, comment=None,
            **kwargs):
        qry = {'insert_into': 'venue_comments',
               'columns':     ('user_id', 'venue_id', 'time', 'comment')}
        cursor.execute(util.query(**qry), (user_id, venue_id, util.now(),
                                           comment))
        return True
 

class VenueFollower:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, following=None,
            **kwargs):
        qry = {'select':   'id',
               'table':    'venue_followers',
               'where':    ('user_id = ?', 'venue_id = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, venue_id))
        res = cursor.fetchone()
        if util.to_bool(following) and not res:
            qry = {'insert_into': 'venue_followers',
                   'columns':      ('user_id', 'venue_id')}
            cursor.execute(util.query(**qry), (user_id, venue_id))
        elif not util.to_bool(following) and res:
            qry = {'delete': 'venue_followers',
                   'where': ('user_id = ?', 'venue_id = ?')}
            cursor.execute(util.query(**qry), (user_id, venue_id))
        return True


class VenueManager:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, **kwargs):
        qry = {'select':   'id',
               'table':    'venue_managers',
               'where':    ('user_id = ?', 'venue_id = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, venue_id))
        res = cursor.fetchone()
        if not res:
            qry = {'insert_into': 'venue_managers',
                   'columns':     ('user_id', 'venue_id', 'time')}
            cursor.execute(util.query(**qry), (user_id, venue_id, util.now()))
            qry = {'update':     'venues',
                   'set_values': ('official'),
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), (1, venue_id))
        return True


class VenueRsvp:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, venue_id=None, from_time=None, until_time=None,
            **kwargs):
        qry = {'select':   'COUNT(id) AS count',
               'table':    'venue_rsvps',
               'where':    ('venue_id = ?', 'maybe = 1', 'going = 0',
                            'time >= ?', 'time < ?')}
        cursor.execute(util.query(**qry), (venue_id, from_time, until_time))
        maybe = cursor.fetchone().count
        qry = {'select':   'COUNT(id) AS count',
               'table':    'venue_rsvps',
               'where':    ('venue_id = ?', 'going = 1',
                            'time >= ?', 'time < ?')}
        cursor.execute(util.query(**qry), (venue_id, from_time, until_time))
        going = cursor.fetchone().count
        return {'maybe': maybe, 'going': going}
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, maybe=None,
            going=None, from_time=None, until_time=None, **kwargs):
        qry = {'select':   'id',
               'table':    'venue_rsvps',
               'where':    ('user_id = ?', 'venue_id = ?',
                            'time >= ?', 'time < ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, venue_id, from_time,
                       until_time))
        res = cursor.fetchone()
        if res:
            values = []
            columns = []
            if maybe:
                values.append(util.to_bool(maybe))
                columns.append('maybe')
            if going:
                values.append(util.to_bool(going))
                columns.append('going')
            values.append(res.id)
            qry = {'update':     'venue_rsvps',
                   'set_values': columns,
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), values)
        else:
            values = [user_id, venue_id, util.now()]
            columns = ['user_id', 'venue_id', 'time']
            if maybe:
                values.append(util.to_bool(maybe))
                columns.append('maybe')
            if going:
                values.append(util.to_bool(going))
                columns.append('going')
            qry = {'insert_into': 'venue_rsvps',
                   'columns':     columns}
            cursor.execute(util.query(**qry), values)
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
        cursor.execute(util.query(**qry), (user_id, venue_id, media_id,
                                           util.now()))
        return True


class VenueStaff:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, venue_id=None, **kwargs):
        nameqry = {'select': ('CONCAT(forename, \' \', surname)',),
                   'table':  'users'}
        fbidqry = {'select': ('facebook_id',),
                   'table':  'users'}
        nameqry['where'] = ('users.id = venue_staff.user_id',)
        fbidqry['where'] = nameqry['where']
        qry = {'select':   ('id', 'user_id', 'promo_perm', 'time',
                            '(' + util.query(**nameqry) + ') AS name',
                            '(' + util.query(**fbidqry) + ') AS facebook_id'),
               'table':    'venue_staff',
               'where':    'venue_id = ?',
               'order_by': 'time DESC'}
        cursor.execute(util.query(**qry), (venue_id,))
        staff = [util.row_to_dict(cursor, row) for row in cursor]
        nameqry['where'] = ('users.id = venue_managers.user_id',)
        fbidqry['where'] = nameqry['where']
        qry = {'select':   ('id', 'user_id', 'time',
                            '(' + util.query(**nameqry) + ') AS name',
                            '(' + util.query(**fbidqry) + ') AS facebook_id'),
               'table':    'venue_managers',
               'where':    'venue_id = ?',
               'order_by': 'time DESC'}
        cursor.execute(util.query(**qry), (venue_id,))
        managers = [util.row_to_dict(cursor, row) for row in cursor]
        return {'staff': staff, 'managers': managers}
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, staff_user_id=None, venue_id=None,
            manager=None, **kwargs):
        qry = {'select':   'id',
               'table':    'venue_staff',
               'where':    ('user_id = ?', 'venue_id = ?'),
               'order_by': 'id',
               'limit':     1}
        cursor.execute(util.query(**qry), (user_id, venue_id))
        res = cursor.fetchone()
        if not res:
            qry = {'insert_into': 'venue_managers',
                   'columns':     ('user_id', 'venue_id', 'time')}
            cursor.execute(util.query(**qry), (user_id, venue_id, util.now()))
            qry = {'update':     'venues',
                   'set_values': ('official'),
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), (1, venue_id))
        return True
        

class VenueView:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, **kwargs):
        qry = {'insert_into': 'venue_views',
               'columns':     ('user_id', 'venue_id', 'time')}
        cursor.execute(util.query(**qry), (user_id, venue_id, util.now()))
        return True


class ShnergleServer:
    images = Image()
    posts = Post()
    post_likes = PostLike()
    post_reports = PostReport()
    post_shares = PostShare()
    post_views = PostView()
    rankings = Ranking()
    users = User()
    venues = Venue()
    venue_categories = VenueCategory()
    venue_comments = VenueComment()
    venue_followers = VenueFollower()
    venue_managers = VenueManager()
    venue_rsvps = VenueRsvp()
    venue_shares = VenueShare()
    venue_staff = VenueStaff()
    venue_views = VenueView()
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
