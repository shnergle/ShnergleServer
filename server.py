from __future__ import unicode_literals
import controller

import cherrypy
import json

# MySQL Test
def decode(data):
    ret = {}
    for key, val in data.iteritems():
        ret[str(key)] = str(val)
    return ret

import mysql.connector
with open('config.json') as config:
    cnx = mysql.connector.connect(**decode(json.load(config)))
cnx.close()


def error(status, message, traceback, version):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message},
                      separators=(',', ':'))


config = {'/': {'error_page.default': error}}
app = cherrypy.Application(controller.ShnergleServer(), '/', config)
