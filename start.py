import webapp2
from webapp2_extras import sessions
import os
import time
from datetime import datetime
from google.appengine.ext.webapp import template
from google.appengine.api import app_identity
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb
from user import User
from folder import Folder
from file import File
import logging

# The base class for managing session variable and request. Almost of classes inherite this base class.
class BaseHandler(blobstore_handlers.BlobstoreUploadHandler, webapp2.RequestHandler):
    def dispatch(self):                                 # override dispatch
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)       # dispatch the main handler
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

# The class for showing main page.
class MainHandler(BaseHandler):
    def get(self):
        # Get user's root
        root = self.session.get('root')

        # If you did not login, redirect to login page
        if str(root) == 'None':
            self.redirect('signin')
            return

        # Get parameter path
        path = self.request.get('path')

        if (path == ''):
            fullpath =  root
        else:
            fullpath =  root + '/' + path

        # Show folders related with user
        self.response.write(root)
        # return
        user_folders = displayUserFolders(root)

        # Show folders
        folders = displayFolders(fullpath, root)

        # Show files
        files = diplayFiles(fullpath, root)

        # Show users
        users = showUsers(root)

        # Breadcrumb
        breadcrumb = []
        if path != '':
            parts = path.split('/')
            for i in range(len(parts)):
                route = ''
                for j in range(i):
                    route += '/' + parts[j]

                route = route[1:]
                if (route == ''):
                    route += parts[i]
                else:
                    route += '/' + parts[i]

                name = parts[i]

                breadcrumb.append({'route': route, 'name': name})

        # Find error messages
        errormessage = self.request.get('err')

        # Show home template with parameters
        templateValues = {
            'breadcrumb': breadcrumb,
            'userfolderitems': user_folders,
            'folderitems': folders,
            'fileitems' : files,
            'useritems' : users,
            'path': path,
            'errormessage': errormessage
        }
        # Redirect to home page
        path = os.path.join(os.path.dirname(__file__), "views/index.html")
        self.response.write(template.render(path, templateValues))

    def post(self):
        # Getting variables for creating new folder
        folder = self.request.POST.get('foldername')
        path = self.request.POST.get('path')

        # Getting value of session variable for user root
        root = self.session.get('root')

        if (path == ''):     # If in root
            full_path = root + '/' + folder
        else:
            full_path = root + '/' + path + '/' + folder

        # If folder with same name is already created, redirect to home with error message.
        if checkDuplicatedFolder(full_path):
            self.redirect('/?path=' + path + '&err=Folder already exists.')
        else:
            # If is not created, create the folder
            createFolder(full_path, root)
            self.redirect('/?path=' + path)

# The class for showing sign up page
class RegisterHandler(BaseHandler):
    def get(self):
        templateValues = {
        }
        path = os.path.join(os.path.dirname(__file__), "views/register.html")
        self.response.write(template.render(path, templateValues))

    def post(self):
        # Getting vairables for signing up
        email = self.request.get('email')
        password= self.request.get('password')
        password_c = self.request.get('password_confirm')

        # password confirm
        if password != password_c:
            templateValues = {
            'errmsg' : 'Password dismatch',
            'email' : email,
            }
            path = os.path.join(os.path.dirname(__file__), "views/register.html")
            self.response.write(template.render(path, templateValues))
        else:
            # Checking user duplication
            if self.userCheck(email) > 0:
                templateValues = {'errmsg' : 'User duplicated','email' : email,}
                path = os.path.join(os.path.dirname(__file__), "views/register.html")
                self.response.write(template.render(path, templateValues))
            else:
                # Register user to user model
                user = User()
                user.password = password
                user.email = email
                user_key = user.put()

                # Save user ID using session variable to identify user.
                self.session['root'] = user_key.urlsafe()

                # Create root determined uniquely by user.
                folder = Folder()
                folder.owner = user_key
                folder.path = str(user_key.id())
                folder.put()

				# Redirect to home
                self.redirect('/')

    # The function for checking user duplication
    def userCheck(self, useremail):
        qry = User.query()
        qry = qry.filter(User.email == useremail)
        results = qry.fetch()
        return len(results)

# Class for user log in
class SigninHandler(BaseHandler):
    def get(self):
        templateValues = {
        }
        path = os.path.join(os.path.dirname(__file__), "views/signin.html")
        self.response.write(template.render(path, templateValues))

    def post(self):
        # Getting variable for user log in
        useremail = self.request.get('email')
        password = self.request.get('pwd')

        qry = User.query()
        qry = qry.filter(User.email == useremail)
        result = qry.fetch()

        errmsg = ''
        # If user is not registered, make error message.
        if len(result) == 0:
            errmsg = 'Unknown User. Please sign up.'
        else:
            qry = qry.filter(User.password == password)
            result = qry.fetch()
            # If input password is not right
            if len(result) == 0:
                errmsg = 'Incorrect Passowrd.'
            else:
                # If user is right, set session variable for identifying user and redirect to home
                self.session['root'] = str(result[0].key.urlsafe())
                self.redirect('/')

        templateValues = {
            'error_message': errmsg
        }
        path = os.path.join(os.path.dirname(__file__), "views/signin.html")
        self.response.write(template.render(path, templateValues))

# The class for log out. When do this, surely initialize session variable
class SignoutHandler(BaseHandler):
    def get(self):
        self.session.clear()
        self.redirect('/signin')

# The class for deleting folder and showing that result
class RemoveFolderHandler(BaseHandler):
    def get(self):
        # Getting value of session variable
        root = self.session.get('root')

        # Getting path of folder for deleting
        path = self.request.get('path')
        if path == '':
            full_path = root
        else:
            full_path = root + '/' + path

        # Delete folder from datastore. Query condition means it contain sub directory.
        qry = Folder.query(Folder.path >= full_path)
        results = qry.fetch()

        # Query result is not correct, because of condition for querying. So fix them.
        for result in results:
            result_path = result.path
            if result_path.find(path) is not -1:
                result.key.delete()

        # After deleting, make directory for redirecting.
        if path.find('/') is not -1:
            red_path = path[:path.rindex('/')]
        else:
            red_path = ''

        self.redirect('/?path=' + red_path)

# The class for deleting file and showing that result.
class RemoveFileHandler(BaseHandler):
    def post(self):
        # getting session variable
        root = self.session.get('root')

        # getting file name and path for deleting file
        file = self.request.get('file')
        file = file.split(',')
        if file[0] == '':
            full_path = str(root)
        else:
            full_path = str(root) + '/' + file[0]
        filename = file[1]

        # Delete file from file model
        qry = File.query()
        qry = qry.filter(File.path == full_path)
        qry = qry.filter(File.name == filename)
        res = qry.fetch()
        res[0].key.delete()

        self.redirect('/?path=' + file[0])

# The class for making complex url in order to upload file
class UploadURL(webapp2.RequestHandler):
    def get(self):
        url_for_upload = blobstore.create_upload_url('/upload')
        self.response.out.write(url_for_upload)

# The class for uploading file and showing that result.
class Upload(BaseHandler):
    def post(self):
        # getting variable that include necessary informations for uploading file.
        upload = self.get_uploads()[0]

        # getting path
        root = self.session.get('root')
        path = self.request.POST.get('path')
        if path != '':
            file_path = root + '/' + path
        else:
            file_path = root

        # Get file info from blobinfo
        file_name = upload.filename;

        # Check if it duplicates
        if checkDuplicatedFile(root, file_name):
            # Delete the file from blobstore
            blobstore.BlobInfo(upload.key()).delete()

            # Display error message
            self.redirect('/?path=' + path + '&err=File already exists.')
            return

        file_size = int(round(blobstore.BlobInfo(upload.key()).size/1000))
        if file_size < 1:
            file_size = 1
        file_date = blobstore.BlobInfo(upload.key()).creation

        # When uploading file, if the file with same name and path is saved in blobstore, delete earlier file and rewrite that file
        query_result = File.query()
        query_result = query_result.filter(File.path == file_path)
        query_result = query_result.filter(File.name == file_name)
        result = query_result.fetch()
        if len(result) > 0:
            result[0].key.delete()
            blobstore.delete(result[0].blob_key)

        # file update to datastore
        file = File()
        file.name = file_name
        file.path = file_path
        file.blob_key = upload.key()
        file.size = file_size
        file.cdate = str(file_date.strftime("%m/%d/%Y %H:%M:%S"))
        file.put()

        self.redirect('/?path=' + path)

# The class for downloading file
class FileDownload(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, filekey, filename):
        # Setting header in response as following in oreder to download file
        self.response.headers['Content-Type'] = 'application/x-gzip'
        self.response.headers['Content-Disposition'] = 'attachment; filename=' + str(filename)

        # if the file that will be downloaded does not exist in blobstore
        if not blobstore.get(filekey):
            self.error(404)
        else:
            # if that file exists in blobstore
            self.send_blob(filekey)

class FileMoveHandler(BaseHandler):
    def post(self):
        root = self.session.get('root')

        move_file = self.request.get('movefile')
        move_path = self.request.get('movepath')
        origin_path = self.request.get('path')

        if origin_path == '':
            origin_path = root
        else:
            origin_path = root + '/' + origin_path

        if move_path == '':
            full_path = root
        else:
            full_path = root + '/' + move_path

        user_key = ndb.Key(urlsafe=root)
        qry = Folder.query(Folder.owner == user_key)
        user_folders = qry.fetch()
        for folder in user_folders:
            if (folder.path == full_path):
                qry = File.query()
                qry = qry.filter(File.name == move_file)
                qry = qry.filter(File.path == origin_path)
                results = qry.fetch()
                if (len(results) > 0):
                    moveFile = results[0]
                    moveFile.path = full_path
                    moveFile.put()
                    self.redirect('/?path=' + move_path)
                else:
                    errmsg = "File path error while moving"

        errmsg = "File path error while moving"
        self.redirect('/?path=' + move_path + '&err='+errmsg)

# Setting config for session variable
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my_secret_key',
}

# The function for checking duplication of folder
def checkDuplicatedFolder(path):
    qry = Folder.query()
    qry =  qry.filter(Folder.path == path)
    result = qry.fetch()
    if len(result) > 0:
        return True
    else:
        return False

# The function for checking duplication of common file
def checkDuplicatedFile(user_key, fname):
    qry = File.query()
    qry = qry.filter(File.name == fname)
    result = qry.fetch()
    for file in result:
        path = file.path
        if path.split('/')[0].strip() == user_key.strip():
            return True

    return False

# The function for making new folder
def createFolder(path, user):
    folder = Folder()
    user_key = ndb.Key(urlsafe=user)
    folder.owner = user_key
    folder.path = path
    now = datetime.now()
    folder.cdate = now.strftime("%m/%d/%Y %H:%M:%S")
    folder.fsize = 0
    folder.fnumber = 0
    folder.dnumber = 0
    folder_key = folder.put()


def displayUserFolders(userkey):
    userFolders = []
    user_key = ndb.Key(urlsafe=userkey)
    qry = Folder.query(Folder.owner == user_key)
    results = qry.fetch()
    for result in results:
        path = result.path
        showPath = path[len(userkey):]
        showPath = showPath[1:] if showPath[:1] == '/' else showPath
        userFolders.append({'showPath': showPath})

    return userFolders

# The function for getting the list of objects belong to Folder model.
def displayFolders(path, userkey):
    folders = []
    if (path != userkey): # if root
        folders.append({'name': '..', 'cdate': ''})

    # Get list of folders from datastore
    # Get Key object from thr urlsafe representation of Key
    user_key = ndb.Key(urlsafe=userkey)
    qry = Folder.query(Folder.owner == user_key)
    results = qry.fetch()
    for result in results:
        rpath = result.path
        start = rpath.find(path)
        if start != -1:
            sub = rpath[start + len(path) + 1:]
            if sub != '':
                if sub.find('/') == -1:
                    folders.append({'name': sub, 'cdate': result.cdate, 'dnumber': result.dnumber, 'fnumber':result.fnumber, 'fsize':result.fsize})

    if (path != userkey):
        qry = Folder.query(Folder.path == path)
        res = qry.fetch()
        parent_folder = res[0]
        parent_folder.dnumber = len(folders) - 1
        parent_folder.put()

    return folders

# The function for getting list of objects belong to File model.
def diplayFiles(path, userkey):
    qry = File.query(File.path == path)
    files = qry.fetch()
    fsize = 0
    for file in files:
        fsize += file.size

    if (path != userkey):
        qry = Folder.query(Folder.path == path)
        res = qry.fetch()
        parent_folder = res[0]
        parent_folder.fnumber = len(files)
        parent_folder.fsize = fsize
        parent_folder.put()
    return files

# The function for getting list of objects belong to User model.
def showUsers(userroot):
    qry = User.query()
    results = qry.fetch()
    userlist = []
    for result in results:
        userkey = result.key.id()
        if str(userkey) != str(userroot):
            userlist.append(result)
    return userlist


# Routing system for handle url request
app = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/register', RegisterHandler),
        ('/signin', SigninHandler),
        ('/signout', SignoutHandler),
        ('/removefolder', RemoveFolderHandler),
        ('/removefile', RemoveFileHandler),
        ('/uploadUrl', UploadURL),
        ('/upload', Upload),
        ('/download/([^/]+)?/([^/]+)?', FileDownload),
        ('/move', FileMoveHandler),
    ],
    debug=True,
    config=config)
