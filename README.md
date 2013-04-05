ShnergleServer
==============

This is the server used for communication with consumer and merchant app for Shnergle, taking care of data storage.

Requirements
------------

 * Python 2.7 or higher
 * CherryPy (3.2.2 included) [fixed wrong import]
 * Requests (1.1.0 included) [made certs import in utils relative, and git fixes]

Where the library is included, the server has not been tested with any other version!


Setup
-----

Just copy config.json.dist to config.json and edit the settings.
app.yaml and index.yaml are configure for Google App Engine and not needed for any other hosting provider.
If not using Google App Engine, optionally add a static route for favicon.ico and make the WSGI server use the public app variable in server.py/


Structure
---------
 
 * URL Structure is /version/class/operation
   * version is in the moment always v1, can but should not be ommited
   * class corresponds to an actual class and should also correspond to a database collection
   * operation is either get or set
     * get returns the data
     * set updates data if _id is specified, otherwise creates a new entry
	 * _id is the parameter to identify entries
   * the index operation (/class/) will display an index where applicable
 * WSGI is used as interface to a proper web server
 * Parameters can be given as GET and/or POST, POST parameters take precedence
 * Output is in JSON or JSONP
 * All delivered JSON documents should be as close as possible to representation in database
 * It is not a RESTful server, yet can be used as such
 * No dependency on hosting provider, thus can be tested by calling the main script (default port is 8080, can be changed by passing an argument)
 * The server module has a public app attribute for use with WSGI compliant servers
