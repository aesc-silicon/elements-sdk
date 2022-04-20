#!venv/bin/python3
"""Tool to handle all ASIC projects in the elements SDK."""
# pylint: disable=invalid-name

import os
import logging
import datetime
import glob

from base import prepare_build, environment, open_board, get_soc_name, get_board_name, parse_args
from base import prepare, compile_, generate, functional_simulation
from base import command

_FORMAT = "%(asctime)s - %(message)s"


def parse_asic_args(subparsers, _):
    """Parses all ASIC related arguments."""
    parser_simulate = subparsers.add_parser('simulate', help="Simulates a design")
    parser_simulate.set_defaults(func=simulate)
    parser_simulate.add_argument('--type', default="functional",
                                 choices=['function', 'gate-level'])

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

#    parser_pack = subparsers.add_parser('pack', help="Pack the design")
#    parser_pack.set_defaults(func=pack)

    parser_test = subparsers.add_parser('test', help="Tests the kit")
    parser_test.set_defaults(func=test)
    parser_test.add_argument('case', help="Name of the test case")


def simulate(args, env, cwd):
    """Command to simulate a SOC on a virtual board."""
    if args.type == "functional":
        functional_simulation(args, env, cwd)

    if args.type == "gate-level":
        soc = get_soc_name(args.soc)
        board = get_board_name(args.board)
        board_data = open_board(args.board)
        top = f"{board}Top"
        env['SOC'] = soc
        env['BOARD'] = board
        env['TOP'] = top

        env['PDK'] = board_data['cadence']['pdk']
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Cadence/tcl/")
        cadence_cwd = os.path.join(cwd, f"build/{soc}/{board}/cadence/sim")

        for binary in glob.glob(f"build/{soc}/{board}/fpl/*.rom"):
            command(f"ln -sf {binary} .", env, cadence_cwd)

        command("./sim.sh", env, env['TCL_PATH'])


def synthesize(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    env['SOC'] = soc
    env['BOARD'] = board
    env['EFFORT'] = args.effort

    if args.toolchain == 'cadence':
        if not 'cadence' in board_data:
            raise SystemExit(f"No cadence definitions in board {args.board}")

        now = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        env['DATETIME'] = now
        env['PROCESS'] = str(board_data['cadence']['process'])
        env['PDK'] = board_data['cadence']['pdk']

        logs_path = os.path.join(cwd, f"build/{soc}/{board}/cadence/synthesize", now, "logs")
        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command(f"genus -f tcl/synthesize.tcl -log {logs_path}", env, cadence_cwd)

        command("rm -rf latest", env,
                os.path.join(cwd, f"build/{soc}/{board}/cadence/synthesize"))
        command(f"ln -sfT {now} latest", env,
                os.path.join(cwd, f"build/{soc}/{board}/cadence/synthesize"))


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
            raise SystemExit(f"No cadence definitions in board {args.board}")

        now = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        env['DATETIME'] = now
        env['PROCESS'] = str(board_data['cadence']['process'])
        env['PDK'] = board_data['cadence']['pdk']

        logs_path = os.path.join(cwd, f"build/{soc}/{board}/cadence/synthesize", now, "logs")
        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command(f"innovus -files tcl/place.tcl -log {logs_path}", env, cadence_cwd)

        command("rm -rf latest", env,
                os.path.join(cwd, f"build/{soc}/{board}/cadence/place"))
        command(f"ln -sfT {now} latest", env,
                os.path.join(cwd, f"build/{soc}/{board}/cadence/place"))


#def pack(args, env, cwd):
#    """Command to pack a layout into a library."""


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

    command(f"sbt \"runMain zibal.soc.{soc.lower()}.{board}Board generated {args.case}\"", env,
            os.path.join(cwd, "zibal"))


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
