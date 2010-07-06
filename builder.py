#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import os.path
import shutil

import yaml

from config import config
from generators.file import ControlGenerator
from generators.file import RulesGenerator 
from generators.file import ChangelogGenerator 
from generators.file import CompatGenerator 
from generators.file import PreInstGenerator
from generators.file import PostInstGenerator
from generators.file import PreRmGenerator
from generators.file import PostRmGenerator
from generators.file import CompatGenerator
from generators.file import ConfigGenerator
from generators.file import TemplatesGenerator
from generators.file import CopyrightGenerator


class Builder(object):
    """ The responsability of this class is to call all the ScriptGenerator.activate methods in the right way.
    """

    def __init__(self, path):
        config['source_path'] = path
        config['info'] = yaml.load(open(path + '/gcs/info').read())
        extension = config['info'].get('config_extension', None)
        if extension:
            config['config_extension'] = extension


    def make_package(self):
        """ Make the package. Use ScriptGenerator objects for this propouse.
        """
        try:
            os.mkdir(config['source_path'] + '/debian')
        except OSError:
            pass

        self.__prepare_conffiles()

        ControlGenerator().activate()
        RulesGenerator().activate()
        ChangelogGenerator().activate()
        CompatGenerator().activate()
        PreInstGenerator().activate()
        PostInstGenerator().activate()
        PreRmGenerator().activate()
        PostRmGenerator().activate()
        CompatGenerator().activate()
        ConfigGenerator().activate()
        TemplatesGenerator().activate()
        CopyrightGenerator().activate()

        # FIXME: At the moment we need to keep the configuration files because
        # the conversion doesn't transparently (dh_install rename problem)
        #self.__delete_tmpfiles()




    def build_package(self):
        """ Build the package. Use a simply debuild for this propouse.
        """
        try:
            os.system('debuild -us -uc')
        except:
            pass


    def __prepare_conffiles(self):
        """ Add .gcs extension at all conffiles (making a copy)
        """
        def copy_file(arg, dirname, file_names):

            for fname in file_names:
                abs_path = dirname + os.sep + fname

                if (not '/.svn' in abs_path) and \
                        (not abs_path.endswith(config['config_extension']))\
                        and (os.path.isfile(abs_path)):
                    shutil.copy(abs_path, abs_path + \
                            config['config_extension'])

        os.path.walk(config['source_path'] + '/gcs/conffiles_skel/',
                copy_file, None)


    def __delete_tmpfiles(self):
        """ Add .gcs extension at all conffiles (making a copy)
        """
        def delete_file(arg, dirname, file_names):

            for fname in file_names:
                abs_path = dirname + os.sep + fname

                if abs_path.endswith(config['config_extension']):
                    os.remove(abs_path)

        os.path.walk(config['source_path'] + '/gcs/conffiles_skel/',
                delete_file, None)

