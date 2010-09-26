#
#  setup.py
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


def SetupDatabase(txn):
  log.msg('Setting up database')

  txn.execute('CREATE TABLE IF NOT EXISTS globals (key VARCHAR(63) PRIMARY KEY, value VARCHAR(255))')

  txn.execute('SELECT value FROM globals WHERE key="version"')
  rows = txn.fetchall()

  if not rows:
    version = 0
  else:
    version = int(rows[0][0])

  log.msg('Current version is %d' % version)

  if version == 0:
    txn.execute('CREATE TABLE user (id INTEGER PRIMARY KEY AUTOINCREMENT, email VARCHAR(255), password VARCHAR(255))')
    txn.execute('CREATE TABLE user_entry (user_id INT, date DATE, text TEXT)')
    txn.execute('REPLACE INTO globals VALUES ("version", "1")')
    version = 1
    log.msg('Upgraded to version 1')
