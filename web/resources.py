#
#  resources.py
#  nightlynotes
#
#  Copyright 2010 The nightlynotes Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS-IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from twisted.python import log
from twisted.web import resource, server, static

import cgi
import cStringIO
import hashlib
import urllib



class HomeResource(resource.Resource):
  def __init__(self, dbpool):
    resource.Resource.__init__(self)

    self.putChild('', static.File('static/index.html'))
    self.putChild('signup', SignupResource(dbpool))
    self.putChild('user', UserResourceTree(dbpool))
    #self.putChild('browse', ...)



class SignupResource(static.File):
  def __init__(self, dbpool):
    static.File.__init__(self, 'static/signup.html')
    self.__dbpool = dbpool


  def __performSignup(self, txn, request):
    log.msg('Processing signup')

    email = request.args['email'][0]
    password = request.args['password'][0]

    txn.execute('SELECT * FROM user WHERE email=?', (email,))

    if txn.fetchall():
      log.msg('Username was taken')
      # TODO(robbyw): This is a bit hacky!  We should use templates.
      request.write('<p>That email is already registered.</p>')
      request.write(file('static/signup.html').read())
      request.finish()
    else:
      log.msg('Successful signup')
      passwordDigest = hashlib.sha224('nightlynotes:%s' % password).hexdigest()
      txn.execute('INSERT INTO user (email, password) VALUES (?, ?)', (email, passwordDigest))
      request.redirect('/user/%s' % urllib.quote(email))
      request.finish()


  def render(self, request):
    if request.method == 'POST':
      self.__dbpool.runInteraction(self.__performSignup, request).addErrback(log.msg)
      return server.NOT_DONE_YET

    else:
      return static.File.render(self, request)



class UserResourceTree(resource.Resource):
  def __init__(self, dbpool):
    resource.Resource.__init__(self)
    self.__dbpool = dbpool

  def __renderList(self, result, request):
    s = cStringIO.StringIO()
    s.write('<h1>Users</h1>')
    s.write('<ul>')
    for userRow in result:
      s.write('<li><a href="/user/%s">%s</a></li>' % (cgi.escape(userRow[0]), cgi.escape(userRow[0])))
    s.write('</ul>')
    request.write(s.getvalue())
    request.finish()

  def render_GET(self, request):
    self.__dbpool.runQuery("SELECT email FROM user ORDER BY email").addCallbacks(self.__renderList, log.msg, (request,))
    return server.NOT_DONE_YET

  def getChild(self, path, request):
    return UserResource(path, self.__dbpool)



class UserResource(resource.Resource):
  def __init__(self, email, dbpool):
    resource.Resource.__init__(self)
    self.__email = email
    self.__dbpool = dbpool

  def __renderList(self, result, request):
    s = cStringIO.StringIO()
    s.write('<h1>Posts by %s</h1>' % self.__email)
    for userRow in result:
      s.write('<hr>')
      s.write('<h2>%s</h2>' % userRow[0])
      s.write('<div>%s</div>' % userRow[1])
    request.write(s.getvalue())
    request.finish()

  def render_GET(self, request):
    query = """
        SELECT date, text FROM user_entry INNER JOIN user ON user.id == user_entry.user_id
        WHERE email = ?
        ORDER BY date desc
        """
    self.__dbpool.runQuery(query, (self.__email,)).addCallbacks(self.__renderList, log.msg, (request,))
    return server.NOT_DONE_YET
