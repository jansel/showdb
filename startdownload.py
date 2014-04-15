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
import sys, os, traceback
from base64 import b64encode

import transmissionrpc

tc = transmissionrpc.Client()

# from deluge.ui.client import sclient as client
# from deluge.ui.common import get_localhost_auth_uri
#
# def downloadTorrent(path, filename, filedump):
#   client.set_core_uri(get_localhost_auth_uri("http://localhost:58846"))
#   client.set_config({'download_location': path})
#   print "Downloading",filename
#   client.add_torrent_file_binary(filename, filedump, [])
#   return True

def downloadTorrent(path, filename, filedump):
  try:
    tc.add(b64encode(filedump),
           download_dir=os.path.abspath(os.path.expanduser(path)))
    return True
  except:
    print "ERROR: Download of", filename, "failed"
    traceback.print_exc()
    return False


def downloadTorrentFile(path, torrentfile):
  filename = os.path.split(torrentfile)[-1]
  filedump = open(torrentfile).read()
  return downloadTorrent(path, filename, filedump)


if __name__ == "__main__":
  assert len(sys.argv) == 3
  if downloadTorrentFile(sys.argv[1], sys.argv[2]):
    print "OK"
    sys.exit(0)
  else:
    print "FAILED"
    sys.exit(1)

