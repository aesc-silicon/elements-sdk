#!venv/bin/python3
"""Tool to handle all projects in the elements SDK."""
import argparse
import subprocess
import os
import logging
import time
import shutil
import glob
import configparser
import datetime
import shlex
import yaml
from packaging import version


_FORMAT = "%(asctime)s - %(message)s"


def open_yaml(path):
    """Opens a YAML file and returns the content as dictionary."""
    try:
        with open(path, 'r') as stream:
            if version.parse(yaml.__version__) > version.parse("5.1.0"):
                return yaml.load(stream, Loader=yaml.FullLoader)
            return yaml.load(stream)
    except yaml.YAMLError as exc:
        raise SystemExit from exc
    except FileNotFoundError as exc:
        raise SystemExit from exc
    raise SystemExit("Unable to open {}".format(path))


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
    parser_compile.add_argument('type', choices=['zephyr', 'bootrom'], help="Type of firmware")
    parser_compile.add_argument('application', nargs='?', default="",
                                help="Name of the application")
    parser_compile.add_argument('-f', action='store_true', help="Force build")

    parser_generate = subparsers.add_parser('generate', help="Generates a SOC")
    parser_generate.set_defaults(func=generate)
    parser_generate.add_argument('soc', help="Name of a SOC")
    parser_generate.add_argument('board', help="Name of a board")

    parser_sim = subparsers.add_parser('simulate', help="Simulates a design")
    parser_sim.set_defaults(func=sim)
    parser_sim.add_argument('soc', help="Name of a SOC")
    parser_sim.add_argument('board', help="Name of a board")

    parser_sim.add_argument('--toolchain', default="oss", choices=['oss', 'cadence'],
                            help="Choose between different toolchains.")
    parser_sim.add_argument('--source', default="generated",
                            choices=['generated', 'synthesized', 'placed'],
                            help="Choose between different design sources.")

    parser_syn = subparsers.add_parser('synthesize', help="Synthesizes the design")
    parser_syn.set_defaults(func=syn)
    parser_syn.add_argument('soc', help="Name of a SOC")
    parser_syn.add_argument('board', help="Name of a board")
    parser_syn.add_argument('--toolchain', default="xilinx", choices=['xilinx', 'oss'],
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

    parser_map = subparsers.add_parser('map', help="Map the design")
    parser_map.set_defaults(func=map_)
    parser_map.add_argument('soc', help="Name of a SOC")
    parser_map.add_argument('board', help="Name of a board")
    parser_map.add_argument('--toolchain', default="cadence", choices=['cadence'],
                            help="Choose between different toolchains.")
    parser_map.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                            help="Choose between different mapping effort modes.")

    parser_place = subparsers.add_parser('place', help="Place and route the design")
    parser_place.set_defaults(func=place)
    parser_place.add_argument('soc', help="Name of a SOC")
    parser_place.add_argument('board', help="Name of a board")
    parser_place.add_argument('--stage', default="save", choices=['init', 'floorplan', 'place',
                                                                  'cts', 'route', 'signoff',
                                                                  'verify', 'save'],
                              help="Define a stage the place and route should stop")

    parser_place.add_argument('--toolchain', default="cadence", choices=['cadence'],
                              help="Choose between different toolchains.")
    parser_place.add_argument('--effort', default="high", choices=['low', 'medium', 'high'],
                              help="Choose between different placeping effort modes.")

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
    parser_test.add_argument('type', choices=['software'], help="Type of testse")
    parser_test.add_argument('case', nargs='?', default="", help="Name of the test case")

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
        with open("./repo", "w") as text_file:
            text_file.write(proc.stdout.decode())

        command = "chmod a+x ./repo"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)

    command = "python3 ./repo init -u https://github.com/phytec-labs/elements-manifest.git"
    if args.manifest:
        command = command + " -m {}".format(args.manifest)
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


def socs(args, env, cwd):
    """Lists all available SOCs by existing SOC files."""
    all_socs = glob.glob("zibal/eda/socs/*yaml")
    all_socs = list(map(lambda x: os.path.splitext(os.path.basename(x))[0], all_socs))
    for soc in all_socs:
        print(f"{soc}")


def boards(args, env, cwd):
    """Lists all available boards for a SOC."""
    soc_file = f"zibal/eda/socs/{args.soc}.yaml"
    if not os.path.exists(soc_file):
        raise SystemExit(f"SOC {args.soc} does not exist.")
    all_boards = open_yaml(soc_file).get('boards', [])
    for board in all_boards:
        print(f"{board}")


def prepare(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}'.format(soc)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)


def compile_(args, env, cwd):
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
        with open("{}/kernel.rom".format(build_cwd), 'w') as rom_file:
            command = "python {}/scripts/gen_rom.py".format(fpl_cwd)
            logging.debug(command)
            subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True, stdout=rom_file)

    if args.type == "zephyr":
        if not args.application:
            raise SystemExit("Firmware type 'zephyr' requires an application. Please define one.")
        force = "always" if args.f else "auto"
        output = f"build/{soc}/{board}/zephyr/"
        kit = f"{soc}-{board}".lower()
        include_path = os.path.join(cwd, f"build/{soc}")
        project_path = os.path.join(cwd, f"build/{soc}/{board}/zephyr-boards/")
        include = f"-DDTC_INCLUDE_FLAG_FOR_DTS=\"-isystem;{include_path}/\" " \
                  f"-DBOARD_ROOT={project_path}"
        command = "venv/bin/west build -p {} -b {} -d {} {} -- {}".format(force, kit, output,
                                                                          args.application,
                                                                          include)
        logging.debug(command)
        subprocess.run(shlex.split(command), env=env, cwd=cwd, check=True)


def generate(args, env, cwd):
    """Command to prepare a SOC board combination by generating all required files."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    env['SOC'] = soc
    env['BOARD'] = board

    cwd = os.path.join(cwd, "zibal")
    command = ['sbt', 'runMain zibal.soc.{}.{}Top '.format(soc.lower(), board)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=cwd, check=True)


def sim(args, env, cwd):
    """Command to simulate a SOC on a virtual board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
    env['SOC'] = soc
    env['BOARD'] = board
    top = f"{board}Top"

    if args.source == "generated" and not os.path.exists(f"build/{soc}/{board}/zibal/{top}.v"):
        raise SystemExit(f"No SOC design found. Run \"./elements.py generate {args.soc} "
                         f"{args.board}\" before.")

    vivado_bit = os.path.exists(f"build/{soc}/{board}/vivado/syn/{top}_pr.v")
    symbiflow_bit = os.path.exists(f"build/{soc}/{board}/symbiflow/{top}_synth.v")
    if args.source == "synthesized" and not (vivado_bit or symbiflow_bit):
        raise SystemExit("No bitstream found. "
                         f"Run \"./elements.py synthesize {args.soc} {args.board}\" before.")

    if args.toolchain == 'oss':
        if args.source == "placed":
            raise SystemExit("Source type is not supported for the Open-Source toolchain.")

        if args.source == "generated":
            source = args.source
        else:
            raise SystemExit("Source type is not supported for the Open-Source toolchain.")

        build_cwd = os.path.join(cwd, f"build/{soc}/{board}/zibal/{board}Board/")
        zibal_cwd = os.path.join(cwd, "zibal")
        command = ['sbt', 'runMain zibal.soc.{}.{}Board {} boot'.format(soc.lower(), board,
                                                                        source)]
        logging.debug(command)
        subprocess.run(command, env=env, cwd=zibal_cwd, check=True)

        command = "gtkwave boot.vcd"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=build_cwd, check=True,
                       stdin=subprocess.PIPE)

    if args.toolchain == 'cadence':
        if args.source == "synthesized":
            raise SystemExit("Source type is not supported for the Cadence toolchain.")

        if not 'cadence' in board_data:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        env['PDK'] = board['cadence']['pdk']
        env['TCL_PATH'] = os.path.join(cwd, "zibal/eda/Cadence/tcl/")
        env['SIM_TYPE'] = args.source
        cadence_cwd = os.path.join(cwd, "build/{}/cadence/sim".format(args.board))

        binaries = glob.glob("build/{}/fpl/*.rom".format(args.board))
        for binary in binaries:
            subprocess.run("ln -sf {} .".format(os.path.join("../../../..", binary)).split(' '),
                           env=env, cwd=cadence_cwd, stdout=subprocess.DEVNULL, check=True)

        command = "../../../../zibal/eda/Cadence/tcl/sim.sh"
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)


def syn(args, env, cwd):
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


def map_(args, env, cwd):
    """Command to map a SOC for a board."""
    soc = get_soc_name(args.soc)
    board = get_board_name(args.board)
    board_data = open_board(args.board)
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

        logs_path = os.path.join(cwd, f"build/{soc}/{board}cadence/map", now, "logs")
        cadence_cwd = os.path.join(cwd, "zibal/eda/Cadence/")
        command = "genus -f tcl/map.tcl -log {}".format(logs_path)
        logging.debug(command)
        subprocess.run(command.split(' '), env=env, cwd=cadence_cwd, check=True)

        command = f"cp build/{soc}/{board}/cadence/map/latest/{soc}.v " \
                  f"build/{soc}/{board}/cadence/map"
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
        if not 'cadence' in board:
            raise SystemExit("No cadence definitions in board {}".format(args.board))

        now = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        env['DATETIME'] = now
        env['PROCESS'] = str(board_data['cadence']['process'])
        env['PDK'] = board_data['cadence']['pdk']

        logs_path = os.path.join(cwd, f"build/{soc}/{board}cadence/map", now, "logs")
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
    syn(args, env, cwd)


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
            raise SystemExit("No bitstream found. "
                             f"Run \"./elements.py synthesize {args.soc} {args.board}\" before.")

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
    if not os.path.exists(f"build/{soc}/{board}/zephyr/zephyr/zephyr.elf"):
        raise SystemExit("No Zephyr elf found. "
                         f"Run \"./elements.py compile {args.soc} {args.board} <app>\" before.")

    openocd_cwd = os.path.join(cwd, "openocd")
    yaml_path = f"../build/{soc}/{board}/zibal/VexRiscv.yaml"
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML {}'.format(yaml_path),
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/hydrogen.cfg']
    logging.debug(command)
    openocd_process = subprocess.Popen(command, env=env, cwd=openocd_cwd,
                                       stdout=subprocess.DEVNULL)

    toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
    command = ['{}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb'.format(toolchain),
               '-x', 'zibal/gdb/{}.cmd'.format(type_),
               'build/{}/{}/zephyr/zephyr/zephyr.elf'.format(soc, board)]
    logging.debug(command)
    if type_ == "flash":
        gdb_process = subprocess.Popen(command, env=env, cwd=cwd)
        time.sleep(15)
        gdb_process.terminate()
    else:
        subprocess.run(command, env=env, cwd=cwd, check=True)
    openocd_process.terminate()


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
    pathes = ["zibal", "fpl", "vivado/sim/logs", "vivado/syn/logs", "cadence/map", "cadence/place",
              "cadence/sim", "symbiflow/logs", f"zephyr-boards/boards/riscv/{soc}"]
    pathes = list(map(lambda x: os.path.join(path, x), pathes))
    for path in pathes:
        if not os.path.exists(path):
            os.makedirs(path)


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
