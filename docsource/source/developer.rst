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
named after chemical elements, all SOCs are named like they would be an isotopes of them. For
example SOCs for the Hydrogen platform are called Hydrogen1, Hydrogen2, etc. Please keep in mind
this number is ongoing and always starts at 1.

All SOCs are placed in zibal/hardware/scala/zibal/soc and platforms can be found under
zibal/hardware/scala/zibal/platforms. Therefore, new SOCs can easily added by creating a new
directory and a file inside both called after the SOC.
