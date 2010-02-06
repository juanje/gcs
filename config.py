#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Parse /etc/gcs.conf for configuration options
"""

import sys

import yaml

try:
    config = yaml.load(open('/etc/gcs.conf').read())

    # Add default options
    config['source_path'] = './'
    config['info'] = {}
    if not config.has_key('diverts_basepath'):
        config['diverts_basepath'] = '/'
    
except:
    print "Can't read /etc/gcs.conf file."
    sys.exit(1)

