#!/usr/bin/env python
# Copyright (c) 2011 Nikhef. All rights reserved.
# Author: Oscar Koeroo <okoeroo (at) nikhef (dot) nl>
# BSD Licence

import subprocess, os, sys

if not os.path.exists('pack.list'):
    print "Missing 'pack.list' file"
    sys.exit(1)

f = open('pack.list', 'r')
s = f.read()

list = ""

for line in s.split('\n'):
    if line.startswith('#') or len(line) < 1:
        continue

    list += line + " "

os.system('tar czf arp-2-bgp.tar.gz ' + list)
print "done"


