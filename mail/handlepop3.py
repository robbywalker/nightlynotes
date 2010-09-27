#
#  handlepop3.py
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


from twisted.mail import pop3client
from twisted.internet import reactor, protocol, defer, ssl
from twisted.enterprise import adbapi, util as dbutil
from twisted.python import log

import email
import re
import sys

class POP3Downloader(pop3client.POP3Client):
  def serverGreeting(self, greeting):
    pop3client.POP3Client.serverGreeting(self, greeting)
    login = self.login(self.factory.username, self.factory.password)
    login.addCallback(self._loggedIn)

  def _loggedIn(self, result):
    return self.listSize().addCallback(self._gotMessageSizes)

  def _gotMessageSizes(self, sizes):
    retrievers = []
    for i in range(len(sizes)):
      retrievers.append(self.retrieve(i).addCallback(
        self._gotMessageLines))
    return defer.DeferredList(retrievers).addCallback(
      self._finished)

  def _gotMessageLines(self, messageLines):
    self.factory.handleMessage("\r\n".join(messageLines))

  def _finished(self, downloadResults):
    return self.quit()


class POP3DownloadFactory(protocol.ClientFactory):
  protocol = POP3Downloader

  def __init__(self, dbpool, username, password):
    self.__dbpool = dbpool
    self.username = username
    self.password = password

  def handleMessage(self, messageData):
    parsedMessage = email.message_from_string(messageData)
    token = re.search(r'\[token (.*)\]', parsedMessage.get('Subject'))
    if token is None:
      log.msg('Missing token from subject: %s' % (parsedMessage.get('Subject')))
      return
    body = parsedMessage.get_payload().strip()
    self._getUserAndDateFromToken(token.group(1), body)

  def clientConnectionFailed(self, connection, reason):
    log.msg(reason)

  def _getUserAndDateFromToken(self, token, body):
    query = 'SELECT user_id, date FROM token WHERE token = ?'
    queryDefer = self.__dbpool.runQuery(query, (token,))
    queryDefer.addCallback(
      self._createEntry, body).addErrback(
      self._failed, 'Token not found: ' + token)
    return queryDefer

  def _createEntry(self, result, body):
    if len(result) == 0:
      log.msg('no user_id or date for token')
      return
    user_id = result[0][0]
    date = result[0][1]
    log.msg('Creating entry for user %s and date %s' % (user_id, date))
    query = '''
      INSERT OR ABORT INTO user_entry (user_id, date, text) VALUES (?, ?, ?)
    '''
    queryDefer = self.__dbpool.runQuery(query, (user_id, date, body))
    queryDefer.addErrback(self._insertUserEntryFailed, user_id, date, body)
    return queryDefer

  def _insertUserEntryFailed(self, failure, user_id, date, body):
    log.msg('Fetching existing user_entry for %s on %s' % (user_id, date))
    query = 'SELECT text FROM user_entry WHERE user_id = ? AND date = ?'
    queryDefer = self.__dbpool.runQuery(query, (user_id, date))
    queryDefer.addCallback(
      self._appendEntry, user_id, date, body).addErrback(
      self._failed, 'Query: ' + query)
    return queryDefer

  def _appendEntry(self, result, user_id, date, body):
    if len(result) != 1:
      log.msg('Trying to append to an existing entry, but no existing' + \
        ' entry found for %s on %s?' % (user_id, date))
      return

    log.msg('Updating entry for user %s and date %s' % (user_id, date))
    query = 'UPDATE user_entry SET text = ? WHERE user_id = ? AND date = ?'
    newBody = '%s\r\n\r\n%s' % (result[0][0], body)
    queryDefer = self.__dbpool.runQuery(query, (newBody, user_id, date))
    queryDefer.addErrback(self._failed, 'Query: ' + query)
    return queryDefer

  def _failed(self, failure, msg):
    msg = 'Failure: ' + msg
    print >> sys.stderr, msg, failure.getErrorMessage()


class POP3Receiver:
  def __init__(self, dbpool, host, defaultaddr, password):
    self.__host = host
    self.f = POP3DownloadFactory(dbpool, defaultaddr, password)

  def fetchEmails(self):
    reactor.connectSSL(self.__host, 995, self.f, ssl.ClientContextFactory())

