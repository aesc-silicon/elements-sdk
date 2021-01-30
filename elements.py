#!venv/bin/python3
"""Tool to handle all projects in the elements SDK."""
import argparse
import subprocess
import os
import logging
import time
import yaml


_FORMAT = "%(asctime)s - %(message)s"


def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r') as stream:
            return list(yaml.load_all(stream, Loader=yaml.FullLoader))
    except yaml.YAMLError as exc:
        raise SystemExit from exc
    except FileNotFoundError as exc:
        raise SystemExit from exc
    raise SystemExit("Unable to open {}".format(path))


def parse_args():
    """Parses all arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help='Enables debug output')

    subparsers = parser.add_subparsers(help='Elements commands')

    parser_init = subparsers.add_parser('init', help='Initialise the SDK')
    parser_init.set_defaults(func=init)
    parser_init.add_argument('--manifest', help="Repo manifest")
    parser_init.add_argument('-f', action='store_true', help="Force init")

    parser_compile = subparsers.add_parser('compile', help='Compiles the firmware')
    parser_compile.set_defaults(func=compile_)
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


def init(args, env, cwd):
    """Clones all repositories, installs and/or build all packages."""
    if args.f:
        command = "rm -rf .repo"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)
    if os.path.exists(".repo"):
        raise SystemExit("Repo exists! Either the SDK is already initialized or force init.")

    command = "repo init -u https://github.com/phytec-labs/elements-manifest.git"
    if args.manifest:
        command = command + " -m {}".format(args.manifest)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "repo sync"
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "./.init.sh {}".format(env['ZEPHYR_SDK_VERSION'])
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    print("Initialization finished")


def compile_(args, env, cwd):
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

        xilinx_cwd = os.path.join(cwd, "zibal/eda/Xilinx/{}".format(
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
        env['PDK'] = board['cadence'].get('pdk', '')

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


def debug(_, env, cwd, type_="debug"):
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
    if type_ == "flash":
        gdb_process = subprocess.Popen(command, env=env, cwd=cwd)
        time.sleep(15)
        gdb_process.terminate()
    else:
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


def get_variable(env, localenv, key):
    """Searchs for a variable in the bash env or in a file env."""
    if key in env:
        return env[key]
    if key in localenv:
        return localenv[key]
    raise SystemExit("Variable {} has no value".format(key))


def environment():
    """Reads the OS environment and adds extra variables for Elements."""
    env = os.environ.copy()
    base = os.path.dirname(os.path.abspath(__file__))
    localenv = {}
    if os.path.exists("env.txt"):
        with open("env.txt", 'r') as stream:
            for line in stream.readlines():
                tmp = line.split('=')
                localenv[tmp[0]] = tmp[1].replace('"', '').replace('\n', '')

    zephyr_sdk_version = get_variable(env, localenv, 'ZEPHYR_SDK_VERSION')
    vivado_path = get_variable(env, localenv, 'VIVADO_PATH')

    env['ELEMENTS_BASE'] = base
    env['ZEPHYR_TOOLCHAIN_VARIANT'] = 'zephyr'
    env['ZEPHYR_SDK_VERSION'] = zephyr_sdk_version
    env['ZEPHYR_SDK_INSTALL_DIR'] = os.path.join(base, 'zephyr-sdk-{}'.format(zephyr_sdk_version))
    env['PATH'] += os.pathsep + vivado_path
    env['VIVADO_PATH'] = vivado_path
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
