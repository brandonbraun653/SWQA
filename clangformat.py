# **********************************************************************************
#   FileName:
#       clangformat.py
#
#   Description:
#       Provides routines used in generically processing a project with clang-format
#
#   Usage Examples:
#       N/A
#
#   2019 | Brandon Braun | brandonbraun653@gmail.com
# **********************************************************************************

import os
import glob
import json

from subprocess import Popen, PIPE


class ClangFormatConfig:
    """ Models a configuration used to execute clang-format on a project """

    def __init__(self, config_file):
        """
        Initialize the ClangFormatConfig class

        :param config_file: File that contains the clang format command line options
        :type config_file: str
        """
        with open(config_file) as f:
            self._raw_config = json.load(f)

    def build_file_command(self, file, working_dir):
        """
        Generates command line options for running clang-format on a single file

        :param file: The file to execute formatting on
        :type file: str

        :param working_dir: Directory that file is relative to
        :type working_dir: str

        :return: Formatted command
        :rtype: str
        """
        path = os.path.realpath(os.path.join(working_dir, file))
        return ' '.join([self.inplace, self.style, path])

    def build_directory_command(self, dir_obj, working_dir):
        """
        Generates command line options for running clang-format on all files in
        a given directory.

        :param dir_obj: Directories description from config file. Should have form:
            {
                "path": str,                    # Directory to search through
                "recursive": bool,              # Whether or not to recursively search
                "extensions": list of str       # Valid extensions
            }
        :type dir_obj: dict

        :param working_dir: Directory that all paths in dir_obj are relative to
        :type working_dir: str

        :return: Formatted command
        :rtype: str
        """
        path = os.path.realpath(os.path.join(working_dir, dir_obj['path']))

        # Grab every file under the path that matches the specified extension.
        files = []
        for ext in dir_obj['extensions']:
            recurse = dir_obj['recursive']

            if recurse:
                search_start = os.path.join(path, '**', ext)
            else:
                search_start = os.path.join(path, ext)

            files.extend(glob.glob(search_start, recursive=recurse))

        files = ' '.join(files)
        return ' '.join([self.inplace, self.style, files])

    @property
    def inplace(self):
        if self._raw_config['inplace']:
            return '-i'
        else:
            return ''

    @property
    def style(self):
        return '-style={}'.format(self._raw_config['style'])

    @property
    def files(self):
        return self._raw_config['files']

    @property
    def directories(self):
        return self._raw_config['directories']


class ClangFormatter:
    """ """

    def __init__(self, project_file, working_dir, clang_format_exe=None):
        """
        Initializes the ClangFormatter class

        :param project_file: Path to file that contains our custom clang-format config
        :type project_file: str

        :param working_dir: Root directory from which clang-format should run
        :type working_dir: str

        :param clang_format_exe: Location of the clang format executable
        :type clang_format_exe: str
        """
        self.config = ClangFormatConfig(config_file=project_file)
        self.working_dir = working_dir
        self.project_file_dir = os.path.dirname(project_file)
        self.clang_format_exe = clang_format_exe

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

    def execute(self):
        """
        Runs the clang-formatting operation

        :return: Process return code
        :rtype: int
        """
        template = '{} -verbose {}'

        for file in self.config.files:
            command = template.format(self.clang_format_exe,
                                      self.config.build_file_command(file, working_dir=self.project_file_dir))
            return_code, stdout, stderr = self._execute_shell_cmd(command, working_dir=self.working_dir)

            if stderr:
                print(stderr)
                return return_code

        for directory in self.config.directories:
            files = self.config.build_directory_command(dir_obj=directory, working_dir=self.project_file_dir)
            command = template.format(self.clang_format_exe, files)
            return_code, stdout, stderr = self._execute_shell_cmd(command, working_dir=self.working_dir)

            if stderr:
                print(stderr)
                return return_code

        return 0


    #{
    #  "path": "../Chimera",
    #  "recursive": true,
    #  "extensions": ["*.hpp", "*.cpp"]
    #}