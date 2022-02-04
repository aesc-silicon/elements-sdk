Elements SDK
============

The Elements software development kit (SDK) is a hard-/software co-design tool to develop, debug
and maintain all stacks of an open-source System on Chip (SoC).

It has various different projects included and supports to choose between open-source or vendor
toolchains for FPGA and ASIC flows.

.. inclusion-start-marker-do-not-remove

Features
########

* Open-Source FPGA flow
* Portfolio of configurable peripherals with OS support
* Predefined SOC platforms
* Integrated Operation Systems like Zephyr
* Toolchain files are generated automatically
* Nightly checks

Focus on defining a custom SOC and writing your applcation!

Prerequisites
#############

* Linux host system (Ubuntu 20.04 recommended)
* Python 3 (python3.8-dev)
* Vivado for Xilinx platforms (optional)
* Cadence for digital silicons (optional)

Installation
############

- Install required packages::

        sudo apt install ssh git curl libtool-bin autotools-dev automake pkg-config libyaml-dev
        sudo apt install libssl-dev gdb ninja-build
        sudo apt install python3 python3.8-dev python3-pip virtualenv openjdk-11-jre-headless
        sudo apt install verilator gtkwave libcanberra-gtk-module libcanberra-gtk3-module
        sudo apt install libtinfo5 libncurses5

- Download the repository and checkout the latest release::

        git clone https://github.com/aesc-silicon/elements-sdk.git
        cd elements-sdk/
        git checkout v22.1

- Create a virtualenv::

        virtualenv -p python3 venv

- Initialise the SDK::

        python3 elements.py init

Vivado
******

The Vivado toolchain is not part of this SDK and needs to be installed separately for Xilinx
platforms from `Xilinx's homepage`_. Download the Linux Self Extracting Web Installer for Version
2020.2 and install it. Select Vivado as product and Vivado HL WebPACK as Edition. You can use this
edition's license for free, if you do not sell the bitsream, and disable everything except the
Artix-7 Platform to save disk storage. Elements excepts to find the Vivado toolchain under
``/opt/xilinx``.

.. code-block:: text

    chmod +x ~/Downloads/Xilinx_Unified_2020.2_1118_1232_Lin64.bin
    ~/Downloads/Xilinx_Unified_2020.2_1118_1232_Lin64.bin

.. _Xilinx's homepage: https://www.xilinx.com/support/download.html

Docker
######

The Elements SDK supports to run inside Docker. Currently, only self-build images can be used
due a lack of uploading pre-build images.

Custom Image
************

A Docker Compose configuration is provided for systems which do not run with the recommended
versions. The Docker will have included all required packages for the SDK, expect vendor toolchains.
Build the image (which can take some minutes).

.. code-block:: text

    docker-compose build

Next, start the Docker in the background.

.. code-block:: text

    docker-compose up -d

Afterwards, all Python tools can be used identical to the CLI.

.. code-block:: text

    sudo docker exec -it elements_sdk_1 \
        ./elements-fpga.py Hydrogen1 Nexys4-DDR build zephyr-samples/demo/leds \
        --toolchain symbiflow

.. tip::

    Add ``--toolchain symbiflow`` as parameter for the synthesize command to use the open-source
    toolchain.

Finally, stop the Docker.

.. code-block:: text

    docker-compose stop

Support
#######

FPGA Development Boards
***********************

+-------------+-----------+------------+
| Board       | Vendor    | FPGA Chip  |
+=============+===========+============+
| Nexys4-DDR  | Digilent  | Artix-7    |
+-------------+-----------+------------+
| AX7101      | Alinx     | Artix-7    |
+-------------+-----------+------------+
| AX7035      | Alinx     | Artix-7    |
+-------------+-----------+------------+
| DH-006      | Phytec    | Artix-7    |
+-------------+-----------+------------+

PDKS
****

+-----------+----------+
| Foundary  | PDK      |
+===========+==========+
| IHP       | SG13S    |
+-----------+----------+
| IHP       | SG13S2   |
+-----------+----------+

.. inclusion-end-marker-do-not-remove

Documentation
#############

The complete documentation is hosted on `https://aesc-silicon.github.io/elements-sdk/`_.

.. _https://aesc-silicon.github.io/elements-sdk/: https://aesc-silicon.github.io/elements-sdk/

It describes the FPGA and ASIC flows and explains basic information and how to develop a simple
Design.

Build
*****
The documentation can easily build with Sphinx. Therefore, run the Makefile inside the docsource
folder.

.. code-block:: text

    source venv/bin/activate
    make clean html -C docsource
    firefox docsource/build/html/index.html

License
#######

Copyright (c) 2022 aesc silicon. Released under the `MIT license`_.

.. _MIT license: COPYING.MIT
