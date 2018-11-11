#!/usr/bin/env python3

import os
import sys
from lkadmin import cli

thisfile = __file__
if not os.path.isabs(thisfile):
    thisfile = os.path.normpath(os.path.join(os.getcwd(), thisfile))
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(thisfile), '..')))

sys.exit(cli.run(thisfile, sys.argv[1:]))