#!venv/bin/python3
"""Tool to handle all projects in the elements SDK."""
import subprocess
import os
import logging
import time
import glob
import configparser
import shlex
import argparse
import sys
import yaml
from packaging import version


_FORMAT = "%(asctime)s - %(message)s"
_RELEASE = "v22.1"


class ElementsParser(argparse.ArgumentParser):
    """Parser for the Elements SDK."""
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        if 'soc' in message:
            sys.stderr.write("\nAvailable SOCs:\n")
            for soc in get_socs():
                sys.stderr.write("\t%s\n" % soc)
            sys.exit(2)
        soc = sys.argv[1] if len(sys.argv) > 0 else ""
        if 'board' in message:
            sys.stderr.write("\nAvailable boards for %s:\n" % soc)
            for board in get_boards_for_soc(soc):
                sys.stderr.write("\t%s\n" % board)
            sys.exit(2)
        if 'command' in message:
            self.print_help(sys.stderr)
            sys.exit(2)
        sys.exit(2)


def validate_soc_name(name):
    """Helper to validate a SOC name is type of string and exist."""
    if not isinstance(name, str):
        raise argparse.ArgumentTypeError("SOC name is not a string.")
    if name not in get_socs():
        raise argparse.ArgumentTypeError(f"No SOC with the name {name} available.")
    return name


def validate_board_name(name):
    """Helper to validate a board name is type of string and exist."""
    if not isinstance(name, str):
        raise argparse.ArgumentTypeError("Board name is not a string.")
    if name not in get_boards():
        raise argparse.ArgumentTypeError(f"No Board with the name {name} available.")
    return name


def parse_args(parse_tool_args):
    """Parses all arguments."""
    parser = ElementsParser()
    parser.add_argument('-v', action='store_true', help="Enables debug output")
    parser.add_argument('soc', type=validate_soc_name)
    parser.add_argument('board', type=validate_board_name)

    subparsers = parser.add_subparsers(help="Elements commands", dest='command')
    subparsers.required = True

    parser_prepare = subparsers.add_parser('prepare', help="Prepares all file for a kit")
    parser_prepare.set_defaults(func=prepare)

    parser_compile = subparsers.add_parser('compile', help="Compiles a firmwares")
    parser_compile.set_defaults(func=compile_)
    parser_compile.add_argument('type', choices=['zephyr', 'bootrom', 'menuconfig'],
                                help="Type of firmware")
    parser_compile.add_argument('application', nargs='?', default="",
                                help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_generate = subparsers.add_parser('generate', help="Generates a SOC")
    parser_generate.set_defaults(func=generate)

    parser_flash = subparsers.add_parser('flash', help="Flashes parts of the SDK")
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi', 'memory'],
                              help="Destination of the bitstream or firmware")

    parser_debug = subparsers.add_parser('debug', help="Debugs a firmware with GDB.")
    parser_debug.set_defaults(func=debug)

    parser_benchmark = subparsers.add_parser('benchmark', help="Benchmark tests for a kit")
    parser_benchmark.set_defaults(func=benchmark)

    parse_tool_args(subparsers)

    return parser.parse_args()


def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r', encoding='UTF-8') as stream:
            if version.parse(yaml.__version__) > version.parse("5.1.0"):
                return yaml.load(stream, Loader=yaml.FullLoader)
            return yaml.load(stream)
    except yaml.YAMLError as exc:
        raise SystemExit from exc
    except FileNotFoundError as exc:
        raise SystemExit from exc
    raise SystemExit("Unable to open {}".format(path))


def get_socs():
    """Returns a list of all available SOCs."""
    all_socs = glob.glob("zibal/eda/socs/*yaml")
    return list(map(lambda x: os.path.splitext(os.path.basename(x))[0], all_socs))


def get_boards():
    """Returns a list of all available boards."""
    all_socs = glob.glob("zibal/eda/boards/*yaml")
    return list(map(lambda x: os.path.splitext(os.path.basename(x))[0], all_socs))


def get_boards_for_soc(soc):
    """Returns a list of all available boards for a SOC."""
    soc_file = f"zibal/eda/socs/{soc}.yaml"
    if not os.path.exists(soc_file):
        raise SystemExit(f"SOC {soc} does not exist.")
    return open_yaml(soc_file).get('boards', [])


def prepare(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}.{}Top prepare'.format(soc.lower(), board)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)


def compile_(args, env, cwd):  # pylint: disable=too-many-locals
    """Command to compile a Zephyr binary or bootrom."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    if args.type == "bootrom":
        command = "make"
        platform = ''.join(i.lower() for i in soc if not i.isdigit())
        fpl_cwd = os.path.join(cwd, "zibal-fpl")
        platform_cwd = os.path.join(fpl_cwd, platform)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=platform_cwd, check=True)

        build_cwd = os.path.join(cwd, f"build/{soc}/{board}/fpl")
        with open("{}/kernel.rom".format(build_cwd), 'w', encoding='UTF-8') as rom_file:
            command = "python {}/scripts/gen_rom.py".format(fpl_cwd)
            logging.debug(command)
            subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True, stdout=rom_file)

    if args.type == "zephyr":
        if not args.application:
            raise SystemExit("Firmware type 'zephyr' requires an application. Please define one.")
        force = "always" if args.f else "auto"
        output = f"build/{soc}/{board}/zephyr/"
        kit = f"{soc}-{board}".lower()
        include_path = os.path.join(cwd, f"build/{soc}/{board}")
        project_path = os.path.join(cwd, f"build/{soc}/{board}/zephyr-boards/")
        include = f"-DDTC_INCLUDE_FLAG_FOR_DTS=\"-isystem;{include_path}/\" " \
                  f"-DBOARD_ROOT={project_path}"
        command = "venv/bin/west build -p {} -b {} -d {} {} -- {}".format(force, kit, output,
                                                                          args.application,
                                                                          include)
        logging.debug(command)
        subprocess.run(shlex.split(command), env=env, cwd=cwd, check=True)

    if args.type == "menuconfig":
        zephyr_cwd = os.path.join(cwd, f"build/{soc}/{board}/zephyr")

        command = "ninja menuconfig"
        logging.debug(command)
        subprocess.run(shlex.split(command), env=env, cwd=zephyr_cwd, check=True)


def generate(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}.{}Top generate'.format(soc.lower(), board)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)


def flash(args, env, cwd):
    """Command to flash the design to a fpga or spi nor."""
    openocd_cwd = os.path.join(cwd, "openocd")
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    top = f"{board}Top"

    if args.destination == 'memory':
        debug(args, env, cwd, type_="flash")
    else:
        if not args.destination in board_data.get('flash_bridge', {}):
            raise SystemExit("Unsupported destination {} for board {}".format(args.destination,
                                                                              args.board))

        vivado_bit = os.path.exists(f"build/{soc}/{board}/vivado/syn/{top}.bit")
        symbiflow_bit = os.path.exists(f"build/{soc}/{board}/symbiflow/{top}.bit")
        if not (vivado_bit or symbiflow_bit):
            raise SystemExit("No bitstream found. Run \"./elements-fpga.py synthesize " \
                             f"{args.soc} {args.board}\" before.")

        if args.destination == "spi":
            bitstream_origin = "vivado"
        else:
            bitstream_origin = "symbiflow" if symbiflow_bit else "vivado"
        destination = board_data['flash_bridge'][args.destination]
        transport = board_data['flash_bridge']["transport"]
        command = ['src/openocd',
                   '-c', 'set SOC {}'.format(soc),
                   '-c', 'set BOARD {}'.format(board),
                   '-c', 'set TOP {}'.format(top),
                   '-c', 'set BASE_PATH {}'.format(env['ELEMENTS_BASE']),
                   '-c', 'set TRANSPORT {}'.format(transport),
                   '-c', 'set BITSTREAM_ORIGIN {}'.format(bitstream_origin),
                   '-f', '../zibal/openocd/flash_{}.cfg'.format(destination)]
        logging.debug(command)
        subprocess.run(command, env=env, cwd=openocd_cwd, check=True)


def debug(args, env, cwd, type_="debug"):
    """Command to debug the firmware with GDB"""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    platform = ''.join(i.lower() for i in soc if not i.isdigit())
    if not os.path.exists(f"build/{soc}/{board}/zephyr/zephyr/zephyr.elf"):
        raise SystemExit("No Zephyr elf found. Run \"./elements-fpga.py compile " \
                         f"{args.soc} {args.board} <app>\" before.")

    openocd_cwd = os.path.join(cwd, "openocd")
    yaml_path = f"../build/{soc}/{board}/zibal/VexRiscv.yaml"
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML {}'.format(yaml_path),
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/{}.cfg'.format(platform)]
    logging.debug(command)
    with subprocess.Popen(command, env=env, cwd=openocd_cwd, stdout=subprocess.DEVNULL) as \
        openocd_process:

        toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
        command = ['{}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb'.format(toolchain),
                   '-x', 'zibal/gdb/{}.cmd'.format(type_),
                   'build/{}/{}/zephyr/zephyr/zephyr.elf'.format(soc, board)]
        logging.debug(command)
        if type_ == "flash":
            with subprocess.Popen(command, env=env, cwd=cwd) as gdb_process:
                time.sleep(15)
                gdb_process.terminate()
        else:
            subprocess.run(command, env=env, cwd=cwd, check=True)
        openocd_process.terminate()


def benchmark(args, env, cwd): # pylint: disable=too-many-locals
    """Command to run Embench benchmark tests"""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    platform = ''.join(i.lower() for i in soc if not i.isdigit())
    toolchain = os.path.join(env['ELEMENTS_BASE'], 'riscv32-unknown-elf/bin/riscv32-unknown-elf-')
    gcc = toolchain + 'gcc'
    gdb = toolchain + 'gdb'
    python = "../venv/bin/python3"


    yaml_file = "build/{0}/{1}/zibal/{1}Top.yaml".format(soc, board)
    if not os.path.exists(yaml_file):
        raise SystemExit(f"{board}Top.yaml does not exist. Run prepare command first!")

    soc_data = open_yaml(yaml_file)
    cpu_frequency = soc_data.get('frequencies', {}).get('cpu', 0)
    if cpu_frequency == 0:
        raise SystemExit(f"No cpu frequency found in {board}Top.yaml")
    cpu_frequency = int(cpu_frequency / 1000000)

    embench_cwd = os.path.join(cwd, "embench-iot")
    command = "{} build_all.py --arch riscv32 --board {} --clean --cc {}".format(python, platform,
                                                                                 gcc)
    logging.debug(command)
    subprocess.run(shlex.split(command), env=env, cwd=embench_cwd, check=True)

    openocd_cwd = os.path.join(cwd, "openocd")
    yaml_path = f"../build/{soc}/{board}/zibal/VexRiscv.yaml"
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML {}'.format(yaml_path),
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/{}.cfg'.format(platform)]
    logging.debug(command)
    with subprocess.Popen(command, env=env, cwd=openocd_cwd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL) as openocd_process:

        print(f"CPU performance is {cpu_frequency} MHz")
        command = "{} benchmark_speed.py --gdb-command {} --target-module run_vexriscv_gdb" \
                  " --timeout 60 --cpu-mhz {}".format(python, gdb, cpu_frequency)
        logging.debug(command)
        subprocess.run(shlex.split(command), env=env, cwd=embench_cwd, check=True)

        openocd_process.terminate()

        command = "{} benchmark_size.py".format(python)
        logging.debug(command)
        subprocess.run(shlex.split(command), env=env, cwd=embench_cwd, check=True)


def get_variable(env, localenv, key):
    """Searchs for a variable in the bash env or in a file env."""
    if key in env:
        return env[key]
    if key in localenv:
        return localenv[key]
    raise SystemExit("Variable {} has no value".format(key))


def get_soc_name(soc):
    """Returns the SOC name used in Elements."""
    return soc.replace('-', '')


def get_board_name(board):
    """Returns the board name used in Elements."""
    return board.replace('-', '')


def open_board(board):
    """Opens a board file and checks a mandatory fields exist."""
    board_file = "zibal/eda/boards/{}.yaml".format(board)
    if not os.path.exists(board_file):
        raise SystemExit(f"Board {board} does not exist.")
    board = open_yaml(board_file)
    if 'xilinx' in board:
        for key in ['part', 'device']:
            if key not in board['xilinx']:
                raise SystemExit(f"No '{key}' defined in board xilinx tree.")
    if 'cadence' in board:
        for key in ['process', 'pdk']:
            if key not in board['cadence']:
                raise SystemExit(f"No '{key}' defined in board cadence tree.")
    if 'flash_bridge' in board:
        for key in ['transport']:
            if key not in board['flash_bridge']:
                raise SystemExit(f"No '{key}' defined in board flash bridge tree.")
    return board


def environment():
    """Reads the OS environment and adds extra variables for Elements."""
    env = os.environ.copy()
    base = os.path.dirname(os.path.abspath(__file__))
    localenv = {}
    if os.path.exists("env.ini"):
        config = configparser.ConfigParser()
        config.read("env.ini")
        localenv.update(config['DEFAULT'].items())

    zephyr_sdk_version = get_variable(env, localenv, 'zephyr_sdk_version')
    vivado_path = get_variable(env, localenv, 'vivado_path')

    env['ELEMENTS_BASE'] = base
    env['ZEPHYR_TOOLCHAIN_VARIANT'] = 'zephyr'
    env['ZEPHYR_SDK_VERSION'] = zephyr_sdk_version
    env['ZEPHYR_SDK_INSTALL_DIR'] = os.path.join(base, 'zephyr-sdk-{}'.format(zephyr_sdk_version))
    env['FPGA_FAM'] = "xc7"
    env['INSTALL_DIR'] = os.path.join(base, 'symbiflow')
    env['PATH'] += os.pathsep + vivado_path
    env['PATH'] += os.pathsep + os.path.join(base, 'symbiflow/xc7/install/bin')
    env['PATH'] = os.path.join(base, 'cmake/bin') + os.pathsep + env['PATH']
    env['PATH'] = os.path.join(base, 'verilator/bin') + os.pathsep + env['PATH']
    env['VERILATOR_ROOT'] = os.path.join(base, 'verilator')
    env['VIVADO_PATH'] = vivado_path
    env['PDK_BASE'] = get_variable(env, localenv, 'pdk_base')
    env['IHP_TECH'] = os.path.join(get_variable(env, localenv, 'pdk_base'), 'tech')
    return env


def verify_soc_board_combination(args):
    """Verifies the given board exists for the SOC."""
    soc_file = f"zibal/eda/socs/{args.soc}.yaml"
    if not os.path.exists(soc_file):
        raise SystemExit(f"SOC {args.soc} does not exist.")
    all_boards = open_yaml(soc_file).get('boards', [])
    if args.board not in all_boards:
        raise SystemExit(f"Board {args.board} is not available for {args.soc}")


def prepare_build(args):
    """Prepares the build directory."""
    verify_soc_board_combination(args)
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)

    path = f"build/{soc}/{board}"
    if not os.path.exists(path):
        os.makedirs(path)
    pathes = ["zibal", "fpl", "vivado/sim/logs", "vivado/syn/logs", "cadence/synthesize",
              "cadence/place", "cadence/sim", "symbiflow/logs",
              f"zephyr-boards/boards/riscv/{soc}"]
    pathes = list(map(lambda x: os.path.join(path, x), pathes))
    for path in pathes:
        if not os.path.exists(path):
            os.makedirs(path)
