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

import feedparser
from pprint import pprint
import time
import signal
import showdb
import config

from config import rss_feed_urls as feed_urls
from config import rss_timeout as timeout

#works for ezrss.it, tvrss.net, etc
def parseSummaryBased(show, feed_url):
  showinfo = dict()
  for e in show['summary'].split(';'):
    try:
      k, v = e.split(':', 1)
      showinfo[k.lower().strip()] = v.strip()
    except:
      pass
  if showinfo.has_key('show name'):
    if showinfo.has_key('season') and showinfo.has_key('episode'):
      ep = showdb.makeSeEpStr(showinfo['season'], showinfo['episode'])
    elif showinfo.has_key('episode date'):
      ep = showdb.makeDateStr(showinfo['episode date'])
    else:
      raise Exception("invalid episode number" + str(showinfo))
    return showdb.add(showinfo['show name'], ep, show['title'] + " " + feed_url,
                      show['link'], method='RSS')
  raise Exception("invalid summary")


def grade_link(link):
  score = 0
  if 'enclosure' in link['rel']:
    score -= 1
  if 'torrent' in link['href']:
    score -= 2
  if '.torrent' in link['href']:
    score -= 4
  if 'torcache.net' in link['href']:
    score -= 8
  if 'bittorrent' in link['type']:
    score -= 16
  return score

#works for most others
def parseTitleBased(show, feed_url):
  name, ep = showdb.splitShowEp(show['title'])
  links = list(show['links'])
  links.sort(key=grade_link)
  return showdb.add(name, ep, show['title'] + " " + feed_url, links[0]['href'],
                    method='RSS')


#attempt to convert an rss feed entry into an Episode() instance
def parseEpisode(show, feed_url):
  errs = []
  for parser in [parseSummaryBased, parseTitleBased]:
    try:
      return parser(show, feed_url)
    except Exception, e:
      errs.append(e)
  try:
    showdb.parseFailed("RSS", show['title'], show['link'], feed_url)
  except:
    pass
  return None


def parseFeed(feed_url, feed):
  existing = 0
  found = 0
  errors = 0
  for e in feed['entries']:
    rv = parseEpisode(e, feed_url)
    if rv is True:
      found += 1
    if rv is False:
      existing += 1
    if rv is None:
      errors += 1
  print "RSS: fetched ", feed_url, " %d existing %d new %d errors" % (
  existing, found, errors)


def onTimeout(signum, frame):
  raise Exception("timeout")


def updateShowDb(feed_urls=feed_urls):
  for u in feed_urls:
    try:
      signal.signal(signal.SIGALRM, onTimeout)
      signal.alarm(timeout)
      parseFeed(u, feedparser.parse(u))
      signal.alarm(0)
    except Exception, e:
      signal.alarm(0)
      print "RSS: FAILED:", e


if __name__ == "__main__":
  import sys

  if len(sys.argv[1:]) > 0:
    updateShowDb(sys.argv[1:])
  else:
    while True:
      updateShowDb()
      time.sleep(config.rss_interval)

