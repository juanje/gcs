#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Parse /etc/gcs.conf for configuration options
"""

import re
import os
import sys
import yaml

try:
    config = yaml.load(open('/etc/gcs.conf').read())
except:
    print "Can't read /etc/gcs.conf file."
    sys.exit(1)

# Add default options
config['source_path'] = './'
config['info'] = {}
config['questions'] = []
if not config.has_key('diverts_basepath'):
    config['diverts_basepath'] = '/'

questions_path = config['source_path'] + '/gcs/questions'

if os.path.isdir(questions_path):
    for template_file in os.listdir(questions_path):
        template_path = config['source_path'] + 'gcs/questions/' + template_file

        if os.path.isdir(template_path):
            pass
        
        try:
            template = re.sub(r'\n\n', '\n---\n', open(template_path).read())
            template = re.sub(r'(?=\W+):(?=.+\n )', ': |\n', template)
            for question in yaml.load_all(template):
                config['questions'].append(question)
        except yaml.scanner.ScannerError as e:
            print "Error parsing %s file." % template_path
            print e
        except Exception as e:
            print e
            sys.exit(1)
