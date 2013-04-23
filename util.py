import json
import functools
from datetime import datetime

import cherrypy
import mysql.connector

from config import config


def dont_cache():
    cherrypy.response.headers['Expires'] = datetime.utcnow().strftime(
        '%a, %d %b %Y %H:%M:%S GMT')
    cherrypy.response.headers['Cache-Control'] = ('no-store, '
                                                  'no-cache, '
                                                  'must-revalidate, '
                                                  'post-check=0, '
                                                  'pre-check=0')


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


class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):

    def _row_to_python(self, rowdata, desc=None):
        row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
        if row:
            return dict(zip(self.column_names, row))
        return None


class MySQLConverterJSON(mysql.connector.conversion.MySQLConverter):
    _DATETIME_to_python =  mysql.connector.conversion.MySQLConverter._str
    _TIMESTAMP_to_python = _DATETIME_to_python


def mysqli(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        cnx = mysql.connector.connect(**config)
        cnx.set_converter_class(MySQLConverterJSON)
        cursor = cnx.cursor(cursor_class=MySQLCursorDict)
        args += (cursor,)
        try:
            res = func(*args, **kwargs)
        finally:
            cnx.commit()
            cursor.close()
            cnx.close()
        return res
    return decorator


def implode(glue, list):
    return list if isinstance(list, str) else glue.join(list)


def query(select=None, table=None, left_join=None, on=None, where=None,
          limit=None,
          insert_into=None, columns=None,
          update=None, set_values=None):
    if select:
        qry = 'SELECT ' + implode(', ', select)
        if table:
            qry += ' FROM ' + implode(', ', table)
        if left_join:
            qry += ' LEFT JOIN (' + implode(', ', left_join) + ')'
        if on:
            qry += ' ON (' + implode(' AND ', on) + ')'
        if where:
            qry += ' WHERE ' + implode(' AND ', where)
        if limit:
            qry += ' LIMIT ' + str(limit)
    elif insert_into:
        qry = 'INSERT INTO ' + insert_into
        if columns:
            qry += (' (' + implode(', ', columns) + ')' + ' VALUES (' +
                    ('%s' + ', %s' * (len(columns) - 1)) + ')')
    elif update:
        qry = 'UPDATE ' + update
        if set_values:
            qry += ' SET ' + implode('=%s, ', set_values) + '=%s'
        if where:
            qry += ' WHERE ' + implode(' AND ', where)
    return qry


expose = cherrypy.expose
