#!/usr/bin/env python

import json
import time

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ForkingMixIn
from datetime import datetime

from pymongo import MongoClient
from gridfs import GridFS

db = MongoClient('127.0.0.1', 27017).test
mongo = db.times
grid = GridFS(db)

class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
    start = time.time()
    if 'err' in self.path or 'obots' in self.path or 'favicon' in self.path:
      self.send_error(404)
      return
    elif 'priv' in self.path:
      self.send_error(403)
      return
    elif 'drop' in self.path:
      mongo.remove()
      self.send_error(200)
      return
    self.send_response(200)
    self.send_header('Expires', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
    path = self.path.split('?', 1) if '?' in self.path else [self.path, None]
    res = {}
    res['json'] = 'JSON'
    res['path'] = path[0].split('/')
    res['path'].pop(0)
    res['query'] = {e.split('=')[0]: e.split('=')[1] if '=' in e else None for e in path[1].split('&')} if path[1] != None else None
    callback = res['query']['callback'] + '(' if res['query'] and 'callback' in res['query'] and res['query']['callback'] else ''
    if callback:
      self.send_header('Content-type', 'application/javascript')
      del res['query']['callback']
    else:
      self.send_header('Content-type', 'application/json')
    self.end_headers()
    res['supports'] = ['python3', 'freeze', 'json', 'jsonp', 'mime', 'mongodb', 'gridfs', '(gzip)', 'speed', 'scaling', 'drop database', 'errors', {'parsing': ['path', 'query'], 'forking': 'used', 'threading': 'blocking', 'methods': ['get', 'post']}]
    avg = 0
    count = mongo.count()
    if count != 0:
      for doc in mongo.find():
        avg += doc['time']
      avg /= count
    res['generated'] = {}
    res['generated']['average'] = avg
    res['generated']['current'] = time.time() - start
    mongo.insert({'time': res['generated']['current']})
    self.wfile.write(bytes(callback + json.dumps(res) + (');' if callback else ''), 'utf-8'))
  def do_POST(self):
    self.do_GET()
  def log_message(self, format, *args):
    open('messages.log', 'a').write("%s - - [%s] %s\n" %
                                    (self.address_string(),
                                     self.log_date_time_string(),
                                     format%args))

class ThreadedHTTPServer(ForkingMixIn, HTTPServer):
  True

if __name__ == '__main__':
  import sys
  import signal
  def quit(signal, frame):
    sys.exit(0)
  signal.signal(signal.SIGINT, quit)
  ThreadedHTTPServer(('localhost', 8080), Handler).serve_forever()
