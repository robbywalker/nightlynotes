#
#  emailer.py
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

from twisted.internet import defer
from twisted.python import log
from mail import smtpsender


class Emailer(object):
  def __init__(self, config, dbpool):
    self.__dbpool = dbpool

    outgoing = config['email']['outgoing']
    self.__sender = smtpsender.SMTPSender(dbpool, outgoing)


  def sendEmails(self):
    self.__dbpool.runQuery('SELECT id, email FROM user').addCallbacks(self.__sendEmails, log.msg)


  @defer.deferredGenerator
  def __sendEmails(self, result):
    for userRow in result:
      wfd = defer.waitForDeferred(self.__sendEmail(userRow[0], userRow[1]))
      yield wfd
      wfd.getResult()


  def __sendEmail(self, userId, email):
    return self.__sender.sendReminder(smtpsender.User(userId, email))
    