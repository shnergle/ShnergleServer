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
        if not kwargs.get('facebook_token', False):
            raise cherrypy.HTTPError(403)
        cursor = kwargs['cursor']
        qry = {'select':   'id',
               'table':    'users',
               'where':    'facebook_token = ?',
               'order_by': 'id',
               'limit':    1}
        cursor.execute(query(**qry), (kwargs['facebook_token'],))
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
        res = json.dumps(func(*args, **kwargs), separators=(',', ':'))
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
            cnx.commit()
            cursor.close()
        return res
    return decorator


def implode(glue, list):
    return list if isinstance(list, str) else glue.join(list)


def query(select=None, table=None, left_join=None, on=None, where=None,
          group_by=None, order_by=None, limit=None,
          insert_into=None, columns=None,
          update=None, set_values=None):
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
            qry += ' SET ' + implode('=?, ', set_values) + '=?'
        if where:
            qry += ' WHERE ' + implode(' AND ', where)
    return qry


expose = cherrypy.expose


def to_int(value):
    return int(value) if value else None

def to_bool(value):
    if value in (0, False, None, '0'): return False
    if isinstance(value, str) and value in ('false', 'no', 'off'): return False
    return True