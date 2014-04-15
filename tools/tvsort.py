#!/usr/bin/python
import os
import sys
import re

reShowName = re.compile(
  "[.](S[0-9]+E[0-9]+|20[0-9]{2}[.][0-9]{2}[.][0-9]{2}|[0-9]+of[0-9]+)[.]",
  re.IGNORECASE)


def parseFilename(str):
  t = reShowName.split(str, 2)
  if len(t) != 3:
    raise None
  t[0] = t[0].replace('.', ' ')
  return t


def sortShow(file, dirs):
  try:
    name, episode, extra = parseFilename(file)
    if name not in dirs and name.lower() in map(str.lower, dirs):
      name = filter(lambda d: d.lower() == name.lower(), dirs)[0]
    if name not in dirs:
      dirs.append(name)
      print "mkdir '%s'" % (name)
      #os.mkdir(name)
    print "mv '%s' '%s'" % (file, name)
    #os.rename(file,name+file)
  except:
    None


if __name__ == '__main__':
  if len(sys.argv) == 2:
    os.chdir(sys.argv[1])
  dirs = filter(os.path.isdir, os.listdir("."))
  files = filter(os.path.isfile, os.listdir("."))
  map(lambda x: sortShow(x, dirs), sorted(files))

