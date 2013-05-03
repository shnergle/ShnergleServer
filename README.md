ShnergleServer
==============

This is the server used for communication with consumer and merchant app for Shnergle, taking care of data storage and aggregation.

Requirements
------------

 * Python 2.7, 3.0 or higher
 * CherryPy (3.2.4 included)
 * pypyodbc (1.1.2 included)

Where the library is included, the server has not been tested with any other version!


Setup
-----

Point the WSGI server to server.app and set the environment variable APP_SECRET to a random string and DATABASE to the connection string.


Structure
---------
 
 * URL Structure is /version/class/operation
   * version is in the moment always v1, can but should not be ommited
   * class corresponds to an actual class and should also correspond to a database collection
   * operation is either get or set
     * get returns the data
     * set updates data if id is specified, otherwise creates a new entry
	 * id is the parameter to identify entries
   * the index operation (/class/) will display an index where applicable
 * WSGI is used as interface to a proper web server
 * Parameters can be given as GET and/or POST, POST parameters take precedence
 * Output is in JSON or JSONP
 * All delivered JSON documents should be as close as possible to representation in database
 * No dependency on hosting provider
 * The server module has a public attribute app for use with WSGI compliant servers
