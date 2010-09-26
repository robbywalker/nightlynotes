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
import hashlib


class HomeResource(resource.Resource):
  def __init__(self, dbpool):
    resource.Resource.__init__(self)

    self.putChild('', static.File('static/index.html'))
    self.putChild('signup', SignupResource(dbpool))
    #self.putChild('user', ...)
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
      request.redirect('/user/%s' % cgi.escape(email))
      request.finish()


  def render(self, request):
    if request.method == 'POST':
      self.__dbpool.runInteraction(self.__performSignup, request).addErrback(log.msg)
      return server.NOT_DONE_YET

    else:
      return static.File.render(self, request)
  