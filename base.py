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
    command = ['sbt', 'runMain zibal.soc.{}.{}Top prepare'.format(soc.lower(), board)]
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
        raise SystemExit("No Zephyr elf found. Run \"./elements-fpga.py compile " \
                         f"{args.soc} {args.board} <app>\" before.")

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
