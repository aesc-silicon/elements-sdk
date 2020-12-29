Application
###########

Applications are stored separatly from Zephyr in different repos. This makes is easier to add
custom applications to the SDK. For demo and testing purpose, some applications are included to the
SDK. They can be found under zephyr-samples. It also contains a template application.

Since elements takes a relative path to the application, it is not important where it's stored, but
to have the correct structure. The following shows the template application:

.. code-block:: text

    .
    ├── CMakeLists.txt
    ├── prj.conf
    └── src
        └── main.c

Zephyr uses cmake to compile everything. The CMakeLists.txt adds all information to the
build-process. All C-Files in src/ must be included to the CMakeList.txt file.

Build-dependancies are solved by KConfig. This system is also implemented to Zephyr and can easily
configure which parts are added to the firmware. The prj.conf-File can be used to en- oder disable
Configs.

The src/ folder contains the Source Code. The template or demos show the basic for threading and
how to use the drivers. Move informations can be found on the official Zephyr documentation.

System on Chip
##############

A System on Chip is an inheritance of one of the platforms. The idea behind this structure is to
easily create new SOCs by only configuring the peripherals for a platform. Since all platforms are
named after chemical elements, all SOCs are named like they would be isotopes of them. For example
SOCs for the Hydrogen platform are called Hydrogen1, Hydrogen2, etc. Please keep in mind this
number is ongoing and always starts at 1.

All SOCs are placed in zibal/hardware/scala/zibal/soc and platforms can be found under
zibal/hardware/scala/zibal/platforms. Therefore, new SOCs can easily added by creating a new file
in the .../soc/ folder. There is a little bit of boilerplate-code which can be copied from other
SOCs. The main part consists of adding the peripherals configurations, IOs and the IP-Cores with
the bus addresses and interrupts.

Afterwards, a new device-tree must be created in zephyr/dts/riscv/ for this SOCs. The DT also
inherits from the platform and only the nodes for each peripheral must be defined. The final
configuration about the status for each peripheral, aliases or informations about LEDs are
defined on board-level.

Boards
######

A board represents a physical hardware with a SOC but do not include an application. It's basically
the pin-out of a SOC for the hardware. Therefore, all information are stored in two parts.

First, the board is defined in Zephyr. The following shows the DH-006, TH-283 and TH-294 boards
for the Hydrogen platform.

.. code-block:: text

    zephyr/boards/riscv/
    └── hydrogen
        ├── board.h
        ├── CMakeLists.txt
        ├── dh006_defconfig
        ├── dh006.dts
        ├── dh006.yaml
        ├── Kconfig.board
        ├── Kconfig.defconfig
        ├── th283_defconfig
        ├── th283.dts
        ├── th283.yaml
        ├── th294_defconfig
        ├── th294.dts
        └── th294.yaml


They are placed under zephyr/boards/riscv/ and than under the name of the platform. Both Kconfig
files contain the configs for all boards inside this folder and new boards should be added to this
file. Each board has three filed. The board_defconfig contains a list of configs for this boards.
The board.yaml describes the board for internal Zephyr tools and board.dts is the board-level
device tree which includes the SOC device tree. The CMakeLists.txt and board.h files can be
ignored.

Second, the board is also defined in Zibal for EDA-Tools like Vivado to simulate or synthesize the
design. All simulation-tools rely for each board on a testbench under zibal/eda/testbenches
which simulates partly a physical board. The top-level file for each SOC is architecture dependen
and defined in the corresponding EDA sub-folder.

For Xilinx boards, the top-level file is placed directly in zibal/eda/Xilinx/. It calls the module
of the SOC, set-ups all IO-blocks and defines the top-level IOs. For example tri-state buffer or
pull-resistors can be definded in this file. Lastly, the routing between the top-level IOs and the
physical FPGA pins is done in zibal/eda/Xilinx/syn/XDC/.
