ShnergleServer
==============

This is the server used for communication with consumer and merchant app for Shnergle, taking care of data storage.

Requirements
------------

 * Python 2
 * CherryPy (included)


Structure
---------
 
 * URL Structure is /class/operation
   * class corresponds to an actual class and should also correspond to a database collection
   * operation is one of add, get or set, corresponding to the CRUD operations (no delete) and a method
 * WSGI is used as interface to a proper web server
 * Parameters can be given as GET and/or POST, POST parameters take precedence