Application
###########

An application is the user-level software. It's build-in to the firmware and will be started by
Zephyr. Custom applications for boards will be added as application during the Zephyr compile
process and are stored separatly from Zephyr in different repos. This makes is easier to add
custom applications to the SDK. For demo and testing purpose, some applications are included to the
SDK. They can be found under ``zephyr-samples/``. It also contains a template application.

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

The src/ folder contains the source code. The template or demos show the basic for threading and
how to use the drivers. Move informations can be found on the official Zephyr documentation.

System on Chip
##############

A System on Chip is an inheritance of one of the platforms. The idea behind this structure is to
easily create new SOCs by only configuring the peripherals for a platform. Since all platforms are
named after chemical elements, all SOCs are named like they would be an isotopes of them. For
example SOCs for the Hydrogen platform are called Hydrogen1, Hydrogen2, etc. Please keep in mind
this number is ongoing and always starts at 1.

All SOCs are placed in zibal/hardware/scala/zibal/soc and platforms can be found under
zibal/hardware/scala/zibal/platforms. Therefore, new SOCs can easily added by creating a new
directory and a file inside both called after the SOC.

Board
#####

A Board is a SOC with a specific pin-out. While a SOC only defines the in- and output-pins, a board
maps these to physical IOs of a package. Each SOC can be used in one or more boards. A good example
is ``Hydrogen1`` which purposes as demo SOC with a minimum of required peripherals to be supported
by as much as boards as possible. A board is represented by a dedicated file in a directory called
after the board inside the SOC directory.

The board file has two designs implemented. First, a top-level representation of the SOC with all
architecture dependent definitions like IO blocks or PLLs. The second file is a design to simulate
the SOC in a virtual board. External components like SPI memory should be added to this. Moreover,
test cases are added here for board verification.

Kit
###

A kit is a combination of a SOC and board. Since a SOC can be used in multiple boards, this unique
combination is very important.
