#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)fix_storage.py
# 
# 
# Copyright (C) 2013 S3IT, University of Zurich. All rights reserved.
# 
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__docformat__ = 'reStructuredText'

import json
import os

storagedir = os.path.expanduser('~/.elasticluster/storage')

def fix_storage_file(path):
    data = json.load(open(path, 'r'))
    if 'nodes' in data:
        print "Storage file already fixed"
        return None

    for d in data['frontend']:
        d['type'] = 'frontend'
    for d in data['compute']:
        d['type'] = 'compute'
    data['nodes'] = data['frontend'] + data['compute']
    del data['frontend']
    del data['compute']
    open(path, 'w').write(json.dumps(data))
    

if __name__ == "__main__":
    for fname in os.listdir(storagedir):
        fix_storage_file(os.path.join(storagedir, fname))
