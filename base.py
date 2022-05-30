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
    parser_compile.add_argument('storage', nargs='?', default="",
                                help="Name of the software storege")
    parser_compile.add_argument('application', nargs='?', default="",
                                help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_menuconfig = subparsers.add_parser('menuconfig',
                                              help="Opens the menuconfig for a firmware")
    parser_menuconfig.set_defaults(func=menuconfig)
    parser_menuconfig.add_argument('storage', help="Name of the software storege")

    parser_generate = subparsers.add_parser('generate', help="Generates a SOC")
    parser_generate.set_defaults(func=generate)

    parser_flash = subparsers.add_parser('flash', help="Flashes parts of the SDK")
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi', 'memory'],
                              help="Destination of the bitstream or firmware")
    parser_flash.add_argument('storage', nargs='?', default="",
                              help="Name of the software storege. Required for memory destination")

    parser_debug = subparsers.add_parser('debug', help="Debugs a firmware with GDB.")
    parser_debug.set_defaults(func=debug)
    parser_debug.add_argument('storage', help="Name of the software storege")

    parser_benchmark = subparsers.add_parser('benchmark', help="Benchmark tests for a kit")
    parser_benchmark.set_defaults(func=benchmark)

    parse_tool_args(subparsers, parser)

    return parser.parse_args()


def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r', encoding='UTF-8') as stream:
            if version.parse(yaml.__version__) > version.parse("5.1.0"):
                return yaml.load(stream, Loader=yaml.FullLoader)
            return yaml.load(stream) # pylint: disable=no-value-for-parameter
    except yaml.YAMLError as exc:
        raise SystemExit from exc
    except FileNotFoundError as exc:
        raise SystemExit from exc
    raise SystemExit(f"Unable to open {path}")


def get_socs():
    """Returns a list of all available SOCs."""
    all_socs = glob.glob("meta/socs/*yaml")
    return list(map(lambda x: os.path.splitext(os.path.basename(x))[0], all_socs))


def get_boards():
    """Returns a list of all available boards."""
    all_socs = glob.glob("meta/boards/*yaml")
    return list(map(lambda x: os.path.splitext(os.path.basename(x))[0], all_socs))


def get_boards_for_soc(soc):
    """Returns a list of all available boards for a SOC."""
    soc_file = f"meta/socs/{soc}.yaml"
    if not os.path.exists(soc_file):
        raise SystemExit(f"SOC {soc} does not exist.")
    return open_yaml(soc_file).get('boards', [])


# pylint: disable=too-many-arguments
def command(cmd, env, cwd, stdout=None, stderr=None, handler=None):
    """Wrapper to call subprocess calls."""
    logging.debug(cmd)
    if handler:
        with subprocess.Popen(shlex.split(cmd), env=env, cwd=cwd, stdout=stdout,
                              stderr=stderr) as process:
            if handler:
                handler(process)
            process.terminate()
    else:
        subprocess.run(shlex.split(cmd), env=env, cwd=cwd, check=True, stdout=stdout,
                       stderr=stderr)


def prepare(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    command(f"sbt \"runMain elements.soc.{soc.lower()}.{board}Prepare\"", env, cwd)


def compile_baremetal(_, env, cwd, name, soc, board):
    """Compiles a bare metal firmware."""
    env['STORAGE'] = name

    fpl_cwd = os.path.join(cwd, "internal/zibal/software/bootrom/")
    command("make", env, fpl_cwd)

    build_cwd = os.path.join(cwd, f"build/{soc}/{board}/software/{name}")
    with open(f"{build_cwd}/kernel.rom", 'w', encoding='UTF-8') as rom_file:
        command(f"python {fpl_cwd}/scripts/gen_rom.py", env, build_cwd, rom_file)


def compile_zephyr(args, env, cwd, name, soc, board, data):
    """Compiles a Zephyr firmware."""
    force = "always" if args.f else "auto"
    kit = f"{soc}-{board}".lower()
    if args.application:
        application = args.application
    else:
        application = data.get('application', "internal/zephyr-samples/demo/leds/")
    include_path = os.path.join(cwd, f"build/{soc}/{board}/software/{name}/")
    if data.get("include", "") == "hardware":
        include_path = os.path.join(cwd, f"hardware/scala/soc/{soc}/{board}/{name}/")
    output = f"../build/{soc}/{board}/software/{name}/zephyr/"
    project_path = os.path.join(cwd, f"build/{soc}/{board}/software/{name}/zephyr-boards/")
    application_path = os.path.join(cwd, application)
    include = f"-DDTC_INCLUDE_FLAG_FOR_DTS=\"-isystem;{include_path}/\" " \
              f"-DBOARD_ROOT={project_path}"
    command(f"../venv/bin/west build -p {force} -b {kit} -d {output} {application_path} -- " \
            f"{include}", env, os.path.join(cwd, "internal"))


def compile_(args, env, cwd):  # pylint: disable=too-many-locals
    """Command to compile a Zephyr binary or bootrom."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    storages = open_yaml(f"build/{soc}/{board}/software/storages.yaml")
    if hasattr(args, 'storage') and args.storage:
        if args.storage not in storages:
            raise SystemExit(f"Storage {args.storage} not found.")
        os_type = storages[args.storage]["os"]
        if os_type == "baremetal":
            #  pyline: disable=too-many-function-args
            compile_baremetal(args, env, cwd, args.storage, soc, board)
        if os_type == "zephyr":
            #  pyline: disable=too-many-function-args
            compile_zephyr(args, env, cwd, args.storage, soc, board, storages[args.storage])
    else:
        for storage, data in storages.items():
            os_type = data.get('os')
            if os_type == "baremetal":
                #  pyline: disable=too-many-function-args
                compile_baremetal(args, env, cwd, storage, soc, board)
            if os_type == "zephyr":
                #  pyline: disable=too-many-function-args
                compile_zephyr(args, env, cwd, storage, soc, board, data)


def menuconfig(args, env, cwd):
    """Opens the menuconfig for a firmware."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    storages = open_yaml(f"build/{soc}/{board}/software/storages.yaml")
    if args.storage not in storages:
        raise SystemExit(f"Storage {args.storage} not found.")
    os_type = storages[args.storage]

    if os_type == "zephyr":
        build_path = os.path.join(cwd, f"build/{soc}/{board}/software/{args.storage}/zephyr/")
        command("ninja menuconfig", env, build_path)


def generate(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    command(f"sbt \"runMain elements.soc.{soc.lower()}.{board}Generate\"", env, cwd)


def functional_simulation(args, env, cwd):
    """Runs a functional simulation and shows the waveform."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board
    top = f"{board}Top"

    if not os.path.exists(f"build/{soc}/{board}/zibal/{top}.v"):
        raise SystemExit(f"No SOC design found. Run \"./elements-fpga.py {args.soc} "
                         f"{args.board} generate\" before.")

    build_cwd = os.path.join(cwd, f"build/{soc}/{board}/zibal/{board}Board/")
    command(f"sbt \"runMain elements.soc.{soc.lower()}.{board}Simulate\"", env, cwd)

    command("gtkwave -o simulate.vcd", env, build_cwd)


def flash(args, env, cwd):
    """Command to flash the design to a fpga or spi nor."""
    openocd_cwd = os.path.join(cwd, "internal/openocd")
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    top = f"{board}Top"

    if args.destination == 'memory':
        debug(args, env, cwd, type_="flash")
    else:
        if not args.destination in board_data.get('flash_bridge', {}):
            raise SystemExit(f"Unsupported destination {args.destination} for board {args.board}")

        vivado_bit = os.path.exists(f"build/{soc}/{board}/vivado/syn/{top}.bit")
        symbiflow_bit = os.path.exists(f"build/{soc}/{board}/symbiflow/{top}.bit")
        if not (vivado_bit or symbiflow_bit):
            raise SystemExit("No bitstream found. Run \"./elements-fpga.py " \
                             f"{args.soc} {args.board} synthesize\" before.")

        if args.destination == "spi":
            bitstream_origin = "vivado"
        else:
            bitstream_origin = "symbiflow" if symbiflow_bit else "vivado"
        destination = board_data['flash_bridge'][args.destination]
        transport = board_data['flash_bridge']["transport"]
        cmd = f"src/openocd -c \"set SOC {soc}\" -c \"set BOARD {board}\" -c \"set TOP {top}\" " \
              f"-c \"set BASE_PATH {env['ELEMENTS_BASE']}\" -c \"set TRANSPORT {transport}\" " \
              f"-c \"set BITSTREAM_ORIGIN {bitstream_origin}\" " \
              f"-f ../zibal/openocd/flash_{destination}.cfg"
        command(cmd, env, openocd_cwd)


def debug(args, env, cwd, type_="debug"):
    """Command to debug the firmware with GDB"""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    platform = ''.join(i.lower() for i in soc if not i.isdigit())
    if not args.storage:
        raise SystemExit("Flashing a software requires the 'storage' argument.")
    storages = open_yaml(f"build/{soc}/{board}/software/storages.yaml")
    if args.storage not in storages:
        raise SystemExit(f"Storage {args.storage} not found.")
    os_type = storages[args.storage]

    if os_type == "zephyr":
        if not os.path.exists(
                f"build/{soc}/{board}/software/{args.storage}/zephyr/zephyr/zephyr.elf"):
            raise SystemExit("No Zephyr elf found. Run \"./elements-fpga.py " \
                             f"{args.soc} {args.board} compile {args.storage}\" before.")
        elf = f"build/{soc}/{board}/software/{args.storage}/zephyr/zephyr/zephyr.elf"

    openocd_cwd = os.path.join(cwd, "internal/openocd")
    yaml_path = f"../../build/{soc}/{board}/zibal/VexRiscv.yaml"
    cmd = f"./src/openocd -c \"set ELEMENTS_CPU0_YAML {yaml_path}\" " \
          f"-f tcl/interface/jlink.cfg -f ../zibal/gdb/{platform}.cfg"

    def openocd_handler(_):
        toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
        cmd = f"{toolchain}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb " \
              f"-x internal/zibal/gdb/{type_}.cmd {elf}"
        if type_ == "flash":
            command(cmd, env, cwd, handler=lambda _: time.sleep(15))
        else:
            command(cmd, env, cwd)

    command(cmd, env, openocd_cwd, subprocess.DEVNULL, handler=openocd_handler)


def benchmark(args, env, cwd): # pylint: disable=too-many-locals
    """Command to run Embench benchmark tests"""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    platform = ''.join(i.lower() for i in soc if not i.isdigit())
    toolchain = os.path.join(env['ELEMENTS_INTERNAL'],
        'riscv32-unknown-elf/bin/riscv32-unknown-elf-')
    gcc = toolchain + 'gcc'
    gdb = toolchain + 'gdb'
    python = "../../venv/bin/python3"


    yaml_file = f"build/{soc}/{board}/zibal/{board}Top.yaml"
    if not os.path.exists(yaml_file):
        raise SystemExit(f"{board}Top.yaml does not exist. Run prepare command first!")

    soc_data = open_yaml(yaml_file)
    cpu_frequency = soc_data.get('frequencies', {}).get('cpu', 0)
    if cpu_frequency == 0:
        raise SystemExit(f"No cpu frequency found in {board}Top.yaml")
    cpu_frequency = int(cpu_frequency / 1000000)

    embench_cwd = os.path.join(cwd, "internal/embench-iot")
    command(f"{python} build_all.py --arch riscv32 --board {platform} --clean --cc {gcc}", env,
            embench_cwd)

    openocd_cwd = os.path.join(cwd, "internal/openocd")
    yaml_path = f"../../build/{soc}/{board}/zibal/VexRiscv.yaml"
    cmd = f"./src/openocd -c \"set HYDROGEN_CPU0_YAML {yaml_path}\" " \
          f"-f tcl/interface/jlink.cfg -f ../zibal/gdb/{platform}.cfg"

    def benchmark_handler(_):
        print(f"CPU performance is {cpu_frequency} MHz")
        cmd = f"{python} benchmark_speed.py --gdb-command {gdb} --target-module run_vexriscv_gdb" \
              " --timeout 60 --cpu-mhz 100"
        command(cmd, env, embench_cwd)

        command(f"{python} benchmark_size.py", env, embench_cwd)

    command(cmd, env, openocd_cwd, subprocess.DEVNULL, handler=benchmark_handler)


def get_variable(env, localenv, key):
    """Searchs for a variable in the bash env or in a file env."""
    if key in env:
        return env[key]
    if key in localenv:
        return localenv[key]
    raise SystemExit(f"Variable {key} has no value")


def get_soc_name(soc):
    """Returns the SOC name used in Elements."""
    return soc.replace('-', '')


def get_board_name(board):
    """Returns the board name used in Elements."""
    return board.replace('-', '')


def open_board(board):
    """Opens a board file and checks a mandatory fields exist."""
    board_file = f"meta/boards/{board}.yaml"
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
    internal = os.path.join(base, "internal")
    localenv = {}
    if os.path.exists("env.ini"):
        config = configparser.ConfigParser()
        config.read("env.ini")
        localenv.update(config['DEFAULT'].items())
        for pdk in ('SG13S', 'SG13S2'):
            if pdk in config:
                localenv.update(config[pdk].items())

    zephyr_sdk_version = get_variable(env, localenv, 'zephyr_sdk_version')
    vivado_path = get_variable(env, localenv, 'vivado_path')

    env['ELEMENTS_BASE'] = base
    env['ELEMENTS_INTERNAL'] = internal
    env['NAFARR_BASE'] = os.path.join(internal, 'nafarr')
    env['ZEPHYR_TOOLCHAIN_VARIANT'] = 'zephyr'
    env['ZEPHYR_SDK_VERSION'] = zephyr_sdk_version
    env['ZEPHYR_SDK_INSTALL_DIR'] = os.path.join(internal, f'zephyr-sdk-{zephyr_sdk_version}')
    env['Zephyr_DIR'] = os.path.join(internal, 'zephyr')
    env['FPGA_FAM'] = "xc7"
    env['INSTALL_DIR'] = os.path.join(internal, 'symbiflow')
    env['PATH'] += os.pathsep + vivado_path
    env['PATH'] += os.pathsep + os.path.join(internal, 'symbiflow/xc7/install/bin')
    env['PATH'] = os.path.join(internal, 'cmake/bin') + os.pathsep + env['PATH']
    env['PATH'] = os.path.join(internal, 'verilator/bin') + os.pathsep + env['PATH']
    env['VERILATOR_ROOT'] = os.path.join(internal, 'verilator')
    env['VIVADO_PATH'] = vivado_path
    env['PDK_BASE'] = get_variable(env, localenv, 'pdk_base')
    env['IHP_TECH'] = os.path.join(get_variable(env, localenv, 'pdk_base'), 'tech')
    return env


def verify_soc_board_combination(args):
    """Verifies the given board exists for the SOC."""
    soc_file = f"meta/socs/{args.soc}.yaml"
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
    pathes = ["zibal", "vivado/sim/logs", "vivado/syn/logs", "cadence/synthesize",
              "cadence/place", "cadence/sim", "symbiflow/logs", "software"]
    pathes = list(map(lambda x: os.path.join(path, x), pathes))
    for path in pathes:
        if not os.path.exists(path):
            os.makedirs(path)
