from twisted.mail import smtp
from twisted.internet import reactor, defer
from twisted.enterprise import adbapi
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from datetime import datetime
import hashlib, sys

class SMTPSender:
  def __init__(self, dbpool, host, handle, domain):
    self.__dbpool = dbpool
    self.__host = host
    self.__handle = handle
    self.__domain = domain

  def sendReminder(self, user): # Assuming some User object with id and toaddr
    self.user = user
    self.generateToken(user.id)

  def send(self, result, token):
    fromaddr = self.__handle + '+' + token + '@' + self.__domain
    message = self.buildMessage(fromaddr, self.user.addr)
    messageData = message.as_string(unixfrom=False)
    sending = smtp.sendmail(self.__host, fromaddr, [self.user.addr], messageData)
    sending.addCallback(self.sendComplete).addErrback(self.handleError)

  def buildMessage(self, fromaddr, toaddr):
    prettydate = datetime.now().strftime('%A, %B %d')
    message = MIMEMultipart()
    message['To'] = toaddr
    message['From'] = fromaddr
    message['Subject'] = "It's " + prettydate + " - snippetize!"
    textPart = MIMEBase('text', 'plain')
    textPart.set_payload('Reply to this email to send in your snippets')
    message.attach(textPart)
    return message

  def sendComplete(self, result):
    print "Message sent."
    reactor.stop()

  def handleError(self, error):
    print >> sys.stderr, "Error!", error.getErrorMessage()
    reactor.stop()

  def generateToken(self, user_id):
    date = datetime.now().date()
    m = hashlib.md5()
    m.update(str(user_id))
    m.update(date.ctime())
    token = m.hexdigest()
    query = '''INSERT INTO token (token, user_id, date) VALUES ('%s', %s, '%s')''' % (
      token, user_id, date.strftime('%Y-%m-%d'))
    print query
    self.__dbpool.runQuery(query).addCallback(
      self.send, token).addErrback(
      self.handleError)
    reactor.run()

class User:
  def __init__(self):
    self.id = 5
    self.addr = 'christineyen@gmail.com'
