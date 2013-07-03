import calendar
import datetime
import functools
import json
import os
import time

import cherrypy
import pypyodbc


def connect(thread_index):
    cherrypy.thread_data.db = pypyodbc.connect(os.environ['DATABASE'])


def dont_cache():
    cherrypy.response.headers['Expires'] = datetime.datetime.utcnow().strftime(
        '%a, %d %b %Y %H:%M:%S GMT')
    cherrypy.response.headers['Cache-Control'] = ('no-store, '
                                                  'no-cache, '
                                                  'must-revalidate, '
                                                  'post-check=0, '
                                                  'pre-check=0')


def protect(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if kwargs.pop('app_secret', False) != os.environ['APP_SECRET']:
            raise cherrypy.HTTPError(403)
        return func(*args, **kwargs)
    return decorator


def auth(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if not kwargs.get('facebook_id', False):
            raise cherrypy.HTTPError(403)
        cursor = kwargs['cursor']
        qry = {'select':   'id',
               'table':    'users',
               'where':    'facebook_id = ?',
               'order_by': 'id',
               'limit':    1}
        cursor.execute(query(**qry), (kwargs['facebook_id'],))
        res = cursor.fetchone()['id']
        if not res:
            raise cherrypy.HTTPError(403)
        kwargs.update(user_id=res)
        return func(*args, **kwargs)
    return decorator


def jsonp(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        dont_cache()
        res = json.dumps(func(*args, **kwargs), separators=(',', ':'),
                         default=lambda o: str(o))
        callback = kwargs.pop('callback', False)
        if callback:
            cherrypy.response.headers['Content-Type'] = ('text/javascript; '
                                                         'charset=utf-8')
            res = callback + '(' + res + ');'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/json'
        return res
    return decorator


def db(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        cursor = cherrypy.thread_data.db.cursor()
        kwargs.update(cursor=cursor)
        try:
            res = func(*args, **kwargs)
        finally:
            cursor.commit()
            cursor.close()
        return res
    return decorator


def implode(glue, list):
    return list if isinstance(list, str) else glue.join(list)


def query(select=None, table=None, left_join=None, on=None, where=None,
          group_by=None, order_by=None, limit=None,
          insert_into=None, columns=None,
          update=None, set_values=None,
          last_id=False):
    if select:
        qry = 'SELECT ' + implode(', ', select)
        if table:
            qry += ' FROM ' + implode(', ', table)
        if left_join and on:
            if isinstance(left_join, str):
                left_join = [left_join]
            if isinstance(on, str):
                on = [on]
            for j, o in zip(left_join, on):
                qry += ' LEFT JOIN ' + j + ' ON ' + o
        if where:
            qry += ' WHERE ' + implode(' AND ', where)
        if group_by:
            qry += ' GROUP BY ' + implode(', ', group_by)
        if order_by:
            qry += ' ORDER BY ' + implode(', ', order_by)
        if limit:
            if isinstance(limit, str) or isinstance(limit, int):
                qry += ' OFFSET 0 ROWS FETCH NEXT ' + str(limit) + ' ROWS ONLY'
            else:
                qry += (' OFFSET ' + str(int(limit[0])) + ' ROWS FETCH NEXT ' +
                        str(int(limit[1])) + ' ROWS ONLY')
    elif insert_into:
        qry = 'INSERT INTO ' + insert_into
        if columns:
            qry += (' (' + implode(', ', columns) + ')' + ' VALUES (' +
                    ('?' + ', ?' * (len(columns) - 1)) + ')')
    elif update:
        qry = 'UPDATE ' + update
        if set_values:
            qry += ' SET ' + implode(' = ?, ', set_values) + ' = ?'
        if where:
            qry += ' WHERE ' + implode(' AND ', where)
    elif last_id:
        qry = 'SELECT SCOPE_IDENTITY() AS [identity]'
    return qry


expose = cherrypy.expose


def to_int(value):
    return int(value) if value else None


def to_bool(value):
    if value is None:
        return None
    if not value:
        return False
    if isinstance(value, str) and value in ('none', 'false', 'no', 'off', '0'):
        return False
    return True
    
    
def to_float(value):
    return float(value) if value else None


def row_to_dict(cursor, row):
    return {t[0]: val for t, val in zip(cursor.description, row)}


def now():
    return calendar.timegm(datetime.datetime.utcnow().utctimetuple())
