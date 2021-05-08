#!venv/bin/python3
"""Tool to handle all projects in the elements SDK."""
import argparse
import subprocess
import os
import logging
import time
import shutil
import glob
import yaml


_FORMAT = "%(asctime)s - %(message)s"


def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r') as stream:
            return yaml.load(stream, Loader=yaml.FullLoader)
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

    parser_clean = subparsers.add_parser('clean', help='Cleans all builds')
    parser_clean.set_defaults(func=clean)

    parser_compile = subparsers.add_parser('compile', help='Compiles the firmware')
    parser_compile.set_defaults(func=compile_)
    parser_compile.add_argument('board', help="Name of the board")
    parser_compile.add_argument('application', help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_generate = subparsers.add_parser('generate', help='Generates the MCU')
    parser_generate.set_defaults(func=generate)
    parser_generate.add_argument('board', help="Name of the board")

    parser_sim = subparsers.add_parser('simulate', help='Simulates the design')
    parser_sim.set_defaults(func=sim)
    parser_sim.add_argument('board', help="Name of the board")
    parser_sim.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss', 'cadence'],
                            help="Choose between different toolchains.")
    parser_sim.add_argument('--source', default="generated",
                            choices=['generated', 'synthesized', 'placed'],
                            help="Choose between different design sources.")

    parser_syn = subparsers.add_parser('synthesize', help='Synthesizes the design')
    parser_syn.set_defaults(func=syn)
    parser_syn.add_argument('board', help="Name of the board")
    parser_syn.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
                            help="Choose between different toolchains.")

    parser_map = subparsers.add_parser('map', help='Map the design')
    parser_map.set_defaults(func=map_)
    parser_map.add_argument('board', help="Name of the board")
    parser_map.add_argument('--toolchain', default="cadence", choices=['cadence'],
                            help="Choose between different toolchains.")
    parser_map.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                            help="Choose between different mapping effort modes.")

    parser_place = subparsers.add_parser('place', help='Place and route the design')
    parser_place.set_defaults(func=place)
    parser_place.add_argument('board', help="Name of the board")
    parser_place.add_argument('--toolchain', default="cadence", choices=['cadence'],
                            help="Choose between different toolchains.")
    parser_place.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                            help="Choose between different placeping effort modes.")

    parser_build = subparsers.add_parser('build', help='Run the complete flow to generate a '
                                                       'bitstream file.')
    parser_build.set_defaults(func=build)
    parser_build.add_argument('board', help="Name of the board")
    parser_build.add_argument('application', help="Name of the application")
    parser_build.add_argument('-f', action='store_true', help="Force build")
    parser_build.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
                            help="Choose between different toolchains.")

    parser_flash = subparsers.add_parser('flash', help='Flashes parts of the SDK')
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('board', help="Name of the board")
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi', 'memory'],
                              help="Destination of the bitstream or firmware")

    parser_debug = subparsers.add_parser('debug', help='Debugs the firmware with GDB.')
    parser_debug.set_defaults(func=debug)
    parser_debug.add_argument('board', help="Name of the board")

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


def clean(args, env, cwd):  # pylint: disable=unused-argument
    """Cleans all build by remove the build directory."""
    if os.path.exists("build/"):
        shutil.rmtree("build/")
    else:
        print("Nothing to do!")


def compile_(args, env, cwd):
    """Command to compile a Zephyr binary for a board and application."""
    force = "always" if args.f else "auto"
    board = args.board.replace('-', '').lower()
    output = "./build/{}/zephyr/".format(args.board)
    command = "west build -p {} -b {} -d {} {}".format(force, board, output, args.application)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def generate(args, env, cwd):
    """Command to generate a Microcontroller design for a SOC."""
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    boot_source = board.get('boot_source', "")
    soc = board.get('SOC', {'name': None}).get('name')

    path = "build/{}/zephyr/zephyr/zephyr.bin".format(args.board)
    if boot_source == "memory" and not os.path.exists(path):
        raise SystemExit("No Zephyr binary found. "
                         "Run \"./elements.py compile <board> <app>\" before.")

    env['BOARD'] = args.board
    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}'.format(soc)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)


def sim(args, env, cwd):
    """Command to simulate a SOC on a virtual board."""
    name = args.board.replace('-', '')
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    soc = board.get('SOC', {'name': None}).get('name')
    top = board.get('SOC', {'top': None}).get('top')
    if not os.path.exists("build/{}/zibal/{}.v".format(args.board, soc)):
        raise SystemExit("No SOC design found. Run \"./elements.py generate {}\" before.".format(
                         args.board))


    if args.toolchain == 'oss':
        if args.source == "synthesized" or args.source == "placed":
            raise SystemExit("Source type is not supported for the OSS toolchain.")

        oss_cwd = os.path.join(cwd, "zibal/eda/OSS")
        build_cwd = os.path.join(cwd, "build/{}/zibal".format(args.board))
        top_rep = top.replace('-', '')
        command = "iverilog -Wall -g2009 -DVCD=\"{2}/{0}.vcd\" -I../testbenches " \
                  " {0}.v ../testbenches/{1}.sv {2}/{3}.v " \
                  " -o {2}/{4}.out".format(top, board.get('testbench', ''),
                                           build_cwd, soc, top_rep, args.board)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=oss_cwd, check=True)
        command = "vvp -l{0}.log {0}.out".format(top_rep)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True)
        command = "gtkwave {0}.vcd".format(top_rep)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True)
    if args.toolchain == 'xilinx':
        if args.source == "placed":
            raise SystemExit("Source type is not supported for the Xilinx toolchain.")

        if not 'xilinx' in board:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))

        sim_type = "syn" if args.source == "synthesized" else "sim"

        env['BOARD'] = args.board
        env['BOARD_NAME'] = name
        env['SOC'] = soc
        env['TOP'] = top
        env['TOP_NAME'] = top.replace('-', '')
        env['TESTBENCH'] = board.get('testbench', '')
        env['TESTBENCH_NAME'] = board.get('testbench', '').replace('-', '')
        env['PART'] = board['xilinx'].get('part', '')
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Xilinx/vivado/{}".format(sim_type))

        xilinx_cwd = os.path.join(cwd, "build/{}/vivado/{}".format(args.board, sim_type))
        binaries = glob.glob("build/{}/zibal/{}.v_*bin".format(args.board, soc))
        for binary in binaries:
            subprocess.run("ln -sf {} .".format(os.path.join("../../../..", binary)).split(' '),
                           env=env, cwd=xilinx_cwd, stdout=subprocess.DEVNULL, check=True)

        command = "vivado -mode batch -source ../../../../zibal/eda/Xilinx/vivado/{}/sim.tcl " \
                  " -log ./logs/vivado.log -journal ./logs/vivado.jou".format(sim_type)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)

    if args.toolchain == 'cadence':
        if args.source == "synthesized":
            raise SystemExit("Source type is not supported for the Cadence toolchain.")

        env['BOARD'] = args.board
        env['BOARD_NAME'] = name
        env['SOC'] = soc
        env['TOP'] = top
        env['TOP_NAME'] = top.replace('-', '')
        env['TESTBENCH'] = board.get('testbench', '')
        env['TESTBENCH_NAME'] = board.get('testbench', '').replace('-', '')
        env['PDK'] = board['cadence'].get('pdk', '')
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Cadence/tcl/")
        env['SIM_TYPE'] = args.source
        cadence_cwd = os.path.join(cwd, "build/{}/cadence/sim".format(args.board))

        command = "../../../../zibal/eda/Cadence/tcl/sim.sh"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)


def syn(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    name = args.board.replace('-', '')
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    soc = board.get('SOC', {'name': None}).get('name')
    top = board.get('SOC', {'top': None}).get('top')
    env['BOARD'] = args.board
    env['BOARD_NAME'] = name
    env['SOC'] = soc
    env['TOP'] = top
    env['TOP_NAME'] = top.replace('-', '')
    env['TESTBENCH'] = board.get('testbench', '')
    env['TESTBENCH_NAME'] = board.get('testbench', '').replace('-', '')

    if not os.path.exists("build/{}/zibal/{}.v".format(args.board, soc)):
        raise SystemExit("No SOC design found. Run \"./elements.py generate {}\" before.".format(
                         soc))

    if args.toolchain == 'xilinx':
        if not 'xilinx' in board:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))
        env['PART'] = board['xilinx'].get('part', '')
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Xilinx/vivado/syn")

        subprocess.run("mkdir -p build/{}/vivado/syn/logs".format(args.board).split(' '), env=env,
                       cwd=cwd, stdout=subprocess.DEVNULL, check=True)

        xilinx_cwd = os.path.join(cwd, "build/{}/vivado/syn".format(args.board))
        command = "vivado -mode batch -source ../../../../zibal/eda/Xilinx/vivado/syn/syn.tcl " \
                  " -log ./logs/vivado.log -journal ./logs/vivado.jou"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)
    if args.toolchain == 'oss':
        if not 'xilinx' in board:
            raise SystemExit("No xilinx definitions in board {}".format(args.board))
        env['PART'] = board['xilinx'].get('part', '').lower()
        env['DEVICE'] = "{}_test".format(board['xilinx'].get('device', ''))

        subprocess.run("mkdir -p build/{}/symbiflow/logs".format(args.board).split(' '), env=env,
                       cwd=cwd, stdout=subprocess.DEVNULL, check=True)

        symbiflow_cwd = os.path.join(cwd, "zibal/eda/Xilinx/symbiflow")
        command = "./syn.sh"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=symbiflow_cwd, check=True)

def map_(args, env, cwd):
    """Command to map a SOC for a board."""
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    name = args.board.replace('-', '')
    soc = board.get('SOC', {'name': None}).get('name')
    top = board.get('SOC', {'top': None}).get('top')
    env['BOARD'] = args.board
    env['BOARD_NAME'] = name
    env['SOC'] = soc
    env['TOP'] = top
    env['TOP_NAME'] = top.replace('-', '')
    env['TESTBENCH'] = board.get('testbench', '')
    env['TESTBENCH_NAME'] = board.get('testbench', '').replace('-', '')
    env['PROCESS'] = str(board['cadence'].get('process', ''))
    env['PDK'] = board['cadence'].get('pdk', '')
    env['EFFORT'] = args.effort

    if args.toolchain == 'cadence':
        if not 'cadence' in board:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command = "genus -f tcl/map.tcl " \
                  "-log ./../../../build/{}/cadence/map/logs/".format(args.board)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)

        command = "cp build/{0}/cadence/map/latest/{1}.v build/{0}/cadence/map".format(args.board,                                                                                         soc)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def place(args, env, cwd):
    """Command to place and route a SOC for a board."""
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    name = args.board.replace('-', '')
    soc = board.get('SOC', {'name': None}).get('name')
    top = board.get('SOC', {'top': None}).get('top')
    env['BOARD'] = args.board
    env['BOARD_NAME'] = name
    env['SOC'] = soc
    env['TOP'] = top
    env['TOP_NAME'] = top.replace('-', '')
    env['TESTBENCH'] = board.get('testbench', '')
    env['TESTBENCH_NAME'] = board.get('testbench', '').replace('-', '')
    env['PROCESS'] = str(board['cadence'].get('process', ''))
    env['PDK'] = board['cadence'].get('pdk', '')
    env['EFFORT'] = args.effort

    if args.toolchain == 'cadence':
        if not 'cadence' in board:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command = "innovus -files tcl/place.tcl " \
                  "-log ./../../../build/{}/cadence/place/logs/".format(args.board)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)

        command = "cp build/{0}/cadence/place/latest/{1}_final.v " \
                  "build/{0}/cadence/place/{1}.v".format(args.board, top)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def build(args, env, cwd):
    """Command to compile, generate and synthesize a board."""
    compile_(args, env, cwd)
    generate(args, env, cwd)
    syn(args, env, cwd)


def flash(args, env, cwd):
    """Command to flash the design to a fpga or spi nor."""
    openocd_cwd = os.path.join(cwd, "openocd")
    board = open_yaml("zibal/eda/boards/{}.yaml".format(args.board))
    top = board.get('SOC', {'top': None}).get('top')
    if args.destination == 'memory':
        debug(args, env, cwd, type_="flash")
    else:
        if not args.destination in board.get('flash_bridge', {}):
            raise SystemExit("Unsupported destination {} for board {}".format(args.destination,
                                                                              args.board))

        top_rep = top.replace('-', '')

        vivado_bit = os.path.exists("build/{}/vivado/syn/{}.bit".format(args.board, top_rep))
        symbiflow_bit = os.path.exists("build/{}/symbiflow/{}.bit".format(args.board, top_rep))
        if not (vivado_bit or symbiflow_bit):
            raise SystemExit("No bitstream found. "
                             "Run \"./elements.py synthesize {}\" before.".format(args.board))

        bitstream_origin = "symbiflow" if symbiflow_bit else "vivado"
        destination = board['flash_bridge'][args.destination]
        transport = board['flash_bridge']["transport"]
        command = ['src/openocd', '-c', 'set BOARD {}'.format(args.board),
                   '-c', 'set TOP {}'.format(top_rep),
                   '-c', 'set BASE_PATH {}'.format(env['ELEMENTS_BASE']),
                   '-c', 'set TRANSPORT {}'.format(transport),
                   '-c', 'set BITSTREAM_ORIGIN {}'.format(bitstream_origin),
                   '-f', '../zibal/openocd/flash_{}.cfg'.format(destination)]
        logging.debug(command)
        subprocess.run(command, env=env, cwd=openocd_cwd, check=True)


def debug(args, env, cwd, type_="debug"):
    """Command to debug the firmware with GDB"""
    if not os.path.exists("build/{}/zephyr/zephyr/zephyr.elf".format(args.board)):
        raise SystemExit("No Zephyr elf found. "
                         "Run \"./elements.py compile <board> <app>\" before.")

    openocd_cwd = os.path.join(cwd, "openocd")
    yaml_path = "../build/{}/zibal/VexRiscv.yaml".format(args.board)
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML {}'.format(yaml_path),
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/hydrogen.cfg']
    logging.debug(command)
    openocd_process = subprocess.Popen(command, env=env, cwd=openocd_cwd,
                                       stdout=subprocess.DEVNULL)

    toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
    command = ['{}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb'.format(toolchain),
               '-x', 'zibal/gdb/{}.cmd'.format(type_),
               'build/{}/zephyr/zephyr/zephyr.elf'.format(args.board)]
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
    env['FPGA_FAM'] = "xc7"
    env['INSTALL_DIR'] = os.path.join(base, 'symbiflow')
    env['PATH'] += os.pathsep + vivado_path
    env['PATH'] += os.pathsep + os.path.join(base, 'symbiflow/xc7/install/bin')
    env['VIVADO_PATH'] = vivado_path
    env['PDK_BASE'] = get_variable(env, localenv, 'PDK_BASE')
    env['IHP_TECH'] = os.path.join(get_variable(env, localenv, 'PDK_BASE'), 'tech')
    return env


def prepare(args):
    """Prepares the build directory."""
    path = "build/{}".format(args.board)
    if not os.path.exists(path):
        subprocess.run("mkdir -p {}".format(path).split(' '), stdout=subprocess.DEVNULL, check=True)
    if not os.path.exists(os.path.join(path, "zibal")):
        subprocess.run("mkdir -p {}".format(os.path.join(path, "zibal")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)
    if not os.path.exists(os.path.join(path, "vivado")):
        subprocess.run("mkdir -p {}".format(os.path.join(path, "vivado/sim/logs")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)
        subprocess.run("mkdir -p {}".format(os.path.join(path, "vivado/syn/logs")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)
    if not os.path.exists(os.path.join(path, "cadence")):
        subprocess.run("mkdir -p {}".format(os.path.join(path, "cadence/map")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)
        subprocess.run("mkdir -p {}".format(os.path.join(path, "cadence/place")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)
        subprocess.run("mkdir -p {}".format(os.path.join(path, "cadence/sim")).split(' '),
                       stdout=subprocess.DEVNULL, check=True)


def main():
    """Main function."""
    args = parse_args()
    if args.v:
        logging.basicConfig(format=_FORMAT, level=logging.DEBUG)
    env = environment()
    if hasattr(args, 'board'):
        prepare(args)
    cwd = os.path.dirname(os.path.realpath(__file__))
    if hasattr(args, 'func'):
        args.func(args, env, cwd)


main()
