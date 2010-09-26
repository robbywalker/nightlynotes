#
#  nightlynotes.tac
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

from twisted.application import internet, service
from twisted.enterprise import adbapi
from twisted.python import log
from twisted.web import resource, server, static

import simplejson as json
import sys

from db import setup
from web import resources
from mail import smtpsender

config = json.load(open('config.json'))

dbpool = adbapi.ConnectionPool(config['database']['module'], *config['database']['parameters'])
dbpool.runInteraction(setup.SetupDatabase).addErrback(log.msg)

application = service.Application('nightlynotes')
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(config['port'], server.Site(resources.HomeResource(dbpool))).setServiceParent(serviceCollection)

outgoing = config['email']['outgoing']
sender = smtpsender.SMTPSender(dbpool, outgoing['host'], outgoing['handle'], outgoing['domain'])
christine = smtpsender.User()
sender.sendReminder(christine)

#incoming = config['email']['incoming']
#receiver = handlepop3.POP3Receiver(dbpool, incoming['host'], incoming['username'], incoming['password'])

#receiver.fetchEmails()
