#!venv/bin/python3
"""Tool to handle all FPGA projects in the elements SDK."""

import argparse
import subprocess
import os
import logging
import glob

from base import prepare_build, environment, open_board, get_soc_name, get_board_name
from base import init, clean, socs, boards, prepare, compile_, generate, flash, debug


_FORMAT = "%(asctime)s - %(message)s"


def parse_args():
    """Parses all arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help="Enables debug output")

    subparsers = parser.add_subparsers(help="Elements commands")

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

    parser_prepare = subparsers.add_parser('prepare', help="Prepares all file for a kit")
    parser_prepare.set_defaults(func=prepare)
    parser_prepare.add_argument('soc', help="Name of a SOC")
    parser_prepare.add_argument('board', help="Name of a board")

    parser_compile = subparsers.add_parser('compile', help="Compiles a firmwares")
    parser_compile.set_defaults(func=compile_)
    parser_compile.add_argument('soc', help="Name of a SOC")
    parser_compile.add_argument('board', help="Name of a board")
    parser_compile.add_argument('type', choices=['zephyr', 'bootrom', 'menuconfig'],
                                help="Type of firmware")
    parser_compile.add_argument('application', nargs='?', default="",
                                help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_generate = subparsers.add_parser('generate', help="Generates a SOC")
    parser_generate.set_defaults(func=generate)
    parser_generate.add_argument('soc', help="Name of a SOC")
    parser_generate.add_argument('board', help="Name of a board")

    parser_simulate = subparsers.add_parser('simulate', help="Simulates a design")
    parser_simulate.set_defaults(func=simulate)
    parser_simulate.add_argument('soc', help="Name of a SOC")
    parser_simulate.add_argument('board', help="Name of a board")

    parser_synthesize = subparsers.add_parser('synthesize', help="Synthesizes the design")
    parser_synthesize.set_defaults(func=synthesize)
    parser_synthesize.add_argument('soc', help="Name of a SOC")
    parser_synthesize.add_argument('board', help="Name of a board")
    parser_synthesize.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
                                   help="Choose between different toolchains.")

    parser_build = subparsers.add_parser('build', help="Run the complete flow to generate a "
                                                       "bitstream file.")
    parser_build.set_defaults(func=build)
    parser_build.add_argument('soc', help="Name of a SOC")
    parser_build.add_argument('board', help="Name of a board")
    parser_build.add_argument('application', nargs='?', default="",
                              help="Name of an application")
    parser_build.add_argument('-f', action='store_true', help="Force build")
    parser_build.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
                              help="Choose between different toolchains.")

    parser_flash = subparsers.add_parser('flash', help="Flashes parts of the SDK")
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('soc', help="Name of a SOC")
    parser_flash.add_argument('board', help="Name of a board")
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi', 'memory'],
                              help="Destination of the bitstream or firmware")

    parser_debug = subparsers.add_parser('debug', help="Debugs a firmware with GDB.")
    parser_debug.set_defaults(func=debug)
    parser_debug.add_argument('soc', help="Name of a SOC")
    parser_debug.add_argument('board', help="Name of a board")

    parser_test = subparsers.add_parser('test', help="Tests the kit")
    parser_test.set_defaults(func=test)
    parser_test.add_argument('soc', help="Name of a SOC")
    parser_test.add_argument('board', help="Name of a board")
    parser_test.add_argument('case', help="Name of the test case")

    return parser.parse_args()


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
    command = ['sbt', 'runMain zibal.soc.{}.{}Board {} boot'.format(soc.lower(), board,
                                                                        "generated")]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=zibal_cwd, check=True)

    binary_files = glob.glob("zibal/{}Top.v*bin".format(board))
    for binary_file in binary_files:
        os.remove(binary_file)

    command = "gtkwave boot.vcd"
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True,
                   stdin=subprocess.PIPE)


def synthesize(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    if not os.path.exists(f"build/{soc}/{board}/zibal/{board}Top.v"):
        raise SystemExit("No SOC design found!\n"
                         f" Run \"./elements.py generate {args.soc} {args.board}\" before.")

    if args.toolchain == 'xilinx':
        if 'xilinx' not in board_data:
            raise SystemExit(f"No xilinx definitions in board {args.board}")
        env['PART'] = board_data['xilinx']['part']
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Xilinx/vivado/syn")

        xilinx_cwd = os.path.join(cwd, f"build/{soc}/{board}/vivado/syn")
        command = "vivado -mode batch -source ../../../../../zibal/eda/Xilinx/vivado/syn/syn.tcl" \
                  " -log ./logs/vivado.log -journal ./logs/vivado.jou"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)
    if args.toolchain == 'oss':
        if not 'xilinx' in board_data:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))
        env['PART'] = board_data['xilinx']['part']
        env['PART'] = board_data['xilinx']['part'].lower()
        env['DEVICE'] = "{}_test".format(board_data['xilinx']['device'])

        symbiflow_cwd = os.path.join(cwd, "zibal/eda/Xilinx/symbiflow")
        command = "make clean"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=symbiflow_cwd, check=True)

        command = "./syn.sh"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=symbiflow_cwd, check=True)


def build(args, env, cwd):
    """Command to compile, generate and synthesize a board."""
    prepare(args, env, cwd)
    board_data = open_board(args.board)
    for firmware in board_data.get('firmwares', []):
        args.type = firmware
        compile_(args, env, cwd)
    generate(args, env, cwd)
    synthesize(args, env, cwd)


def test(args, env, cwd):
    """Command to run tests in different projects for a kit."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    zibal_cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}.{}Board generated {}'.format(soc.lower(), board,
                                                                             args.case)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=zibal_cwd, check=True)

    binary_files = glob.glob("zibal/{}Top.v*bin".format(board))
    for binary_file in binary_files:
        os.remove(binary_file)


def main():
    """Main function."""
    args = parse_args()
    if args.v:
        logging.basicConfig(format=_FORMAT, level=logging.DEBUG)
    env = environment()
    if hasattr(args, 'soc') and hasattr(args, 'board'):
        prepare_build(args)
    cwd = os.path.dirname(os.path.realpath(__file__))
    if hasattr(args, 'func'):
        args.func(args, env, cwd)


main()
