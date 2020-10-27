"""Tool to handle all projects in the elements SDK."""
import argparse
import subprocess
import os
import logging


_FORMAT = "%(asctime)s - %(message)s"
ZEPHYR_SDK_VERSION = "0.11.4"
VIVADO_PATH = "/opt/xilinx/Vivado/2019.2/bin/"


def parse_args():
    """Parses all arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help='Enables debug output')

    subparsers = parser.add_subparsers(help='Elements commands')

    parser_zephyr = subparsers.add_parser('zephyr', help='Builds the firmware')
    parser_zephyr.set_defaults(func=zephyr)
    parser_zephyr.add_argument('board', help="Name of the board")
    parser_zephyr.add_argument('application', help="Name of the application")
    parser_zephyr.add_argument('-f', action='store_true', help="Force build")

    parser_zibal = subparsers.add_parser('zibal', help='Builds the MCU')
    parser_zibal.set_defaults(func=zibal)
    parser_zibal.add_argument('soc', help="Name of the SOC")

    parser_sim = subparsers.add_parser('sim', help='Simulates the design')
    parser_sim.set_defaults(func=sim)
    parser_sim.add_argument('board', help="Name of the board")
    parser_sim.add_argument('--toolchain', default="xilinx", choices=['xilinx'],
                            help="Choose between differen toolchains.")

    parser_synth = subparsers.add_parser('synth', help='Synthesizes the design')
    parser_synth.set_defaults(func=synth)
    parser_synth.add_argument('board', help="Name of the board")
    parser_synth.add_argument('--toolchain', default="xilinx", choices=['xilinx'],
                              help="Choose between differen toolchains.")
    parser_synth.add_argument('-sim', action='store_true',
                              help="Simulate the design after synthesized")

    parser_flash = subparsers.add_parser('flash', help='Flashes parts of the SDK')
    parser_flash.set_defaults(func=flash)
    parser_flash.add_argument('board', help="Name of the board")
    parser_flash.add_argument('--destination', default='fpga', choices=['fpga', 'spi'],
                              help="Destination of the bitstream")
    parser_flash.add_argument('--toolchain', default="xilinx", choices=['xilinx'],
                              help="Choose between differen toolchains.")

    parser_gdb = subparsers.add_parser('GDB', help='Debugs the firmware')
    parser_gdb.set_defaults(func=gdb)
    parser_gdb.add_argument('type', choices=['flash', 'debug'], help="Type of GDB connection")

    parser_test = subparsers.add_parser('test', help='Tests the SDK')
    parser_test.set_defaults(func=test)
    parser_test.add_argument('-zibal', action='store_true', help="Run all Zibal tests")

    return parser.parse_args()


def zephyr(args, env, cwd):
    """Command to build a Zephyr binary for a board and application."""
    force = "always" if args.f else "auto"
    board = args.board.replace('-', '').lower()
    command = "west build -p {} -b {} -d ./build/zephyr/ {}".format(force, board,
                                                                    args.application)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=cwd, check=True)


def zibal(args, env, cwd):
    """Command to build a Microcontroller desig for a SOC."""
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
    # TODO toolchain
    xilinx_cwd = os.path.join(cwd, "zibal/eda/Xilinx/sim")
    command = "vivado -mode tcl -source tcl/{}.tcl -log ./output/logs/vivado.log " \
              "-journal ./output/logs/vivado.jou".format(args.board)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)


def synth(args, env, cwd):
    """Command to synthesize a SOC for a board."""
    # TODO toolchain
    xilinx_cwd = os.path.join(cwd, "zibal/eda/Xilinx/syn")
    sim_flag = "_sim" if args.sim else ""
    command = "vivado -mode tcl -source tcl/{}{}.tcl -log ./output/logs/vivado.log " \
              "-journal ./output/logs/vivado.jou".format(args.board, sim_flag)
    logging.debug(command)
    subprocess.run(command.split(' '), env=env, cwd=xilinx_cwd, check=True)


def flash(args, env, cwd):
    """Command to flash the design to a fpga or spi nor."""
    # TODO toolchain
    openocd_cwd = os.path.join(cwd, "openocd")
    if args.destination == 'spi':
        destination = 'spi'
    if args.destination == 'fpga':
        destination = "xc7"
    board = args.board.replace('-', '')
    command = ['src/openocd', '-c', 'set BOARD {}'.format(board),
               '-c', 'set BASE_PATH {}'.format(env['ELEMENTS_BASE']),
               '-f', '../zibal/eda/Xilinx/configs/flash_{}.cfg'.format(destination)]
    logging.debug(command)
    subprocess.run(command, env=env, cwd=openocd_cwd, check=True)


def gdb(args, env, cwd):
    """Command to debug the firmware."""
    openocd_cwd = os.path.join(cwd, "openocd")
    command = ['./src/openocd', '-c', 'set HYDROGEN_CPU0_YAML ../build/zibal/VexRiscv.yaml',
               '-f', 'tcl/interface/jlink.cfg',
               '-f', '../zibal/gdb/hydrogen.cfg']
    logging.debug(command)
    openocd_process = subprocess.Popen(command, env=env, cwd=openocd_cwd,
                                       stdout=subprocess.DEVNULL)

    toolchain = env['ZEPHYR_SDK_INSTALL_DIR']
    command = ['./{}/riscv64-zephyr-elf/bin/riscv64-zephyr-elf-gdb'.format(toolchain),
               '-x', 'zibal/gdb/{}.cmd'.format(args.type),
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
    env['ELEMENTS_BASE'] = os.path.dirname(os.path.abspath(__file__))
    env['ZEPHYR_TOOLCHAIN_VARIANT'] = 'zephyr'
    env['ZEPHYR_SDK_INSTALL_DIR'] = 'zephyr-sdk-{}'.format(ZEPHYR_SDK_VERSION)
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
