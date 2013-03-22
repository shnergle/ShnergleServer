ShnergleServer
==============

This is the server used for communication with consumer and merchant app for Shnergle, taking care of data storage.

Requirements
------------

 * Python 2
 * CherryPy (included)
 * Google App Engine


Structure
---------
 
 * URL Structure is /class/operation
   * class corresponds to an actual class and should also correspond to a database collection
   * operation is one of add, get or set, corresponding to the CRUD operations (no delete) and a method
   * the index operation (/class/) will display an index where applicable
 * WSGI is used as interface to a proper web server
 * Parameters can be given as GET and/or POST, POST parameters take precedence
 * Output is in JSON or JSONP
 * All delivered JSON documents should be as close as possible to representation in database
 * It is not a RESTful server, yet can be used as such
