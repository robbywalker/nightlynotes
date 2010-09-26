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
from twisted.web import resource, server, static

import json
import sys

from web import resources

config = json.load(open('config.json'))
  
application = service.Application('nightlynotes')
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(config['port'], server.Site(resources.HomeResource())).setServiceParent(serviceCollection)