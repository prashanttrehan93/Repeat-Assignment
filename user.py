from google.appengine.ext import ndb

class User(ndb.Model):
	first_name = ndb.StringProperty()
	last_name = ndb.StringProperty()
	email = ndb.StringProperty()
	password = ndb.StringProperty()
