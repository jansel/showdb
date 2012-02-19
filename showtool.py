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

import showdb
import sys
import time
import sqlite3

try:
  cmd=sys.argv[1]
  args=sys.argv[2:]
  if "help" in cmd:
    raise Exception()
except:
  print '''USAGE:

showtool list 
   -- lists all known shows

showtool latest
   -- list episodes added in the last 48 hours

showtool search <showname> [episode]
   -- search for a specific show

showtool download <showname> [episode]
   -- download all episodes matching a given search

showtool fetch [url-to-rss-feed]
   -- scan a given RSS feed for new shows

showtool alias <oldshow> <newshow>
   -- add an alias to automatically rename one show to another

showtool cleanup 
   -- perform database cleanup

showtool query <sql-query>
   -- execute a raw query on the database
'''
  sys.exit(1)
  
searchname=' '.join(args)+'%'
searchep="%"
try:
  searchname,searchep=showdb.splitShowEp(' '.join(args))
except:
  pass
  
isfilteredshow = showdb.mkshowfilter()
mapmap=lambda fn, ll: map(lambda l: map(fn, l), ll)
db=showdb.opendb()
rv=db.cursor()
rows=[]

if cmd in ["list", "ls", "search", "find"]:
  print "Searching for name like",searchname,"episode like",searchep
  rv=db.execute('''
                   SELECT name,max(episode) as "last ep", count(distinct episode) as "eps",sum(downloaded>0) as dls,date(max(created),'unixepoch') as updated, '' as sub
                   FROM shows 
                   WHERE name LIKE ? AND episode LIKE ? 
                   GROUP BY name ORDER BY name
                ''', (searchname,searchep))
  rows=rv.fetchall()
  if len(rows)==1:
    rv=db.execute('''
                     SELECT name, episode, sum(downloaded>0) as "dls", count(*) as "vers", '' as sub
                     FROM shows 
                     WHERE name LIKE ? AND episode LIKE ? 
                     GROUP BY name,episode ORDER BY name,episode
                  ''', (searchname,searchep))
    rows=rv.fetchall()
  for i in xrange(len(rows)):
    if isfilteredshow(rows[i][0]):
      rows[i]=list(rows[i])
      rows[i][-1]='Y'

elif cmd in ["latest"]:
  rv=db.execute('''
                   SELECT name,episode as "episode", sum(downloaded>0) as "dls", count(*) as "vers", date(max(created),'unixepoch') as "updated"
                   FROM shows 
                   WHERE created > ?
                   GROUP BY name,episode ORDER BY max(created) DESC
                ''', [int(time.time())-3600*24])

elif cmd in ["download"]:
  assert len(args)>0
  rv=db.execute('''
                   SELECT DISTINCT name,episode
                   FROM shows 
                   WHERE name LIKE ? AND episode LIKE ? 
                ''', (searchname,searchep))
  rows=rv.fetchall()
  for name,ep in rows:
    showdb.downloadShow(name,ep)

elif cmd in ["fetch"]:
  import rssshowfeed
  if len(args)==0:
    rssshowfeed.updateShowDb()
  else:
    rssshowfeed.updateShowDb(args)
  showdb.checkNew()

elif cmd in ["check"]:
  assert len(args)==0
  showdb.checkNew()

elif cmd in ["cleanup"]:
  assert len(args)==0
  rv=db.execute("vacuum")
  rv=db.execute("analyze")
  db.commit()

elif cmd in ["alias"]:
  assert len(args)==2
  rv=db.execute("INSERT INTO aliases(oldname, newname) VALUES(?,?)", args)
  db.commit()

elif cmd in ["query"]:
  rv=db.execute(' '.join(args))

else:
  print "unknown command, for help run with --help"
  sys.exit(1)

if len(rows)==0:
  rows=rv.fetchall()

if len(rows)>0:
  rows=mapmap(str,rows)
  keys=map(lambda x: x[0], rv.description)
  lens=map(len, keys)
  def printrow(row):
    for e,l in zip(row, lens):
      print '|',
      print e.ljust(l),
    print '|'
  #get max width of each col
  for row in rows:
    for i in xrange(len(keys)):
      lens[i]=max(lens[i], len(row[i]))

  printrow(map(lambda x: x.upper(), keys))
  for row in rows:
    printrow(row)
  
print "count =", max(rv.rowcount,len(rows))







