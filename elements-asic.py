#!venv/bin/python3
"""Tool to handle all FPGA projects in the elements SDK."""
# pylint: disable=invalid-name

import subprocess
import os
import logging
import datetime

from base import prepare_build, environment, open_board, get_soc_name, get_board_name, parse_args
from base import prepare, compile_, generate



_FORMAT = "%(asctime)s - %(message)s"


def parse_asic_args(subparsers):
    """Parses all ASIC related arguments."""
    parser_simulate = subparsers.add_parser('simulate', help="Simulates a design")
    parser_simulate.set_defaults(func=simulate)

    parser_synthesize = subparsers.add_parser('synthesize', help="Synthesize the design")
    parser_synthesize.set_defaults(func=synthesize)
    parser_synthesize.add_argument('--toolchain', default="cadence", choices=['cadence'],
                                   help="Choose between different toolchains.")
    parser_synthesize.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                                   help="Choose between different synthesizing effort modes.")

    parser_place = subparsers.add_parser('place', help="Place and route the design")
    parser_place.set_defaults(func=place)
    parser_place.add_argument('--stage', default="save", choices=['init', 'floorplan', 'place',
                                                                  'cts', 'route', 'signoff',
                                                                  'verify', 'save'],
                              help="Define a stage the place and route should stop")
    parser_place.add_argument('--toolchain', default="cadence", choices=['cadence'],
                              help="Choose between different toolchains.")
    parser_place.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                              help="Choose between different placing effort modes.")

    parser_test = subparsers.add_parser('test', help="Tests the kit")
    parser_test.set_defaults(func=test)
    parser_test.add_argument('case', help="Name of the test case")


def simulate(args, env, cwd):
    """Command to simulate a SOC on a virtual board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board
    top = f"{board}Top"

    if not os.path.exists(f"build/{soc}/{board}/zibal/{top}.v"):
        raise SystemExit(f"No SOC design found. Run \"./elements-fpga.py generate {args.soc} "
                         f"{args.board}\" before.")

    build_cwd = os.path.join(cwd, f"build/{soc}/{board}/zibal/{board}Board/")
    zibal_cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}.{}Board {} simulate'.format(soc.lower(), board,
                                                                        "generated")]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=zibal_cwd, check=True)

    command = "gtkwave simulate.vcd"
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True,
                   stdin=subprocess.PIPE)


def synthesize(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    top = f"{board}Top"
    env['SOC'] = soc
    env['BOARD'] = board
    env['EFFORT'] = args.effort

    if args.toolchain == 'cadence':
        if not 'cadence' in board_data:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        now = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        env['DATETIME'] = now
        env['PROCESS'] = str(board_data['cadence']['process'])
        env['PDK'] = board_data['cadence']['pdk']

        logs_path = os.path.join(cwd, f"build/{soc}/{board}/cadence/synthesize", now, "logs")
        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command = "genus -f tcl/synthesize.tcl -log {}".format(logs_path)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)

        command = f"cp build/{soc}/{board}/cadence/synthesize/latest/{top}.v " \
                  f"build/{soc}/{board}/cadence/synthesize"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def place(args, env, cwd):
    """Command to place and route a SOC for a board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    env['SOC'] = soc
    env['BOARD'] = board
    env['EFFORT'] = args.effort
    env['STAGE'] = args.stage


    if args.toolchain == 'cadence':
        if not 'cadence' in board_data:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        now = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        env['DATETIME'] = now
        env['PROCESS'] = str(board_data['cadence']['process'])
        env['PDK'] = board_data['cadence']['pdk']

        logs_path = os.path.join(cwd, f"build/{soc}/{board}cadence/synthesize", now, "logs")
        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command = "innovus -files tcl/place.tcl -log {}".format(logs_path)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)

        command = f"cp build/{soc}/{board}/cadence/place/latest/{soc}_final.v " \
                  f"build/{soc}/{board}/cadence/place/{soc}.v"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def build(args, env, cwd):
    """Command to compile, generate and synthesize a board."""
    prepare(args, env, cwd)
    board_data = open_board(args.board)
    for firmware in board_data.get('firmwares', []):
        args.type = firmware
        compile_(args, env, cwd)
    generate(args, env, cwd)
    synthesize(args, env, cwd)
    place(args, env, cwd)


def test(args, env, cwd):
    """Command to run tests in different projects for a kit."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    if args.type == "software":

        zibal_cwd = os.path.join(cwd, "zibal")
        command = ['sbt', 'runMain zibal.soc.{}.{}Board generated {}'.format(soc.lower(), board,
                                                                             args.case)]
        logging.debug(command)
        subprocess.run(command, env=env, cwd=zibal_cwd, check=True)


def main():
    """Main function."""
    args = parse_args(parse_asic_args)
    if args.v:
        logging.basicConfig(format=_FORMAT, level=logging.DEBUG)
    env = environment()
    if hasattr(args, 'soc') and hasattr(args, 'board'):
        prepare_build(args)
    cwd = os.path.dirname(os.path.realpath(__file__))
    if hasattr(args, 'func'):
        args.func(args, env, cwd)


main()
