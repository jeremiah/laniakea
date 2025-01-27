#!/usr/bin/env python3

import os
import sys

thisfile = __file__
if not os.path.isabs(thisfile):
    thisfile = os.path.normpath(os.path.join(os.getcwd(), thisfile))
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(thisfile), '..', 'lib', 'laniakea')))
if not thisfile.startswith(('/usr', '/bin')):
    sys.path.append(os.path.normpath(os.path.join(os.path.dirname(thisfile), '..')))

from daktape import cli

sys.exit(cli.run(thisfile, sys.argv[1:]))
