import hashlib
import json
import math
import os

import cherrypy

import azureutil
import util


class Confirm:
    
    @util.expose
    @util.db
    def index(self, cursor=None, venue_id=None, user_id=None, hashd=None,
              **kwargs):
        if not venue_id or not user_id or not hashd:
            return 'Error!'
        qry = {'select':   ('name', 'email', 'phone', 'website'),
               'table':    'venues',
               'where':    ('id = ?')}
        cursor.execute(util.query(**qry), (venue_id,))
        venue = cursor.fetchone()
        if not venue:
            return 'Error!'
        qry = {'select':   ('forename', 'surname'),
               'table':    'users',
               'where':    ('id = ?')}
        cursor.execute(util.query(**qry), (user_id,))
        user = cursor.fetchone()
        if not user:
            return 'Error!'
        if hashd != hashlib.md5(venue.email + '|' + str(venue_id) + '|' + str(user_id) + '|confirm|' + os.environ['APP_SECRET']).hexdigest():
            return 'Error!'
        qry = {'update':     'venues',
               'set_values': ('email_verified'),
               'where':      'id = ?'}
        cursor.execute(util.query(**qry), (1, venue_id))
        with open(os.path.dirname(os.path.abspath(__file__)) + 'email_confirmed.txt', 'rb') as f:
                msg = f.read()
                msg.replace('[EmailAddress]', venue.email)
                msg.replace('[PhoneNumber]', venue.phone)
                msg.replace('[Website]', venue.website)
                msg.replace('[Name]', user.forename + ' ' + user.surname)
                msg.replace('[VenueName]', venue.name)
                msg.replace('[Link]', 'http://shnergle-api.azurewebsites.net/confirm/' + str(venue_id) + '/' + hashlib.md5(venue.email + '|' + str(venue_id) + '|confirm|' + os.environ['APP_SECRET']).hexdigest())
                subject = 'Thanks for verifying [EmailAddress], we will now complete the verification of [VenueName]'
                subject.replace('[EmailAddress]', venue.email)
                subject.replace('[VenueName]', venue.name)
                msg = MIMEText(msg)
        msg['Subject'] = subject
        msg['From'] = os.environ['EMAIL']
        msg['To'] = venue.email
        s = smtplib.SMTP(os.environ['SMTP_SERVER'])
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()
        return 'Confirmed.'
        
        
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
            hide=None, post_id=None, image=None, **kwargs):
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
            post_added = int(cursor.fetchone().identity)
            return azureutil.store(image.file, 'post', str(post_added))


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
                   'columns':     ('user_id', 'post_id', 'time')}
            cursor.execute(util.query(**qry), (user_id, post_id, util.now()))
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
               'columns':     ('user_id', 'post_id', 'media_id', 'time')}
        cursor.execute(util.query(**qry), (user_id, post_id, media_id,
                                           util.now()))
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
     
     
class Promotion:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, venue_id=None, getall=None, level=None,
            **kwargs):
        red = {'select': 'COUNT(id)',
               'table':  'promotion_redemptions',
               'where':  'promotion_id = promotions.id'}
        promo_qry = {'select':   ('id', 'title', 'description',
                                  'passcode', 'start', '[end]', 'maximum',
                                  'creator', 'level',
                                  '(' + util.query(**red) + ') AS redemptions'),
                     'table':    'promotions',
                     'where':    ['venue_id = ?', 'hidden != 1'],
                     'order_by': 'id DESC'}
        if not util.to_bool(getall):
            promo_qry['limit'] = 1
            promo_qry['where'].append(str(util.now()) + ' >= start')
            promo_qry['where'].append('([end] = 0 OR [end] > ' + str(util.now()) + ')')
            promo_qry['where'].append('(' + util.query(**red) + ') <= maximum')
            promo_qry['where'].append(level + ' >= level')
            promo_qry['order_by'] = 'level DESC, id DESC'
            cursor.execute(util.query(**promo_qry), (venue_id,))
            return util.row_to_dict(cursor, cursor.fetchone())
        cursor.execute(util.query(**promo_qry), (venue_id,))
        return [util.row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, venue_id=None, delete=None,
            promotion_id=None, title=None, description=None, start=None,
            end=None, maximum=None, passcode=None, level=None, **kwargs):
        if util.to_bool(delete) and promotion_id:
            qry = {'update':     'promotions',
                   'set_values': ('hidden'),
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), (1, promotion_id))
        elif promotion_id:
            qry = {'update':     'promotions',
                   'set_values': ('title', 'description', 'start', '[end]',
                                  'maximum', 'passcode', 'venue_id', 'level'),
                   'where':      'id = ?'}
            cursor.execute(util.query(**qry), (title, description, start, end,
                                               maximum, passcode, venue_id,
                                               level, promotion_id))
        else:
            qry = {'insert_into': 'promotions',
                   'columns':      ('title', 'description', 'start', '[end]',
                                    'maximum', 'creator', 'passcode',
                                    'venue_id', 'level')}
            cursor.execute(util.query(**qry), (title, description, start, end,
                                               maximum, user_id, passcode,
                                               venue_id, level))
        return True
        
        
class PromotionRedemption:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, **kwargs):
        qry = {'select':   ('venues.name', 'promotion_redemptions.time',
                            'promotions.passcode', 'promotions.description'),
               'left_join': ('promotions', 'venues'),
               'on':        ('promotion_redemptions.promotion_id = promotions.id', 'venues.id = promotions.venue_id'),
               'table':     'promotion_redemptions',
               'where':     ('promotion_redemptions.user_id = ?'),
               'order_by':  'time DESC'}
        cursor.execute(util.query(**qry), (user_id,))
        return [util.row_to_dict(cursor, row) for row in cursor]
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def set(self, cursor=None, user_id=None, promotion_id=None, **kwargs):
        cnt = {'select':   ('COUNT(id)'),
               'table':     'promotion_redemptions',
               'where':     ('promotion_id = promotions.id')}
        promo = {'select':   ('[end]', 'maximum', 'passcode',
                              '(' + util.query(**cnt) + ') AS count'),
                 'table':     'promotions',
                 'where':     ('id = ?')}
        cursor.execute(util.query(**promo), (promotion_id,))
        row = cursor.fetchone()
        if int(row.end) != 0 and int(row.end) < util.now():
            return 'time'
        if int(row.maximum) != 0 and int(row.count) >= int(row.maximum):
            return 'number'
        qry = {'insert_into': 'promotion_redemptions',
               'columns':     ('user_id', 'promotion_id', 'time')}
        cursor.execute(util.query(**qry), (user_id, promotion_id, util.now()))
        return row.passcode


class Ranking:
    
    @util.expose
    @util.protect
    @util.db
    @util.auth
    @util.jsonp
    def get(self, cursor=None, user_id=None, **kwargs):
        t = self.thresholds(cursor)
        posts_total = {'select': 'COUNT(id) AS count',
                       'table': 'posts',
                       'where': 'user_id = ?'}
        cursor.execute(util.query(**posts_total), (user_id,))
        posts_total = cursor.fetchone().count
        following_total = {'select': 'COUNT(id) AS count',
                           'table': 'venue_followers',
                           'where': 'user_id = ?'}
        cursor.execute(util.query(**following_total), (user_id,))
        following_total = cursor.fetchone().count
        redemptions_total = {'select': 'COUNT(id) AS count',
                             'table': 'promotion_redemptions',
                             'where': 'user_id = ?'}
        cursor.execute(util.query(**redemptions_total), (user_id,))
        redemptions_total = cursor.fetchone().count
        posts = {'select': 'COUNT(id) AS count',
                 'table': 'posts',
                 'where': ('user_id = ?', 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**posts), (user_id,))
        posts = cursor.fetchone().count
        rsvps = {'select': 'COUNT(id) AS count',
                 'table': 'venue_rsvps',
                 'where': ('user_id = ?', 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**rsvps), (user_id,))
        rsvps = cursor.fetchone().count
        comments = {'select': 'COUNT(id) AS count',
                    'table': 'venue_comments',
                    'where': ('user_id = ?',
                              'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**comments), (user_id,))
        comments = cursor.fetchone().count
        likes = {'select': 'COUNT(id) AS count',
                 'table': 'post_likes',
                 'where': ('user_id = ?', 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**likes), (user_id,))
        likes = cursor.fetchone().count
        redemptions = {'select': 'COUNT(id) AS count',
                       'table': 'promotion_redemptions',
                       'where': ('user_id = ?',
                                 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**redemptions), (user_id,))
        redemptions = cursor.fetchone().count
        share_venue = {'select': 'COUNT(id) AS count',
                       'table': 'venue_shares',
                       'where': ('user_id = ?',
                                 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**share_venue), (user_id,))
        share_venue = cursor.fetchone().count
        share_posts = {'select': 'COUNT(id) AS count',
                       'table': 'post_shares',
                       'where': ('user_id = ?',
                                 'time >' + str(util.now() - 2592000))}
        cursor.execute(util.query(**share_posts), (user_id,))
        share_posts = cursor.fetchone().count
        score = ((share_posts + share_venue) * 5 + posts * 4 + rsvps * 3 + comments * 2 + likes)
        for threshold in t:
            if score < threshold:
                res = 0
                break
        else:
            res = 3
        return {'thresholds': t,
                'level': res,
                'posts_total': posts_total,
                'following_total': following_total,
                'redemptions_total': redemptions_total,
                'posts': posts,
                'redemptions': redemptions,
                'share': share_posts + share_venue,
                'rsvps': rsvps,
                'comments': comments,
                'likes': likes,
                'score': score}
    
    def thresholds(self, cursor):
        users = {'select': 'COUNT(id) AS count', 'table': 'users'}
        cursor.execute(util.query(**users))
        users = cursor.fetchone().count
        thresholds = []
        for percent in (0.8, 0.95, 0.99):
            number = math.floor(percent * users)
            rsvps = {'select': 'COUNT(id)',
                     'table': 'venue_rsvps',
                     'where': ('user_id = users.id',
                               'time > ' + str(util.now() - 2592000))}
            venue_shares = {'select': 'COUNT(id)',
                            'table': 'venue_shares',
                            'where': ('user_id = users.id',
                                      'time > ' + str(util.now() - 2592000))}
            post_shares = {'select': 'COUNT(id)',
                           'table': 'post_shares',
                           'where': ('user_id = users.id',
                                     'time > ' + str(util.now() - 2592000))}
            comments = {'select': 'COUNT(id)',
                        'table': 'venue_comments',
                        'where': ('user_id = users.id',
                                  'time > ' + str(util.now() - 2592000))}
            likes = {'select': 'COUNT(id)',
                     'table': 'post_likes',
                     'where': ('user_id = users.id',
                               'time > ' + str(util.now() - 2592000))}
            posts = {'select': 'COUNT(id)',
                     'table': 'posts',
                     'where': ('user_id = users.id',
                               'time > ' + str(util.now() - 2592000))}
            thresholdqry = {'select':    ('((' + util.query(**venue_shares) + ') * 5 + ' +
            '(' + util.query(**post_shares) + ') * 5 + ' +
            '(' + util.query(**posts) + ') * 4 + ' +
            '(' + util.query(**rsvps) + ') * 3 + ' +
            '(' + util.query(**comments) + ') * 2 + ' +
            '(' + util.query(**likes) + ')) AS count',),
                            'table':     'users',
                            'group_by':  'id',
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
    def get(self, cursor=None, user_id=None, term=None, **kwargs):
        return self.retrieve(cursor=cursor, user_id=user_id, term=term)
    
    def retrieve(self, cursor=None, user_id=None, term=None):
        if util.to_bool(term):
            qry = {'select':    ['id',
                                 'facebook_id',
                                 'forename',
                                 'surname'
                                 ],
                   'table':     'users',
                   'where':     ("CONCAT(forename, \' \', surname) LIKE ?",),
                   'order_by':  'surname ASC, forename ASC'}
            cursor.execute(util.query(**qry), ("%" + term.replace(' ', "%") + "%",))
            return [util.row_to_dict(cursor, row) for row in cursor]
        else:
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
            qry = {'update':     'user_searches',
                   'set_values': ('time'),
                   'where':      'user_id = ?'}
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
            trending=None, from_time=None, until_time=None, promotions=None,
            level=None, **kwargs):
        subqry = {'select':   'COUNT(id)',
                  'table':    'venue_followers',
                  'where':    ('user_id = ' + str(user_id),
                               'venue_id = venues.id')}
        red = {'select': 'COUNT(id)',
               'table':  'promotion_redemptions',
               'where':  'promotion_id = promotions.id'}
        promoqry = {'select':   'COUNT(id)',
                    'table':    'promotions',
                    'where':    ('venue_id = venues.id',
                                 str(util.now()) + ' >= start',
                                 '([end] = 0 OR [end] > ' + str(util.now()) + ')',
                                 '(' + util.query(**red) + ') <= maximum',
                                 level + ' >= level',
                                 'hidden != 1')}
        managerqry = {'select':   'COUNT(id)',
                      'table':    'venue_managers',
                      'where':    ('user_id = ' + str(user_id),
                                  'venue_id = venues.id')}
        staffqry =  {'select':   'COUNT(id)',
                     'table':    'venue_staff',
                     'where':    ('user_id = ' + str(user_id),
                                  'venue_id = venues.id')}
        staffppqry =  {'select':   'SUM(promo_perm)',
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
                  '(' + util.query(**staffppqry) + ') AS promo_perm',
                  "(" + util.query(**subqry) + ") AS following",
                  '(' + util.query(**promoqry) + ') AS promotions']
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
                     'where':    ('maybe = 1', 'venue_id = venues.id',
                                  'going = 0', 'time >= ?', 'time < ?')}
            going = {'select':   'COUNT(id)',
                     'table':    'venue_rsvps',
                     'where':    ('going = 1', 'venue_id = venues.id',
                                  'time >= ?', 'time < ?')}
            if util.to_bool(quiet):
                order_by = ('(' + util.query(**maybe) +') + (' + util.query(**going) +') * 2 ASC',)
            elif util.to_bool(trending):
                order_by = ('(' + util.query(**maybe) +') + (' + util.query(**going) +') * 2 DESC',)
            else:
                order_by = ('((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?)) ASC',)
            where = ('((lat - ?) * (lat - ?) + (lon - ?) * (lon - ?)) <= ? * ?',)
            if util.to_bool(promotions):
                where += ('(' + util.query(**promoqry) + ') > 0',)
            if util.to_bool(quiet) or util.to_bool(trending):
                fields[0] = 'TOP(12) id'
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
                    values += (from_time, until_time, from_time, until_time)
            cursor.execute(util.query(**qry), values)
            return [util.row_to_dict(cursor, row) for row in cursor]
    
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
        nameqry = {'select': ('CONCAT(forename, \' \', SUBSTRING(surname, 1, 1))',),
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
               'order_by': 'time DESC',
               'limit':    10}
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
            qry = {'select':   ('name', 'email'),
                   'table':    'venues',
                   'where':    ('id = ?')}
            cursor.execute(util.query(**qry), (venue_id,))
            venue = cursor.fetchone()
            qry = {'select':   ('forename', 'surname'),
                   'table':    'users',
                   'where':    ('id = ?')}
            cursor.execute(util.query(**qry), (user_id,))
            user = cursor.fetchone()
            with open(os.path.dirname(os.path.abspath(__file__)) + 'email_confirm.txt', 'rb') as f:
                msg = f.read()
                msg.replace('[Name]', user.forename + ' ' + user.surname)
                msg.replace('[VenueName]', venue.name)
                msg.replace('[Link]', 'http://shnergle-api.azurewebsites.net/confirm/?venue_id=' + str(venue_id) + '&user_id=' + str(user_id) + '&hashd=' + hashlib.md5(venue.email + '|' + str(venue_id) + '|' + str(user_id) + '|confirm|' + os.environ['APP_SECRET']).hexdigest())
                subject = 'Verify Email Address ownership for [VenueName] on Shnergle'
                subject.replace('[VenueName]', venue.name)
                msg = MIMEText(msg)
            msg['Subject'] = subject
            msg['From'] = os.environ['EMAIL']
            msg['To'] = venue.email
            s = smtplib.SMTP(os.environ['SMTP_SERVER'])
            s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
            s.sendmail(msg['From'], [msg['To']], msg.as_string())
            s.quit()
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
    def set(self, cursor=None, user_id=None, staff_user_id=None, venue_id=None,
            manager=None, promo_perm=None, delete=None, **kwargs):
        if util.to_bool(delete):
            qry = {'delete':   'venue_staff',
                   'where':    ('user_id = ?', 'venue_id = ?')}
            cursor.execute(util.query(**qry), (staff_user_id, venue_id))
            qry = {'delete':   'venue_managers',
                   'where':    ('user_id = ?', 'venue_id = ?')}
            cursor.execute(util.query(**qry), (staff_user_id, venue_id))
        elif util.to_bool(manager):
            qry = {'select':   'id',
                   'table':    'venue_managers',
                   'where':    ('user_id = ?', 'venue_id = ?'),
                   'order_by': 'id',
                   'limit':     1}
            cursor.execute(util.query(**qry), (staff_user_id, venue_id))
            res = cursor.fetchone()
            if not res:
                qry = {'delete':   'venue_staff',
                       'where':    ('user_id = ?', 'venue_id = ?')}
                cursor.execute(util.query(**qry), (staff_user_id, venue_id))
                qry = {'insert_into': 'venue_managers',
                       'columns':     ('user_id', 'venue_id', 'time')}
                cursor.execute(util.query(**qry), (staff_user_id, venue_id,
                                                   util.now()))
        else:
            qry = {'select':   'id',
                   'table':    'venue_staff',
                   'where':    ('user_id = ?', 'venue_id = ?'),
                   'order_by': 'id',
                   'limit':     1}
            cursor.execute(util.query(**qry), (staff_user_id, venue_id))
            res = cursor.fetchone()
            if not res:
                qry = {'delete':   'venue_managers',
                       'where':    ('user_id = ?', 'venue_id = ?')}
                cursor.execute(util.query(**qry), (staff_user_id, venue_id))
                qry = {'insert_into': 'venue_staff',
                       'columns':     ('user_id', 'venue_id', 'time',
                                       'promo_perm')}
                cursor.execute(util.query(**qry), (staff_user_id, venue_id,
                                                   util.now(),
                                                   1 if util.to_bool(promo_perm) else 0))
            else:
                qry = {'update':     'venue_staff',
                       'set_values': ('promo_perm'),
                       'where':      ('user_id = ?', 'venue_id = ?')}
                cursor.execute(util.query(**qry), (1 if util.to_bool(promo_perm) else 0,
                                                   staff_user_id, venue_id))
        return True
    
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
    confirm = Confirm()
    images = Image()
    posts = Post()
    post_likes = PostLike()
    post_reports = PostReport()
    post_shares = PostShare()
    post_views = PostView()
    promotions = Promotion()
    promotion_redemptions = PromotionRedemption()
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
        
    @util.expose
    def index(self):
        return ''
    
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
