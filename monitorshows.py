#!/usr/bin/env python
# Copyright (C) 2009-2010 by Jason Ansel
# jansel@csail.mit.edu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import os
import select
import socket
import sys
import showdb

from config import rss_interval, check_interval, check_delay

wake_r, wake_w = socket.socketpair()


def wake():
  try:
    wake_w.send("\n", socket.MSG_DONTWAIT)
  except Exception, e:
    print "wake() failed", e


def run_rssshowfeed_once(feed_url):
  pid = os.fork()
  if pid == 0:
    import rssshowfeed

    showdb.on_add = wake
    rssshowfeed.updateShowDb([feed_url])
    sys.exit(0)
  return os.waitpid(pid, 0)


def fork_rssshowfeed():
  pid = os.fork()
  if pid == 0:
    import config
    import rssshowfeed

    while True:
      for x in config.rss_feed_urls:
        run_rssshowfeed_once(x)
        time.sleep(rss_interval)
    sys.exit(0)
  return pid


def fork_ircshowfeed():
  pid = os.fork()
  if pid == 0:
    import ircshowfeed

    showdb.on_add = wake
    ircshowfeed.main()
    sys.exit(0)
  return pid


fork_ircshowfeed()
fork_rssshowfeed()

while True:
  showdb.checkNew()
  rl, wl, xl = select.select([wake_r], [], [], check_interval)
  time.sleep(check_delay)
  if len(rl) > 0:
    try:
      if len(wake_r.recv(4096, socket.MSG_DONTWAIT)) <= 0:
        print "DB: check unknown reason..."
    except Exception, e:
      print "wake_r.recv failed", e

