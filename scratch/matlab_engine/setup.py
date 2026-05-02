#Copyright 2014-2025 MathWorks, Inc.

import warnings

# Usage of pip is encouraged, but the "setup.py install" workflow is still supported, so 
# this script suppresses related warnings.
warnings.filterwarnings('ignore', message='.*Use build and pip and other standards-based tools.*')

# We start with setuptools. If that fails, we back off to distutils. If that fails, we issue
# an error.

firstExceptionMessage = ''
secondExceptionMessage = ''

try:
    from setuptools import setup
    from setuptools.command.build_py import build_py
except Exception as firstE:
    firstExceptionMessage = str(firstE)

if firstExceptionMessage:
    try:
        # Currently, we suppress warnings about deprecation of distutils. Once we
        # no longer support any Python versions that provide distutils, we can
        # remove the line.
        warnings.filterwarnings('ignore', message='.*distutils package is deprecated.*', 
            category=DeprecationWarning)
        from distutils.core import setup
        from distutils.command.build_py import build_py
    except Exception as secondE:
        secondExceptionMessage = str(secondE)

if secondExceptionMessage:
    raise EnvironmentError("Installation failed. Install setuptools using 'python -m pip install setuptools', then try again.")
    
import os
import sys
import platform

# UPDATE_IF_PYTHON_VERSION_ADDED_OR_REMOVED : search for this string in codebase 
# when support for a Python version must be added or removed
_supported_versions = ['3.7', '3.9', '3.10', '3.11', '3.12', '3.13']
_ver = sys.version_info
_version = '{0}.{1}'.format(_ver[0], _ver[1])
newer_than_supported = _ver[1] > 13

# Check if current version is not supported and not newer than highest supported version
if not _version in _supported_versions and not newer_than_supported:
    raise EnvironmentError('MATLAB Engine for Python supports Python version'
                        ' 3.9, 3.10, 3.11, 3.12, and 3.13, but your version of Python '
                        'is %s' % _version)
elif newer_than_supported:
    # warning for versions newer than supported ones
    warnings.warn('MATLAB Engine for Python supports Python version'
                    ' 3.9, 3.10, 3.11, 3.12, and 3.13, but your version of Python '
                    'is %s' % _version)

_dist = "dist"
_matlab_package = "matlab"
_engine_package = "engine"
_arch_filename = "_arch.txt"
_py_arch = platform.architecture()
_system = platform.system()
_py_bitness =_py_arch[0]

class BuildEngine(build_py):

    @staticmethod
    def _get_arch_from_system(system): 
        if system == 'Windows':
            return 'win64'
        elif system == 'Linux':
            return 'glnxa64'
        elif system == 'Darwin':
            # determine if ARM or Intel Mac machine
            if platform.mac_ver()[-1] == 'arm64':
                return 'maca64'
            return 'maci64'

    @staticmethod
    def _bin_dir_w_arch_exists(bin_dir, arch):
        ret = os.access(os.path.join(bin_dir, arch), os.F_OK)
        return ret

    @staticmethod
    def _find_arch(predicate):
        _bin_dir = predicate
        _arch = None
        _arch_bitness = {"glnxa64": "64bit", "maci64": "64bit",
                         "win32": "32bit", "win64": "64bit", "maca64": "64bit"}
        _arch_from_system = BuildEngine._get_arch_from_system(_system)
        if BuildEngine._bin_dir_w_arch_exists(_bin_dir, _arch_from_system):
            _arch = _arch_from_system
        if _arch is None:
            if _system == 'Darwin':
                if _arch_from_system == 'maci64':
                    _alt_arch = 'maca64'
                else:
                    _alt_arch = 'maci64'
                if BuildEngine._bin_dir_w_arch_exists(_bin_dir, _alt_arch):
                    raise EnvironmentError(f'MATLAB installation in {_bin_dir} is {_alt_arch}, but Python interpreter is {_arch_from_system}. Reinstall MATLAB or use a different Python interpreter.') 
            raise EnvironmentError('The installation of MATLAB is corrupted.  '
                                   'Please reinstall MATLAB or contact '
                                   'Technical Support for assistance.')

        if _py_bitness != _arch_bitness[_arch]:
            raise EnvironmentError('%s Python does not work with %s MATLAB. '
                                   'Please check your version of Python' %
                                   (_py_bitness, _arch_bitness[_arch]))
        return _arch

    def _generate_arch_file(self, target_dir):
        _arch_file_path = os.path.join(target_dir, _arch_filename)
        _cwd = os.getcwd()
        matlab_root = r'E:\MySoftwares\Softwares\MATLAB\R2026a'
        _bin_dir = os.path.join(matlab_root, 'bin')
        _engine_dir = os.path.join(_cwd, _dist, _matlab_package, _engine_package)
        _extern_bin_dir = os.path.join(matlab_root, 'extern', 'bin')
        _arch = self._find_arch(_bin_dir)
        _bin_dir = os.path.join(_bin_dir, _arch)
        _engine_dir = os.path.join(_engine_dir, _arch)
        _extern_bin_dir = os.path.join(_extern_bin_dir, _arch)
        try:
            _arch_file = open(_arch_file_path, 'w')
            _arch_file.write(_arch + os.linesep)
            _arch_file.write(_bin_dir + os.linesep)
            _arch_file.write(_engine_dir + os.linesep)
            _arch_file.write(_extern_bin_dir + os.linesep)
            _arch_file.close()
        except IOError:
            raise EnvironmentError('You do not have write permission '
                                   'in %s ' % target_dir)

    def run(self):
        build_py.run(self)
        _target_dir = os.path.join(self.build_lib, _matlab_package, _engine_package)
        self._generate_arch_file(_target_dir)


if __name__ == '__main__':

    setup(
        name="matlabengine",
        version="26.1",
        description='A module to call MATLAB from Python',
        author='MathWorks',
        url='https://www.mathworks.com/',
        platforms=['Linux', 'Windows', 'macOS'],
        package_dir={'': 'dist'},
        packages=['matlab','matlab.engine'],
        cmdclass={'build_py': BuildEngine}
    )
