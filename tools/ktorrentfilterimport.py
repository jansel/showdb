#!/usr/bin/python
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

import sys
import re
from pprint import pprint

r1=re.compile("[0-9]+:")
r2=re.compile("word_matches")

lines=r1.split(open(sys.argv[1]).read())

idxs=filter(lambda i: r2.match(lines[i]) is not None, xrange(len(lines)))
idxs=map(lambda x: x+1, idxs)

for x in idxs:
  print lines[x][:-1]


