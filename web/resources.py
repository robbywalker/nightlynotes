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

from twisted.web import resource, server, static

import cgi


class HomeResource(resource.Resource):
  def __init__(self, dbpool):
    resource.Resource.__init__(self)
    self.__dbpool = dbpool

    self.putChild('', static.File("static/index.html"))
    #self.putChild('signup', ...)
    #self.putChild('user', ...)
    #self.putChild('browse', ...)
