#!venv/bin/python3
"""Tool to handle all projects in the elements SDK."""
import argparse
import subprocess
import os
import logging
import yaml


_FORMAT = "%(asctime)s - %(message)s"
ZEPHYR_SDK_VERSION = "0.12.0"
VIVADO_PATH = "/opt/xilinx/Vivado/2019.2/bin/"

def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r') as stream:
            return list(yaml.load_all(stream, Loader=yaml.FullLoader))
    except yaml.YAMLError as exc:
        raise SystemExit(exc)
    except FileNotFoundError as exc:
        raise SystemExit(exc)
    raise SystemExit("Unable to open {}".format(path))


def parse_args():
    """Parses all arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help='Enables debug output')

    subparsers = parser.add_subparsers(help='Elements commands')

    parser_compile = subparsers.add_parser('compile', help='Compiles the firmware')
    parser_compile.set_defaults(func=compile)
    parser_compile.add_argument('board', help="Name of the board")
    parser_compile.add_argument('application', help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_generate = subparsers.add_parser('generate', help='Generates the MCU')
    parser_generate.set_defaults(func=generate)
    parser_generate.add_argument('soc', help="Name of the SOC")

    parser_sim = subparsers.add_parser('simulate', help='Simulates the design')
    parser_sim.set_defaults(func=sim)
    parser_sim.add_argument('board', help="Name of the board")
    parser_sim.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
                            help="Choose between differen toolchains.")
    parser_sim.add_argument('-synthesized', action='store_true',
                            help="Simulate an already syntheized design")

    parser_syn = subparsers.add_parser('synthesize', help='Synthesizes the design')
    parser_syn.set_defaults(func=syn)
    parser_syn.add_argument('board', help="Name of the board")
    parser_syn.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'cadence'],
                            help="Choose between differen toolchains.")

    parser_flash = subparsers.add_parser('flash', help='Flashes parts of the SDK')
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('board', help="Name of the board")
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi', 'memory'],
                              help="Destination of the bitstream or firmware")

    parser_debug = subparsers.add_parser('debug', help='Debugs the firmware with GDB.')
    parser_debug.set_defaults(func=debug)

    parser_test = subparsers.add_parser('test', help='Tests the SDK')
    parser_test.set_defaults(func=test)
    parser_test.add_argument('-zibal', action='store_true', help="Run all Zibal tests")

    return parser.parse_args()


def compile(args, env, cwd):
    """Command to compile a Zephyr binary for a board and application."""
    force = "always" if args.f else "auto"
    board = args.board.replace('-', '').lower()
    command = "west build -p {} -b {} -d ./build/zephyr/ {}".format(force, board,
                                                                    args.application)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def generate(args, env, cwd):
    """Command to generate a Microcontroller design for a SOC."""
    subprocess.run("mkdir -p build/zibal/".split(' '), env=env, cwd=cwd,
                   stdout=subprocess.DEVNULL, check=True)

    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}'.format(args.soc)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)

    xilinx_cwd = os.path.join(cwd, "eda/Xilinx/sim")
    for index in range(0, 4):
        cmd = "ln -sf ../../../../build/zibal/{0}.v_toplevel_system_onChipRam_ram_symbol{1}.bin " \
                  "{0}.v_toplevel_system_onChipRam_ram_symbol{1}.bin".format(args.soc, index)
        logging.debug(cmd)
        subprocess.run(cmd.split(' '), env=env, cwd=xilinx_cwd, stdout=subprocess.DEVNULL,
                       check=True)

    xilinx_cwd = os.path.join(cwd, "eda/Xilinx/syn")
    for index in range(0, 4):
        cmd = "ln -sf ../../../../build/zibal/{0}.v_toplevel_system_onChipRam_ram_symbol{1}.bin " \
                  "{0}.v_toplevel_system_onChipRam_ram_symbol{1}.bin".format(args.soc, index)
        logging.debug(cmd)
        subprocess.run(cmd.split(' '), env=env, cwd=xilinx_cwd, stdout=subprocess.DEVNULL,
                       check=True)


def sim(args, env, cwd):
    """Command to simulate a SOC on a virtual board."""
    name = args.board.replace('-', '')
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))[0]
    if not 'common' in board:
        raise SystemExit("No common definitions in board {}".format(args.board))
    common = board.get('common')

    if args.toolchain == 'oss':
        oss_cwd = os.path.join(cwd, "zibal/eda/OSS")
        build_cwd = os.path.join(cwd, "build/zibal")
        top_rep = common.get('top', '').replace('-', '')
        command = "iverilog -Wall -g2009 {0}.v ../testbenches/{1}.sv ../../../build/zibal/{2}.v " \
                  " -I../testbenches -o ../../../build/zibal/{3}.out".format(common.get('top', ''),
                                                                  common.get('testbench', ''),
                                                                  common.get('SOC', ''),
                                                                  top_rep)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=oss_cwd, check=True)
        command = "vvp -l{0}.log {0}.out".format(top_rep)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True)
        command = "gtkwave {0}.vcd".format(top_rep)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True)
    if args.toolchain == 'xilinx':
        if not 'xilinx' in board:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))
        env['BOARD'] = args.board
        env['BOARD_NAME'] = name
        env['SOC'] = common.get('SOC', '')
        env['TOP'] = common.get('top', '')
        env['TOP_NAME'] = common.get('top', '').replace('-', '')
        env['TESTBENCH'] = common.get('testbench', '')
        env['TESTBENCH_NAME'] = common.get('testbench', '').replace('-', '')
        env['PART'] = board['xilinx'].get('part', '')

        xilinx_cwd = os.path.join(cwd, "zibal/eda/Xilinx/sim".format(
            "syn" if args.synthesized else "sim"))
        command = "vivado -mode tcl -source tcl/sim.tcl -log ./output/logs/vivado.log " \
                  "-journal ./output/logs/vivado.jou"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)


def syn(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    name = args.board.replace('-', '')
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))[0]
    if not 'common' in board:
        raise SystemExit("No common definitions in board {}".format(args.board))
    common = board.get('common')
    env['BOARD'] = args.board
    env['BOARD_NAME'] = name
    env['SOC'] = common.get('SOC', '')
    env['TOP'] = common.get('top', '')
    env['TOP_NAME'] = common.get('top', '').replace('-', '')
    env['TESTBENCH'] = common.get('testbench', '')
    env['TESTBENCH_NAME'] = common.get('testbench', '').replace('-', '')

    if args.toolchain == 'xilinx':
        if not 'xilinx' in board:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))
        env['PART'] = board['xilinx'].get('part', '')

        xilinx_cwd = os.path.join(cwd, "zibal/eda/Xilinx/syn")
        command = "vivado -mode tcl -source tcl/syn.tcl -log ./output/logs/vivado.log " \
                  "-journal ./output/logs/vivado.jou"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)

    if args.toolchain == 'cadence':
        if not 'cadence' in board:
            raise SystemExit("No cadence definitions in board {}".format(args.board))
        env['PROCESS'] = board['cadence'].get('process', '')

        cadence_cwd = os.path.join(cwd, "zibal/eda/cadence")
        command = "genus -f tcl/frontend.tcl -log ./output/logs/"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)


def flash(args, env, cwd):
    """Command to flash the design to a fpga or spi nor."""
    openocd_cwd = os.path.join(cwd, "openocd")
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))[0]
    if args.destination == 'memory':
        debug(args, env, cwd, type_="flash")
    else:
        if not args.destination in board.get('destinations', {}):
            raise SystemExit("Unsupported destination {} for board {}".format(args.destination,
                                                                              args.board))
        name = args.board.replace('-', '')
        destination = board['destinations'][args.destination]
        command = ['src/openocd', '-c', 'set BOARD {}'.format(name),
                   '-c', 'set BASE_PATH {}'.format(env['ELEMENTS_BASE']),
                   '-f', '../zibal/openocd/flash_{}.cfg'.format(destination)]
        logging.debug(command)
        subprocess.run(command, env=env, cwd=openocd_cwd, check=True)


def debug(args, env, cwd, type_="debug"):
    """Command to debug the firmware with GDB"""
    openocd_cwd = os.path.join(cwd, "openocd")
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML ../build/zibal/VexRiscv.yaml',
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/hydrogen.cfg']
    logging.debug(command)
    openocd_process = subprocess.Popen(command, env=env, cwd=openocd_cwd,
                                       stdout=subprocess.DEVNULL)

    toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
    command = ['{}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb'.format(toolchain),
               '-x', 'zibal/gdb/{}.cmd'.format(type_),
               'build/zephyr/zephyr/zephyr.elf']
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)

    openocd_process.terminate()


def test(args, env, cwd):
    """Command to run tests in the different projects."""
    if args.zibal:
        zibal_cwd = os.path.join(cwd, "zibal")
        command = "sbt test"
        logging.debug(command)
        result = subprocess.run(command.split(' '), env=env, cwd=zibal_cwd, check=True)
        if result == 1:
            raise SystemExit("Zibal failed")


def environment():
    """Reads the OS environment and adds extra variables for Elements."""
    env = os.environ.copy()
    base = os.path.dirname(os.path.abspath(__file__))
    env['ELEMENTS_BASE'] = base
    env['ZEPHYR_TOOLCHAIN_VARIANT'] = 'zephyr'
    env['ZEPHYR_SDK_INSTALL_DIR'] = os.path.join(base, 'zephyr-sdk-{}'.format(ZEPHYR_SDK_VERSION))
    env['PATH'] += os.pathsep + VIVADO_PATH
    env['VIVADO_PATH'] = VIVADO_PATH
    return env


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
