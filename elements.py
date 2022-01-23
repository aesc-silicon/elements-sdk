#!venv/bin/python3
"""Tool to handle common commands in the elements SDK."""
# pylint: disable=invalid-name

import argparse
import subprocess
import os
import logging
import shutil

from base import environment, get_socs, get_boards_for_soc, _RELEASE


_FORMAT = "%(asctime)s - %(message)s"


def parse_args():
    """Parses all common related arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help="Enables debug output")

    subparsers = parser.add_subparsers(help="Elements commands", dest='command')
    subparsers.required = True

    parser_init = subparsers.add_parser('init', help="Initialise the SDK")
    parser_init.set_defaults(func=init)
    parser_init.add_argument('--manifest', help="Repo manifest")
    parser_init.add_argument('-f', action='store_true', help="Force init")

    parser_clean = subparsers.add_parser('clean', help="Cleans all builds")
    parser_clean.set_defaults(func=clean)

    parser_socs = subparsers.add_parser('socs', help="Lists all available SOCs.")
    parser_socs.set_defaults(func=socs)

    parser_boards = subparsers.add_parser('boards', help="Lists all available boards for a SOC.")
    parser_boards.set_defaults(func=boards)
    parser_boards.add_argument('soc', help="Name of a SOC")

    return parser.parse_args()


def init(args, env, cwd):
    """Clones all repositories, installs and/or build all packages."""
    if args.f:
        command = "rm -rf .repo"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    if os.path.exists(".repo"):
        raise SystemExit("Repo exists! Either the SDK is already initialized or force init.")

    if not os.path.exists("./repo"):
        command = "curl https://storage.googleapis.com/git-repo-downloads/repo-1"
        logging.debug(command)
        proc = subprocess.run(command.split(' '), cwd=cwd, check=True, stdout=subprocess.PIPE)
        with open("./repo", "w", encoding='UTF-8') as text_file:
            text_file.write(proc.stdout.decode())

        command = "chmod a+x ./repo"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "python3 ./repo init -u https://github.com/aesc-silicon/elements-manifest.git" \
              " -m {}".format(args.manifest if args.manifest else _RELEASE + ".xml")
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "python3 ./repo sync"
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "./.init.sh {}".format(env['ZEPHYR_SDK_VERSION'])
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    print("Initialization finished")


def clean(args, env, cwd):  # pylint: disable=unused-argument
    """Cleans all build by remove the build directory."""
    if os.path.exists("build/"):
        shutil.rmtree("build/")
    else:
        print("Nothing to do!")


def socs(args, env, cwd):  # pylint: disable=unused-argument
    """Lists all available SOCs by existing SOC files."""
    for soc in get_socs():
        print(f"{soc}")


def boards(args, env, cwd):  # pylint: disable=unused-argument
    """Lists all available boards for a SOC."""
    for board in get_boards_for_soc(args.soc):
        print(f"{board}")


def main():
    """Main function."""
    args = parse_args()
    if args.v:
        logging.basicConfig(format=_FORMAT, level=logging.DEBUG)
    env = environment()
    cwd = os.path.dirname(os.path.realpath(__file__))
    if hasattr(args, 'func'):
        args.func(args, env, cwd)

main()
