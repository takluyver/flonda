from pathlib import Path
from flit import inifile, common
from enum import Enum
import tarfile
from io import BytesIO

class Platform(Enum):
    linux = 1
    osx = 2
    windows = 3

pkgdir = Path(__file__).parent

class PackageBuilder:
    def __init__(self, ini_path, python_version, platform, bitness):
        self.ini_path = ini_path
        self.ini_info = ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, ini_info)
        self.python_version = python_version
        self.platform = platform
        self.bitness = bitness
        self.files = []
        self.has_prefix_files = []

    def record_file(self, arcname, has_prefix=False):
        self.files.append(arcname)
        if has_prefix:
            self.has_prefix_files.append(arcname)

    def site_packages_path(self):
        if self.platform is Platform.windows:
            return 'Lib/site-packages/'
        else:
            return 'lib/python{}/site-packages/'.format(self.python_version)

    def scripts_path(self):
        if self.platform is Platform.windows:
            return 'Scripts/'
        else:
            return 'bin/'

    def build(self, fileobj):
        with tarfile.open(fileobj=fileobj, mode='w:bz2') as tf:
            self.add_module(tf)
            self.create_scripts(tf)
            #self.write_index(tf)
            self.write_has_prefix_list(tf)
            self.write_files_list(tf)

    def add_module(self, tf):
        src = str(self.module.path)
        dst = self.site_packages_path() + self.module.path.name
        tf.add(src, arcname=dst)

    def _write_script_unix(self, tf, name, contents):
        ti = tarfile.TarInfo(self.scripts_path() + name)
        contents = contents.encode('utf-8')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))
        self.record_file(ti.name)

    def _write_script_windows(self, tf, name, contents):
        self._write_script_unix(tf, name+'-script.py', contents)
        src = str(pkgdir / 'cli-{}.exe'.format(self.bitness))
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
            if self.platform == Platform.windows:
                self._write_script_windows(tf, name, s)
            else:
                self._write_script_unix(tf, name, s)

    def write_index(self, tf):
        raise NotImplementedError

    def write_has_prefix_list(self, tf):
        contents = '\n'.join(self.has_prefix_files).encode('utf-8')
        ti = tarfile.TarInfo('info/has_prefix')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))

    def write_files_list(self, tf):
        contents = '\n'.join(self.files).encode('utf-8')
        ti = tarfile.TarInfo('info/files')
        ti.size = len(contents)
        tf.addfile(ti, BytesIO(contents))

if __name__ == '__main__':
    ini_path = Path('/home/takluyver/Code/astcheck/flit.ini')
    pb = PackageBuilder(ini_path, '3.5', Platform.linux, '64')
    with open('test_pkg.tar.bz2', 'wb') as f:
        pb.build(f)
