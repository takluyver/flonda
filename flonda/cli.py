import argparse
import pathlib
import subprocess
import sys

from . import __version__
from .flonda import PackageBuilder

DEFAULT_PYTHON = ['{}.{}'.format(*sys.version_info[:2])]
DEFAULT_PLATFORMS = ['linux-64', 'linux-32', 'osx-64', 'win-64', 'win-32']

def main(argv=None):
    ap = argparse.ArgumentParser(prog='flonda')
    ap.add_argument('--version', action='version', version='flonda '+__version__)
    ap.add_argument('--pythons', help='Comma separated Python versions to build for')
    ap.add_argument('--platforms', help='Comma separated conda platforms to build for')
    ap.add_argument('--ini-file', type=pathlib.Path, default='flit.ini')
    ap.add_argument('--dist-dir', type=pathlib.Path)
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    parser_build = subparsers.add_parser('build',
         help='Build conda packages')
    parser_publish = subparsers.add_parser('publish',
         help='Build conda packages & publish to anaconda.org')

    args = ap.parse_args(argv)

    if args.pythons:
        pythons = args.pythons.split(',')
    else:
        pythons = DEFAULT_PYTHON

    if args.platforms:
        platforms = args.platforms.split(',')
    else:
        platforms = DEFAULT_PLATFORMS

    if args.dist_dir:
        dist_dir = args.dist_dir
    else:
        dist_dir = args.ini_file.parent / 'dist'

    if args.subcmd == 'build':
        build_multi(args.ini_file, dist_dir, pythons, platforms)
    elif args.subcmd == 'publish':
        files = build_multi(args.ini_file, dist_dir, pythons, platforms)
        publish_packages(files)
    else:
        ap.print_help()
        sys.exit(1)


def build_multi(ini_path, dist_dir, pythons, platforms):
    built_packages = []

    for plat in platforms:
        try:
            (dist_dir / plat).mkdir(parents=True)
        except FileExistsError:
            pass

        platform, bitness = plat.split('-')
        for py in pythons:
            pb = PackageBuilder(ini_path, py, platform, bitness)
            # TODO: Build numbers aren't always 0
            filename = '{}-{}-py{}_0.tar.bz2'.format(
                pb.metadata.name, pb.metadata.version, py.replace('.', ''))
            pkg_path = dist_dir / plat / filename
            with pkg_path.open('wb') as f:
                pb.build(f)

            built_packages.append(pkg_path)

    # The filename should be the same for all of them
    filename = '{}-{}-*.tar.bz2'.format(pb.metadata.name, pb.metadata.version)
    print("Packages are now in", dist_dir / '*' / filename)
    return built_packages

def publish_packages(package_files):
    print("Uploading {} files to anaconda.org...".format(len(package_files)))
    subprocess.run(['anaconda', 'upload'] + package_files, check=True)
