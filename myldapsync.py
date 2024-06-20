#!/usr/bin/env python

###########################################################################################
#
# myldapsync - fork of pgldapsync by EnterpriseDB Corporation adopted for MySQL and MariaDB
#
# Synchronise MySQL users with users in an LDAP directory.
#
###########################################################################################

# -*- coding: utf-8 -*-

"""myldapsync application runner."""

# FIX THIS!
# pylint: disable=import-self

import re
import sys

from myldapsync import main

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
