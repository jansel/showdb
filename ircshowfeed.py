#! /usr/bin/env python
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

import irclib
from ircbot import SingleServerIRCBot
from pprint import pprint
import showdb
import re
import random

from config import irc_names            as names
from config import irc_servers          as servers
from config import irc_channels         as channels 
from config import irc_usernameFilters   as usernameFilters
from config import irc_msgFilters       as msgFilters
from config import irc_msgFiltersIgnore as msgFiltersIgnore

#remove mIRC colors
cleanupMsgRe = re.compile("([\x01-\x1f]|\x03[0-9][0-9]?(,[0-9][0-9]?)?)")

servers=map(lambda x: (x,6667), servers)

class FeedScrapeBot(SingleServerIRCBot):
  def __init__(self, servers=servers, names=names, channels=channels, interval=60):
    print "IRC: connecting..."
    self.names=names
    SingleServerIRCBot.__init__(self, servers, random.sample(self.names,1)[0], random.sample(names,1)[0], interval)
    self.channelswanted = channels

  def get_nickname(self):
    return self.connection.get_nickname()
  
  def channels_checker(self):
    if not self.connection.is_connected():
      print "IRC: reconnecting..."
      self.jump_server()
    else:
      for chan in self.channelswanted:
        if not self.channels.has_key(chan):
          print "IRC: joining ",chan
          self.connection.join(chan)
    self.connection.execute_delayed(self.reconnection_interval, self.channels_checker)

  def on_nicknameinuse(self, c, e):
    print "IRC: nicknameinuse", self.get_nickname()
    c.nick(random.sample(self.names,1)[0])

  def on_welcome(self, c, e):
    print "IRC: connected", self.connection.get_server_name(), "with nickname", self.get_nickname()
    self.connection.mode(self.get_nickname(),":+i")
    self.channels_checker()

  def on_privmsg(self, c, e):
    print "IRC:", e.eventtype(), e.source(), e.target(), e.arguments()

  def on_pubmsg(self, c, e):
    try:
      user = e.source().split('!',1)[0]
      chan = self.channels[e.target()]
      msg = e.arguments()[0]
      msg = cleanupMsgRe.sub("",msg)
      self.check_msg(e.target(),chan,user,msg)
    except Exception, e:
      print "IRC: error:",e

  def check_msg(self, channame, chan, user, msg):
    #if chan.is_oper(user) or chan.is_voiced(user):
      if any(map(lambda x: x.search(user) is not None, usernameFilters)):
        for r in msgFilters:
          m=r.match(msg)
          if m:
            src=m.group(1)
            url=m.group(2)
            try:
              show,ep=showdb.splitShowEp(src)
              showdb.add(show,ep,src,url,method="IRC:%s"%channame)
              return
            except Exception, e:
              showdb.parseFailed('IRC', src, url, channame)
        for r in msgFiltersIgnore:
          m=r.match(msg)
          if m:
            return
        print "IRC: NOMATCH",channame,user,msg


def main():
  FeedScrapeBot().start()

if __name__ == "__main__":
  main()

