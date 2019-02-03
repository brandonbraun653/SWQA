# **********************************************************************************
#   FileName:
#       cppcheck.py
#   Description:
#       Utilizes CPPCheck to lint the Thor repo for errors
#   Usage Examples:
#       N/A
#
#   2019 | Brandon Braun | brandonbraun653@gmail.com
# **********************************************************************************

import os
import json

from typing import Dict
from subprocess import Popen, PIPE


class CppCheckConfig:

    def __init__(self, name, config):
        """
        Initialize the CPPCheckConfig class

        :param name: Name of the configuration
        :type name: str

        :param config: Configuration information
        :type config: dict
        """
        self._name = name
        self._raw_config = config
        self._results_dir = ""
        self._cpp_working_dir = ""

    def build_command(self):
        """
        Builds the full command used to run cppcheck on this configuration

        :return: cppcheck command arguments
        :rtype: str
        """
        command = ' '.join([self.threads, self.output_format, self.message_level, self.defines, self.un_defines,
                            self.standard, self.platform, self.error_exit_code, self.includes, self.excludes,
                            self.directories, self.files])

        suppression_list = self.generate_suppression_list()

        if suppression_list:
            command = ' '.join(['--suppressions-list={}'.format(suppression_list), command])

        if self.add_ons:
            command = ' '.join(['--dump', command])

        if self.options:
            command = ' '.join([self.options, command])

        return command

    def generate_suppression_list(self):
        """
        Using the loaded configuration file, generates a suppression list text file that
        can be used to prevent certain errors from showing up in the output.

        :return: Relative path to the suppression list
        :rtype: str or None
        """
        act_out_file = None
        config_suppression = self._raw_config['suppression']

        if config_suppression:
            # Resolve full path to the output file
            act_out_file = os.path.join(self._results_dir, '{}_suppression_list.txt'.format(self.name))

            out_format = '{}:{}:{}'
            with open(act_out_file, 'w') as f:
                for item in config_suppression:
                    # Make sure paths that include environment variables are valid
                    filename = os.path.expandvars(item['filename'])
                    if not os.path.isfile(filename):
                        raise RuntimeError("Invalid path: {}".format(filename))

                    # Fill in the output template
                    output_string = out_format.format(item['error_id'],
                                                      filename,
                                                      item['line'])

                    # Filter the string for the character sequence that would occur if 'filename' was blank.
                    # Returns the original string if the sequence is not present
                    output_string = output_string.split('::', 1)[0]

                    # Trim up the string should 'line' not be present
                    output_string = output_string.strip(':')

                    # Write the comment first, then the actual exclusion command
                    f.write('// {}\n'.format(item['comment']))
                    f.write(output_string + '\n\n')

        return os.path.relpath(act_out_file, os.path.commonprefix([os.getcwd(), act_out_file]))

    @property
    def cpp_working_dir(self):
        return self._cpp_working_dir

    @cpp_working_dir.setter
    def cpp_working_dir(self, val):
        self._cpp_working_dir = val
        self._results_dir = os.path.join(self._cpp_working_dir, self.output_dir, self.name)
        if not os.path.isdir(self._results_dir):
            os.makedirs(self._results_dir)

    @property
    def results_dir(self):
        return self._results_dir

    @property
    def name(self):
        return self._name

    @property
    def files(self):
        """
        Loads the files to be run through cppcheck and formats them. This expects to
        be relative to the working directory of the eventual cppcheck call.

        :return: Formatted files
        :rtype:str
        """
        return ' '.join(self._raw_config['files'])

    @property
    def directories(self):
        """
        Loads the directories from the config file into a cppcheck formatted string. This
        expects to be relative to the working directory of the eventual cppcheck call.

        :return: Formatted directories
        :rtype: str
        """
        return ' '.join(self._raw_config['directories'])

    @property
    def includes(self):
        """
        Converts the loaded config file include settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted string of includes
        :rtype: str
        """
        individual_includes = []

        for include_file in self._raw_config['includes']:
            individual_includes.append('-I{}'.format(include_file))

        combined_includes = ' '.join(individual_includes)
        return combined_includes

    @property
    def excludes(self):
        """
        Converts the loaded config file exclude settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted string of excludes
        :rtype: str
        """
        individual_excludes = []

        for exclude_file in self._raw_config['excludes']:
            individual_excludes.append('-i{}'.format(exclude_file))

        combined_excludes = ' '.join(individual_excludes)
        return combined_excludes

    @property
    def defines(self):
        """
        Converts the loaded config file define settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted string of defines
        :rtype: str
        """
        individual_defines = []

        for define in self._raw_config['defines']:
            individual_defines.append('-D{}'.format(define))

        combined_defines = ' '.join(individual_defines)
        return combined_defines.strip()

    @property
    def un_defines(self):
        """
        Converts the loaded config file un-define settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted string of un-defines
        :rtype: str
        """
        individual_un_defines = []

        for un_define in self._raw_config['un_defines']:
            individual_un_defines.append('-i{}'.format(un_define))

        combined_un_defines = ' '.join(individual_un_defines)
        return combined_un_defines

    @property
    def message_level(self):
        """
        Converts the loaded config file message level settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted command string of message levels
        :rtype: str
        """
        levels = ','.join(self._raw_config['message_level'])
        return '--enable={}'.format(levels.strip())

    @property
    def add_ons(self):
        return self._raw_config['add_ons']

    @property
    def threads(self):
        """
        Converts the loaded config file thread settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted command string to use the proper number of threads
        :rtype: str
        """
        return '-j {}'.format(self._raw_config['threads'])

    @property
    def output_format(self):
        """
        Converts the loaded config file output format settings into a string suitable
        to be used on the cppcheck command line call.

        :return: Formatted command string to use the proper template
        :rtype: str
        """
        # Allow the user template to take priority
        if self._raw_config['output_template']:
            command = '--template=\"{}\"'.format(self._raw_config['output_template'])
        else:
            command = '--template=\"{}\"'.format(self._raw_config['output_format'])
        return command

    @property
    def output_dir(self):
        return self._raw_config['output_dir']

    @property
    def options(self):
        return ' '.join(self._raw_config['options'])

    @property
    def use_xml(self):
        raise NotImplementedError

    @property
    def standard(self):
        return '--std={}'.format(self._raw_config['standard'])

    @property
    def platform(self):
        return '--platform={}'.format(self._raw_config['platform'])

    @property
    def error_exit_code(self):
        return '--error-exitcode={}'.format(self._raw_config['on_error_exit_code'])


class CppCheck:
    def __init__(self, exe_path):
        """
        Initialize the CPPCheck class

        :param exe_path: Absolute path to cppcheck.exe
        :type exe_path: str
        """
        self._cppcheck_exe = exe_path
        self._version = 'unknown'

        self.configurations = {}  # type: Dict[str, CppCheckConfig]

    @staticmethod
    def _execute_shell_cmd(command, working_dir=None):
        """
        Executes a given command on the default system shell, printing the output to console

        :param command: The command to be executed
        :type command: str

        :param working_dir: Absolute path to the location to execute from
        :type working_dir: str

        :return: Output of the process
        :rtype: int, str, str
        """
        actual_working_dir = os.getcwd() if working_dir is None else working_dir
        process = Popen(command, stdout=PIPE, stderr=PIPE, cwd=actual_working_dir, shell=True)

        output, error = process.communicate()
        return_code = process.returncode

        return return_code, output.decode('utf-8'), error.decode('utf-8')

    @property
    def version(self):
        """
        Get's the current version of cppcheck

        :return: version string
        :rtype: str
        """
        # Expected output: b'Cppcheck <ver> <some qualifier>'
        _, cmd_output = self.cppcheck('--version', working_dir=os.getcwd())

        if cmd_output:
            formatted = cmd_output[0].split()
            self._version = float(formatted[1])
        else:
            self._version = 'unknown'

        return self._version

    def cppcheck(self, cmd, working_dir):
        """
        Execute a cppcheck command

        :param cmd: The command to be executed
        :type cmd: str

        :param working_dir: Which directory to run the command from
        :type working_dir: str

        :return: Command return info
        :rtype: int, list of str, list of str
        """
        full_command = '{} {}'.format(self._cppcheck_exe, cmd)
        print("Running CPPCheck, please be patient...")
        print(full_command)
        _rc, _out, _err = self._execute_shell_cmd(command=full_command, working_dir=working_dir)
        print("Return Code: {}".format(_rc))
        print("CPPCheck Complete")
        return _rc, _out, _err

    def load_config(self, file):
        """
        Loads a json file that contains our custom cppcheck config information

        :param file: Absolute path to the configuration file
        :type file: str

        :return: None
        """
        with open(file) as f:
            raw_json = json.load(f)
            for config in raw_json:
                self.configurations[config] = CppCheckConfig(name=config, config=raw_json[config])

    def execute(self, config, working_dir):
        """
        Run cppcheck on a loaded configuration

        :param config: Which configuration to run the checks on
        :type config: str

        :param working_dir: Where to execute the command from
        :type working_dir: str

        :return: Process return code
        :rtype: int
        """
        return_code = 0

        if config in self.configurations.keys():
            cfg = self.configurations[config]
            cfg.cpp_working_dir = working_dir
            command = cfg.build_command()

            return_code, out, err = self.cppcheck(cmd=command, working_dir=working_dir)

            # Write stdout to file
            log_file = os.path.join(cfg.results_dir, '{}_log.txt'.format(cfg.name))
            with open(log_file, 'w') as f:
                f.write(out)

            # Write stderr to file
            err_file = os.path.join(cfg.results_dir, '{}_err.txt'.format(cfg.name))
            with open(err_file, 'w') as f:
                f.write(err)

        return return_code

    def run_add_on(self, dump_file, which):
        raise NotImplementedError
