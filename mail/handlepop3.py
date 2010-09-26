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
    log.msg("parsed token %s from subject: %s" % (str(token), parsedMessage.get('Subject')))
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
    log.msg('trying to create entry for user %s and date %s' % (user_id, date))
    query = '''
      INSERT INTO user_entry (user_id, date, text)
      VALUES (%s, '%s', '%s')
    ''' % (user_id, date, body)
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

