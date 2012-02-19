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

import base64
import startdownload 
import gzip
import os
import re
import sqlite3
import subprocess 
import sys
import time
import config
from StringIO import StringIO
from pprint import pprint

try:
  from urllib2 import urlopen
except:
  from urllib import urlopen

try:
  import libtorrent
except:
  import deluge.libtorrent as libtorrent

from config import showdb_file,download_dir,filters_file,titlere_SE,titlere_DATE

showdb_file = os.path.expanduser(showdb_file)
filters_file = os.path.expanduser(filters_file)
download_dir = os.path.expanduser(download_dir)
assert os.path.isfile(filters_file)
assert os.path.isdir(download_dir)

def patchURL(url):
  url=url.replace("bt-chat.com/details.php?",      "bt-chat.com/download1.php?",1)
  url=url.replace("mininova.org/tor/",             "mininova.org/get/",1)
  return url.strip()


normalizeShownameRe = re.compile("(uncensored|micro|[\t .-])*$", re.IGNORECASE)
normalizeShowName = lambda s: normalizeShownameRe.sub('', s).replace('.',' ').replace('_',' ').strip()

propercase=lambda s: ' '.join(map(lambda x: x.capitalize(), s.split(' ')))

on_add=lambda: None

#normalize date strings
def makeDateStr(d):
  if len(d) == 0:
    return "0-0-0"
  #try many different date formats
  for f in ["%b %d %Y", "%b %d, %Y", "%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%m/%d/%y"]:
    try:
      return time.strftime("%Y-%m-%d",time.strptime(d, f))
    except:
      pass
  return d

#normalize season/episode strings
makeSeEpStr = lambda s, e: "S%02dE%02d"%(int(s),int(e))

#split a title or filename into a showname and episode
def splitShowEp(title):
  for reg in titlere_SE:
    m = reg.match(title)
    if m is not None:
      return (normalizeShowName(m.group(1)), makeSeEpStr(m.group(2), m.group(3)))
  for reg in titlere_DATE:
    m = reg.match(title)
    if m is not None:
      return (normalizeShowName(m.group(1)), makeDateStr(m.group(2)))
  raise Exception("invalid title")

#load a list of regexps
def loadlist(filename):
  lines=open(filename).readlines()
  lines=map(lambda x: x.strip(), lines)
  lines=filter(lambda x: len(x)>0,  lines)
  lines=filter(lambda x: x[0]!='#', lines)
  return lines

#return a function to check if a show is subscribed
def mkshowfilter():
  filters = map(lambda x: re.compile(x, re.IGNORECASE), loadlist(filters_file))
  return lambda name: any(map(lambda r: r.match(name) is not None, filters))

#check disk for a show
def findExistingEpisode(searchshow, searchep):
  def ismatch(name):
    try:
      show,ep=splitShowEp(name)
      if show.lower()==searchshow and ep==searchep:
        return True
    except:
      pass
    return False
  searchshow=searchshow.lower()
  for name in os.listdir(download_dir):
    path=download_dir+"/"+name
    if os.path.isfile(path) and ismatch(name):
      return True
    if os.path.isdir(path) and name.lower()==searchshow:
      if any(map(ismatch, os.listdir(path))):
        return True
  return False


#parse simple data from a torrent file
class TorrentInfo:
  def __init__(self, url):
    self.url=url
    try:
      self.torrent=urlopen(url).read()
    except Exception,e:
      raise Exception("urlopen failed:"+str(e))
    try:
      self.info=libtorrent.torrent_info(libtorrent.bdecode(self.torrent))
    except:
      #try with gunzip
      self.torrent=gzip.GzipFile("","rb",1, StringIO(self.torrent)).read()
      self.info=libtorrent.torrent_info(libtorrent.bdecode(self.torrent))
  def trackers(self):
    return map(lambda x: x.url, self.info.trackers())
  def files(self):
    return map(lambda x: x.path, self.info.files())
  def total_size(self):
    return self.info.total_size()
  def info_hash(self):
    return str(self.info.info_hash())
  def writeto(self, path):
    open(path, 'wb').write(self.torrent)
  def download(self):
   return startdownload.downloadTorrent(download_dir, self.url, self.torrent)

#lower is better
def scoreTorrent(name, episode, torrent):
  score=0
  files = torrent.files()
  if len(files) != 1:
    score+=8 #wrong number of files
  else:
    try:
      _name,_episode = splitShowEp(files[0])
      if _name.lower()!=name.lower() or _episode!=episode:
        score+=2 #file parsed to wrong thing
    except:
      score+=4 #cant parse the file
  return score

opendb = lambda: sqlite3.connect(showdb_file)

def createTables():
  db = opendb()
  db.executescript('''
      CREATE TABLE IF NOT EXISTS shows (
        id         INTEGER PRIMARY KEY,
        name       TEXT COLLATE NOCASE,
        episode    TEXT COLLATE NOCASE,
        url        TEXT COLLATE NOCASE,
        src        TEXT COLLATE NOCASE,
        created    INTEGER,
        downloaded INTEGER DEFAULT 0,
        checked    INTEGER DEFAULT 0,
        UNIQUE(name,episode,url)
      );
      
      CREATE INDEX IF NOT EXISTS idx_shows_checked
      ON shows(checked);
  
      -- aliases use the following triggers to auto-rename shows
      CREATE TABLE IF NOT EXISTS aliases (
        oldname TEXT COLLATE NOCASE UNIQUE,
        newname TEXT COLLATE NOCASE,
        UNIQUE(oldname,newname)
      );

      -- apply new aliases to existing shows on creation
      CREATE TRIGGER IF NOT EXISTS trg_alias_created
        AFTER INSERT ON aliases 
        BEGIN 
          UPDATE OR REPLACE shows SET name=NEW.newname WHERE name=NEW.oldname; 
        END;
      CREATE TRIGGER IF NOT EXISTS trg_alias_updated
        AFTER UPDATE ON aliases 
        BEGIN 
          UPDATE OR REPLACE shows SET name=NEW.newname WHERE name=NEW.oldname; 
        END;
      
      -- apply existing aliases to new shows as they are added
      CREATE TRIGGER IF NOT EXISTS trg_alias_apply_insert
        AFTER INSERT ON shows 
        WHEN NEW.name IN (SELECT oldname FROM aliases)
        BEGIN 
          UPDATE shows SET name = (SELECT newname FROM aliases WHERE oldname=NEW.name) WHERE rowid=NEW.rowid;
        END;
      CREATE TRIGGER IF NOT EXISTS trg_alias_apply_update
        AFTER UPDATE OF name ON shows
        WHEN NEW.name IN (SELECT oldname FROM aliases)
        BEGIN 
          UPDATE shows SET name = (SELECT newname FROM aliases WHERE oldname=NEW.name) WHERE rowid=NEW.rowid;
        END;
      
      
      -- list of failed parses
      CREATE TABLE IF NOT EXISTS unparsed (
        src        TEXT COLLATE NOCASE,
        url        TEXT COLLATE NOCASE,
        created    INTEGER,
        UNIQUE(src,url)
      );
    ''')
  db.commit()
  db.close()

createTables()

#add a torrent to the database
def add(name, episode, src, url, method='DB'):
  db=opendb()
  url=patchURL(url)
  try:
    rc=db.execute("INSERT INTO shows(name,episode,src,url,created) VALUES (?,?,?,?,?)",
                 (name,episode,src,url,int(time.time()))).rowcount
  except:
    rc=0
  db.commit()
  db.close()
  if rc>0:
    print "%s: Added:"%method, name, episode, url
    on_add()
    return True
  else:
    return False

#add a torrent to the database
def parseFailed(pfx, src, url, msg=""):
  db=opendb()
  url=patchURL(url)
  try:
    rc=db.execute("INSERT INTO unparsed(src,url,created) VALUES (?,?,?)",
                 (src,url,int(time.time()))).rowcount
  except:
    rc=0
  db.commit()
  db.close()
  if rc>0:
    print "%s: PARSE FAILED: %s" % (pfx,src), msg
    return True
  else:
    return False

def downloadShow(name, episode, t=int(time.time())):
  db=opendb()
  r=db.execute("SELECT count(*) FROM shows WHERE name=? AND episode=? AND downloaded>0", (name,episode))
  is_downloaded=r.fetchone()[0]>0
  if is_downloaded:
    print "DB: skipping download (downloaded):", name, episode
    db.close()
    return True

  is_existing  = findExistingEpisode(name, episode)
  if is_existing:
    print "DB: skipping download (existing):", name, episode
    db.close()
    return True

  r=db.execute('''SELECT id,url 
                  FROM shows WHERE name=? AND episode=?
                  ORDER BY src LIKE '%hdtv%' DESC
               ''', (name,episode))
  best=None
  for sid,url in r:
    try:
      torrent = TorrentInfo(url)
      torrent.sid=sid
      torrent.score=scoreTorrent(name,episode,torrent)
      if best is None or best.score>torrent.score:
        best=torrent
        if best.score==0:
          break
    except Exception, e:
      print "DB: ",name,episode,"download failed:",e, url
      pass

  db.close()#cant have db open durring fork()
  if best is not None and best.download():
    db=opendb()
    db.execute("UPDATE shows SET downloaded=? WHERE id=?", (t, best.sid))
    db.commit()
    db.close()
    print "DB: downloaded:", name, episode, "(score=%d)"%torrent.score
    return True
  else:
    return False

def markChecked(name, episode, t):
  db=opendb()
  db.execute("UPDATE shows SET checked=? WHERE checked=0 AND created<=? AND name=? and episode=?", (t,t,name,episode))
  db.commit()
  db.close()

def checkNew():
  isSubscribed=mkshowfilter()
  t = int(time.time())
  db=opendb()
  rows = db.execute("SELECT DISTINCT name, episode FROM shows WHERE checked=0").fetchall()
  db.close()
  for name, episode in rows:
    if isSubscribed(name):
      if downloadShow(name, episode, t):
        markChecked(name, episode, t)
    else:
      markChecked(name, episode, t)

if __name__ == "__main__":
  while True:
    checkNew()
    time.sleep(config.check_interval)

