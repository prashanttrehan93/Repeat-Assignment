from google.appengine.ext import ndb
from user import User

class Folder(ndb.Model):
	owner = ndb.KeyProperty(kind=User)
	path = ndb.StringProperty()
	cdate = ndb.StringProperty()
	fsize = ndb.IntegerProperty()
	fnumber = ndb.IntegerProperty()
	dnumber = ndb.IntegerProperty()
