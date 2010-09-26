#
#  smtpsender.py
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


from twisted.mail import smtp
from twisted.internet import reactor, defer
from twisted.enterprise import adbapi
from twisted.python import log

from datetime import datetime
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart

import hashlib, sys



class SMTPSender:
  def __init__(self, dbpool, host, handle, domain):
    self.__dbpool = dbpool
    self.__host = host
    self.__handle = handle
    self.__domain = domain

  def sendReminder(self, user): # Assuming some User object with id and toaddr
    self.user = user
    return self.generateToken(user.id)

  def send(self, result, token):
    fromaddr = self.__handle + '+' + token + '@' + self.__domain
    message = self.buildMessage(fromaddr, self.user.addr)
    messageData = message.as_string(unixfrom=False)
    sending = smtp.sendmail(self.__host, fromaddr, [self.user.addr], messageData)
    sending.addErrback(log.msg)
    return sending

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

  def generateToken(self, user_id):
    date = datetime.now().date()
    m = hashlib.md5()
    m.update(str(user_id))
    m.update(date.ctime())
    token = m.hexdigest()
    query = '''REPLACE INTO token (token, user_id, date) VALUES ('%s', %s, '%s')''' % (
        token, user_id, date.strftime('%Y-%m-%d'))
    log.msg('Token query: %s' % query)

    queryDefer = self.__dbpool.runQuery(query)
    queryDefer.addCallback(self.send, token).addErrback(log.msg)
    return queryDefer



class User:
  def __init__(self, userId, email):
    self.id = userId
    self.addr = email
