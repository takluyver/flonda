import json
import os
from pathlib import Path
import posixpath
from flit import inifile, common
import tarfile
from io import BytesIO

pkgdir = Path(__file__).parent

class PackageBuilder:
    def __init__(self, ini_path, python_version, platform, bitness):
        self.ini_path = ini_path
        self.directory = ini_path.parent
        self.ini_info = ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(ini_info['module'], self.directory)
        self.metadata = common.make_metadata(self.module, ini_info)
        self.python_version = python_version
        self.platform = platform
        assert platform in {'osx', 'linux', 'win'}, platform
        self.bitness = bitness
        assert bitness in {'32', '64'}, bitness
        self.files = []
        self.has_prefix_files = []

    def record_file(self, arcname, has_prefix=False):
        self.files.append(arcname)
        if has_prefix:
            self.has_prefix_files.append(arcname)

    def site_packages_path(self):
        if self.platform == 'win':
            return 'Lib/site-packages/'
        else:
            return 'lib/python{}/site-packages/'.format(self.python_version)

    def scripts_path(self):
        if self.platform == 'win':
            return 'Scripts/'
        else:
            return 'bin/'

    def build(self, fileobj):
        with tarfile.open(fileobj=fileobj, mode='w:bz2') as tf:
            self.add_module(tf)
            self.create_scripts(tf)
            self.write_index(tf)
            self.write_has_prefix_list(tf)
            self.write_files_list(tf)

    def _include(self, path):
        name = os.path.basename(path)
        if (name == '__pycache__') or name.endswith('.pyc'):
            return False
        return True

    def add_module(self, tf):
        if self.module.is_package:
            for dirpath, dirs, files in os.walk(str(self.module.path)):
                reldir = os.path.relpath(dirpath, str(self.directory))
                for f in sorted(files):
                    full_path = os.path.join(dirpath, f)
                    if self._include(full_path):
                        in_archive = posixpath.join(self.site_packages_path(), reldir, f)
                        tf.add(full_path, in_archive)
                        self.record_file(in_archive)

                dirs[:] = [d for d in sorted(dirs) if self._include(d)]
                for d in dirs:
                    full_path = os.path.join(dirpath, d)
                    tf.add(full_path,
                           posixpath.join(self.site_packages_path(), reldir, d),
                           recursive=False)

        else:
            # Module is a single file
            src = str(self.module.path)
            dst = self.site_packages_path() + self.module.path.name
            tf.add(src, arcname=dst)
            self.record_file(dst)

    def _write_script_unix(self, tf, name, contents):
        ti = tarfile.TarInfo(self.scripts_path() + name)
        contents = contents.encode('utf-8')
        ti.size = len(contents)
        ti.mode = 0o755  # Set executable bit
        tf.addfile(ti, BytesIO(contents))
        self.record_file(ti.name, has_prefix=True)

    def _write_script_windows(self, tf, name, contents):
        from win_cli_launchers import find_exe
        self._write_script_unix(tf, name+'-script.py', contents)
        src = find_exe(arch=('x86' if self.bitness == '32' else 'x64'))
        dst = self.scripts_path() + name + '.exe'
        tf.add(src, arcname=dst)
        self.record_file(dst)

    def create_scripts(self, tf):
        for name, (mod, func) in self.ini_info['scripts'].items():
            s = common.script_template.format(
                module=mod, func=func,
                # This is replaced when the package is installed:
                interpreter='/opt/anaconda1anaconda2anaconda3/bin/python',
            )
            if self.platform == 'win':
                self._write_script_windows(tf, name, s)
            else:
                self._write_script_unix(tf, name, s)

    def _find_license(self):
        if self.metadata.license:
            return self.metadata.license

        for cl in self.metadata.classifiers:
            if cl.startswith('License :: OSI Approved :: '):
                return cl[len('License :: OSI Approved :: '):]

        return ''

    def _get_dependencies(self):
        py = ["python {}*".format(self.python_version)]
        cfg = self.ini_info['raw_config']
        if cfg.has_section('x-flonda') and ('requires' in cfg['x-flonda']):
            return py + cfg['x-flonda']['requires'].splitlines()
        else:
            from .requirements import requires_dist_to_conda_requirements
            return py + requires_dist_to_conda_requirements(self.metadata.requires_dist,
                            self.python_version, self.platform, self.bitness)

    def write_index(self, tf):
        a = {
          "arch": ("x86_64" if self.bitness=='64' else 'x86'),
          "build": "py{}_0".format(self.python_version.replace('.', '')),
          "build_number": 0,
          "depends": self._get_dependencies(),
          "license": self._find_license(),
          "name": self.metadata.name,
          "platform": self.platform,
          "subdir": "{}-{}".format(self.platform, self.bitness),
          "version": self.metadata.version,
        }
        contents = json.dumps(a, indent=2, sort_keys=True).encode('utf-8')
        ti = tarfile.TarInfo('info/index.json')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))

    def write_has_prefix_list(self, tf):
        if not self.has_prefix_files:
            return
        contents = '\n'.join(self.has_prefix_files).encode('utf-8')
        ti = tarfile.TarInfo('info/has_prefix')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))

    def write_files_list(self, tf):
        contents = '\n'.join(self.files).encode('utf-8')
        ti = tarfile.TarInfo('info/files')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))

