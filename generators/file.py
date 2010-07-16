#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import re
import datetime
import email.Utils

from config import config
from generators.part import DivertPart
from generators.part import ScriptsPart 


class FileGenerator(object):

    def __init__(self):
        self.template_content = ''

    
    def activate(self):
        raise NotImplementedError


    def set_template_content(self, template_name):
        """ Set template content from  template_name (using config dictionary)

        @param template_name: Key of the config dictionary for template.
        @type template_name: string
        """
        try:
            template_file = open(config[template_name])
            self.template_content = template_file.read()
            template_file.close()
        except KeyError:
            print "Don't find template '%s'" % template_name
        except:
            print "Can't create template content. Template: %s" % template_name


    def _copy_file(self, orig_path, dest_path, mode=0644, dirmode=750):
        real_orig_path = config['source_path'] + '/' + orig_path
        real_dest_path = config['source_path'] + '/' + dest_path
        try:
            os.makedirs(os.dirname(real_dest_path), dirmode)
        except: OSError
            pass
        shutil.copy(real_orig_path, real_dest_path)
        os.chmod(real_dest_path, mode)

    
    def _write_file(self, path, mode=0644, dirmode=750):
        real_path = config['source_path'] + '/' + path
        try:
            os.makedirs(os.dirname(real_path), dirmode)
        except: OSError
            pass
        real_file = open(real_path, 'w')
        real_file.write(self.template_content)
        real_file.close()
        os.chmod(real_path, mode)


class ControlGenerator(FileGenerator):
    """ Generate debian/control file from gcs/info file.
    """
    def activate(self):
        """ Generate debian/control file

        Steps:

        1) Obtain control template
        2) Set template properties (using tags) from gcs/info file.
        3) Write debian/control file
        """
        self.set_template_content('control_template')

        self.__set_name()
        self.__set_author()
        self.__set_predepends()
        self.__set_provides()
        self.__set_depends()
        self.__set_recommends()
        self.__set_suggests()
        self.__set_conflicts()
        self.__set_replaces()
        self.__set_section()
        self.__set_priority()
        self.__set_descriptions()

        self._write_file('debian/control')


    def __set_name(self):
        name = config['info']['name']
        newcontent = self.template_content.replace('<NAME>', name)
        self.template_content = newcontent


    def __set_author(self):
        author = config['info']['author']
        newcontent = self.template_content.replace('<MANTAINER>', author)
        self.template_content = newcontent


    def __set_predepends(self):
        predepends = self.__parse_list('/gcs/predepends')
        newcontent = self.template_content.replace('<PREDEPENDS>', predepends)
        self.template_content = newcontent


    def __set_depends(self):
        depends = self.__parse_list('/gcs/depends')
        newcontent = self.template_content.replace('<DEPENDS>', depends)
        self.template_content = newcontent


    def __set_recommends(self):
        recommends = self.__parse_list('/gcs/recommends')
        newcontent = self.template_content.replace('<RECOMMENDS>', recommends)
        self.template_content = newcontent


    def __set_suggests(self):
        suggests = self.__parse_list('/gcs/suggests')
        newcontent = self.template_content.replace('<SUGGESTS>', suggests)
        self.template_content = newcontent


    def __set_conflicts(self):
        conflicts = self.__parse_list('/gcs/conflicts')
        newcontent = self.template_content.replace('<CONFLICTS>', conflicts)
        self.template_content = newcontent


    def __set_replaces(self):
        replaces = self.__parse_list('/gcs/replaces')
        newcontent = self.template_content.replace('<REPLACES>', replaces)
        self.template_content = newcontent


    def __set_provides(self):
        provides = self.__parse_list('/gcs/provides')
        newcontent = self.template_content.replace('<PROVIDES>', provides)
        self.template_content = newcontent


    def __set_section(self):
        section = config['info']['section']
        newcontent = self.template_content.replace('<SECTION>', section)
        self.template_content = newcontent

    def __set_priority(self):
        priority = config['info']['priority']
        newcontent = self.template_content.replace('<PRIORITY>', priority)
        self.template_content = newcontent

    def __set_descriptions(self):
        shortdesc = config['info']['shortdesc']
        longdesc = config['info']['longdesc']
        newcontent = self.template_content.replace('<SHORTDESC>', shortdesc)
        newcontent = newcontent.replace('<LONGDESC>', longdesc)
        self.template_content = newcontent

    def __parse_list(self, file):
        try:
            items_list = open(config['source_path'] + file).readlines()
        except IOError:
            #print "No existe el fichero %s" % file
            return ''
    
        new_items = []
        for item in items_list:
            item = item.strip()
            if not item or item.startswith('#'):
                continue
            name_and_version = item.split()

            item_string = name_and_version[0]
            if len(name_and_version) == 2:
                version = name_and_version[1].lstrip("(").rstrip(")")
                item_string += " (%s)" % version

            new_items.append(item_string)

        items = ', '.join(new_items)
        return items



class RulesGenerator(FileGenerator):
    """ Generates debian/rules.

    Generates debian/rules file based on "newfiles_skel" 
    and "conffiles_skel" directories, and "newfiles" file.
    """

    def __init__(self):
        self.dhinstall_list = []
        self.copy_list = []
        self.dirs = []
        FileGenerator.__init__(self)


    def activate(self):
        self.set_template_content('rules_template')

        self.__process_newfiles()
        self.__process_skel('newfiles_skel')
        self.__process_skel('conffiles_skel')
        self.__write_rules_file()


    def __process_newfiles(self):
        """ Process "newfiles" file looking for files to install.
        """
        if os.path.isfile(config['source_path'] + '/gcs/newfiles'):
            newfiles_lines = open(config['source_path'] + '/gcs/newfiles').readlines()
    
            for line in newfiles_lines:
                line = line.strip()
                line_tuple = line.split()
                if (len(line_tuple) != 2) or line.startswith('#'):
                    continue
    
                self.__add_dhinstall(*line_tuple)


    def __process_skel(self, skel_name):
        """ Process skel_name directory recursively.

        Process skel_name directory recursively 
        looking for files to install.
        """ 
        orig_stuff_len = len(config['source_path'] + '/')
        dest_stuff_len = len(config['source_path'] + '/gcs/' + \
                skel_name + '/')

        def set_dhinstall(arg, dirname, file_names):
            if not '/.svn' in dirname:
                dir_to_add = dirname[dest_stuff_len - 1:]
                if dir_to_add:
                    self.dirs.append(dirname[dest_stuff_len - 1:])    

            for fname in file_names:
                base_path = dirname + os.sep + fname
                orig_path = base_path[orig_stuff_len:]
                dest_path = base_path[dest_stuff_len:]

                if (not '/.svn' in orig_path) and\
                        os.path.isfile(orig_path):
                    dest_path = os.path.dirname(dest_path)
                    if skel_name == "conffiles_skel":
                        dest_path = os.path.join(config['diverts_basepath'], dest_path)
                    self.__add_dhinstall(orig_path, dest_path)
                elif os.path.islink(orig_path):
                    dest_path = os.path.dirname(dest_path)
                    self.__add_copy(orig_path, dest_path)

        os.path.walk(config['source_path'] + '/gcs/' + skel_name, 
                set_dhinstall, None)


    def __write_rules_file(self):
        copy_content = '\n'.join(self.copy_list)
        newcontent = self.template_content.replace('<DHINSTALL_SLOT>', 
                copy_content)
        self.template_content = newcontent

        self._write_file('debian/rules', 0755)

        # write debian/install file
        install_file = open(config['source_path'] + '/debian/install', 'w')
        install_file.write('\n'.join(self.dhinstall_list))
        install_file.close()

        # write debian/dirs file
        dirs_file = open(config['source_path'] + '/debian/dirs', 'w')
        dirs_file.write('\n'.join(self.dirs))
        dirs_file.close()


    def __add_dhinstall(self, orig_path, dest_path):
        if not dest_path:
            return
        #dest_path = os.path.dirname(dest_path)
        command = ''
	    # If we aren't working with config files or we are working with them but has the appropiate
	    # extension fill the command
        if not ('gcs/conffiles_skel/' in orig_path) or orig_path.endswith(config['config_extension']):
            command = orig_path + " " + dest_path

        if command:
            self.dhinstall_list.append(command)


    def __add_copy(self, orig_path, dest_path):
        if not dest_path:
            return
        #dest_path = os.path.dirname(dest_path)
        command = ''
	    # If we aren't working with config files or we are working with them but has the appropiate
	    # extension fill the command
        if not ('gcs/conffiles_skel/' in orig_path) or orig_path.endswith(config['config_extension']):
            dest_path = os.path.join('debian', config['info']['name'], dest_path)
            command = '\tcp -d "%s" "%s"' % (orig_path, dest_path)

        if command:
            self.copy_list.append(command)



class ChangelogGenerator(FileGenerator):

    def __init__(self):
        try:
            self.actual_content = open(config['source_path'] + \
                '/gcs/changelog').read()
            self.changelog_exists = True
        except Exception:
            self.actual_content = ''
            self.changelog_exists = False

        FileGenerator.__init__(self)


    def activate(self):
        if self.__is_new_version():
            self.set_template_content('changelog_template')

            self.__set_basic_info()
            self.__set_changes()

            self.template_content += '\n\n' + self.actual_content
            self._write_file('gcs/changelog')
            self._write_file('debian/changelog')
        elif self.changelog_exists:
            self._copy_file('gcs/changelog', 'debian/changelog')


    def __set_basic_info(self):
        info = config['info']
        newcontent = self.template_content.replace('<NAME>',
                info['name'])
        newcontent = newcontent.replace('<VERSION>', 
                str(info['version']))
        newcontent = newcontent.replace('<DISTRIB>', 
                os.popen('lsb_release -cs').read()[:-1])
        newcontent = newcontent.replace('<AUTHOR>', 
                info['author'])
        newcontent = newcontent.replace('<DATE>',
                email.Utils.formatdate(None,True)) 

        self.template_content = newcontent


    def __set_changes(self):
        changes_str = ''
        if not config['info']['changes']: 
            config['info']['changes'] = ['No changes']
        for change in config['info']['changes']:
            changes_str += '  * %s\n' % change

        newcontent = self.template_content.replace('<CHANGES>',
                changes_str)
        self.template_content = newcontent


    def __is_new_version(self):
        """ Check if there is a new version of package.
        """
        content = None
        try:
            content = open('gcs/changelog').readlines()
        except:
            pass
        
        if not content: return True

        old_version = re.findall('\((.*)\)', content[0])[0]
        new_version = str(config['info']['version'])

        if old_version == new_version:
            return False
        else:
            return True

class PrePostGenerator(FileGenerator):
    """<abstract>
    """

    def __init__(self):
        FileGenerator.__init__(self)
        self.scripts = []

        # Params for derivated classes.
        self.template_name = ''
        self.file_path = ''
        self.divert_content = ''
        self.scripts_path = ''

        # Default DebConf slot for all derivated classes
        self.debconf_content = '''
## Source debconf library.
. /usr/share/debconf/confmodule
'''


    def activate(self):
        self.set_template_content(self.template_name)
        initial_content = self.template_content
        initial_content = initial_content.replace('<DEBCONF_SLOT>', '')
        initial_content = initial_content.replace('<DIVERT_SLOT>', '')
        initial_content = initial_content.replace('<SCRIPTS_SLOT>', '')
        
        self._set_debconf()
        self._set_divert()
        self._set_install_scripts()

        if initial_content != self.template_content:
            self._write_file(self.file_path, 0755)
        else:
            try:
                os.remove(config['source_path'] + '/' + self.file_path)
            except:
                pass


    def _set_debconf(self):
        newcontent = self.template_content.replace('<DEBCONF_SLOT>', 
               self.debconf_content)
        self.template_content = newcontent


    def _set_divert(self):
        newcontent = self.template_content.replace('<DIVERT_SLOT>', 
               self.divert_content)
        self.template_content = newcontent


    def _set_install_scripts(self):
        scripts_part = ScriptsPart(config['source_path'] + \
                '/' + self.scripts_path)

        scripts_content = scripts_part.get_scripts_content()
        newcontent = self.template_content.replace('<SCRIPTS_SLOT>',
                scripts_content)
        self.template_content = newcontent



class PreInstGenerator(PrePostGenerator):

    def __init__(self):
        PrePostGenerator.__init__(self)

        self.template_name = 'preinst_template'
        self.file_path = 'debian/preinst'
        self.scripts_path = 'gcs/install_scripts/pre/'



class PostInstGenerator(PrePostGenerator):

    def __init__(self):
        PrePostGenerator.__init__(self)

        self.template_name = 'postinst_template'
        self.file_path = 'debian/postinst'
        self.divert_content = DivertPart().get_postinst_content()
        self.scripts_path = 'gcs/install_scripts/pos/'



class PreRmGenerator(PrePostGenerator):

    def __init__(self):
        PrePostGenerator.__init__(self)

        self.template_name = 'prerm_template'
        self.file_path = 'debian/prerm'
        self.divert_content = DivertPart().get_prerm_content()
        self.scripts_path = 'gcs/remove_scripts/pre/'



class PostRmGenerator(PrePostGenerator):

    def __init__(self):
        PrePostGenerator.__init__(self)

        self.template_name = 'postrm_template'
        self.file_path = 'debian/postrm'
        self.scripts_path = 'gcs/remove_scripts/pos/'
        self.debconf_content += '''
if [ "$1" = "purge" ]; then
    # Remove my changes to the db.
    db_purge
fi
'''



class CompatGenerator(FileGenerator):

    def activate(self):
        self.set_template_content('compat_template')
        self._write_file('debian/compat')



class SourceFormatGenerator(FileGenerator):

    def activate(self):
        self.set_template_content('sourceformat_template')
        self._write_file('debian/source/format')



class ConfigGenerator(FileGenerator):
    """ Generate debian/config file from configuration, if it exists
    """
    def __init__(self):
        self.dbinput_list = []
        FileGenerator.__init__(self)

    def __set_debconf_questions(self):
        for question in config['questions']:
            self.dbinput_list.append('db_input critical %s || true' % question['Template'])
        dbinput_content = '\n'.join(self.dbinput_list)
        newcontent = self.template_content.replace('<DBINPUT_SLOT>', dbinput_content)
        self.template_content = newcontent

    def activate(self):
        """ Generate debian/config file

        Steps:

        1) Obtain control template
        2) Set template content from configuration.
        3) Write debian/config file
        """
        self.set_template_content('config_template')
        initial_content = self.template_content
        initial_content = initial_content.replace('<DBINPUT_SLOT>', '')
        
        # Allow custom configuration scripts
        if os.path.exists(config['source_path'] + '/gcs/install_scripts/config'):
            self._copy_file('gcs/install_scripts/config', 'debian/config', 0755)
            pass

        self.__set_debconf_questions()

        if initial_content != self.template_content:
            self._write_file('debian/config')
        else:
            try:
                os.remove(config['source_path'] + '/config')
            except:
                pass


class TemplatesGenerator(FileGenerator):
    """ Generate debian/templates file
    """
    def __init__(self):
        FileGenerator.__init__(self)
        self.template_keys = ( 'Template', 'Type', 'Description' )


    def _gen_template_content(self):
        for question in config['questions']:
            for key in self.template_keys: 
                value = question[key].replace("\n", "\n  ")
                value = re.sub(r'\n  $', '', value)
                self.template_content += key + ': ' + value + "\n"
            self.template_content += "\n"


    def activate(self):
        initial_content = self.template_content

        self._gen_template_content()

        if initial_content != self.template_content:
            self._write_file('debian/templates')
        else:
            try:
                os.remove(config['source_path'] + '/templates')
            except:
                pass



class CopyrightGenerator(FileGenerator):

    def activate(self):
        self.set_template_content('copyright_template')

        self.__set_author()

        self._write_file('debian/copyright')


    def __set_author(self):
        from datetime import date
        today = date.today()
        author = "Copyright %s, %s" % (today.year, config['info']['author'])
        newcontent = self.template_content.replace('<AUTHOR>', author)
        self.template_content = newcontent
