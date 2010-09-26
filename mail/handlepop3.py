from twisted.mail import pop3client
from twisted.internet import reactor, protocol, defer, ssl
from twisted.enterprise import adbapi, util as dbutil
from twisted.python import log
import email, re, sys

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
    log.msg("parsed token %s from subject: %s" % (
      str(token.group(1)), parsedMessage.get('Subject')))
    if token is None:
      return
    body = parsedMessage.get_payload()[0].get_payload().strip()
    self._getUserAndDateFromToken(token.group(1), body)

  def clientConnectionFailed(self, connection, reason):
    log.msg(reason)

  def _getUserAndDateFromToken(self, token, body):
    query = "SELECT user_id, date FROM token WHERE token = '%s'" % (token)
    queryDefer = self.__dbpool.runQuery(query)
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
      INSERT OR ABORT INTO user_entry (user_id, date, text)
      VALUES (%s, '%s', '%s')
    ''' % (user_id, date, body)
    queryDefer = self.__dbpool.runQuery(query)
    queryDefer.addErrback(self._insertUserEntryFailed, user_id, date, body)
    return queryDefer

  def _insertUserEntryFailed(self, failure, user_id, date, body):
    log.msg('Fetching existing user_entry for %s on %s' % (user_id, date))
    query = '''
      SELECT text FROM user_entry WHERE user_id = %s AND date = '%s'
    ''' % (user_id, date)
    queryDefer = self.__dbpool.runQuery(query)
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
    query = '''
      UPDATE user_entry SET text = '%s\n%s' WHERE user_id = %s AND date = '%s'
    ''' % (result[0][0], body, user_id, date)
    queryDefer = self.__dbpool.runQuery(query)
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

