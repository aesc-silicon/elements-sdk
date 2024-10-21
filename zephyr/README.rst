Elements Zephyr
===============

.. inclusion-start-marker-do-not-remove

Elements is fully integrated into Zephyr's meta-tool West and aims to provide RISC-V designs to
developers without deep knowledge about hardware design. Therefore, extra commands were added to
West to generate, synthesize, and simulate designs.

Prerequisites
#############

* Linux host system (Ubuntu 22.04 recommended)
* Python 3 (python3.10-dev)
* Vivado for Xilinx platforms (optional)

Installation
############

- Install required packages::

        sudo apt install ssh git curl libtool-bin autotools-dev automake pkg-config libyaml-dev
        sudo apt install libssl-dev gdb ninja-build flex bison libfl-dev cmake libftdi1-dev
        sudo apt install python3 python3.10-dev python3-pip virtualenv openjdk-11-jdk-headless
        sudo apt install verilator gtkwave libcanberra-gtk-module libcanberra-gtk3-module
        sudo apt install libtinfo5 libncurses5 libboost-all-dev

- Install sbt::

        echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | sudo tee /etc/apt/sources.list.d/sbt.list
        echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | sudo tee /etc/apt/sources.list.d/sbt_old.list
        curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | sudo -H gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/scalasbt-release.gpg --import
        sudo chmod 644 /etc/apt/trusted.gpg.d/scalasbt-release.gpg
        sudo apt update
        sudo apt install sbt

- Download and build all components::

        chmod +x init.sh
        ./init.sh

Afterwards, everything should be installed and `west` can be used to generate RISC-V designs.

Vivado
******

The Vivado toolchain is not part of this SDK and needs to be installed separately for Xilinx
platforms from `Xilinx's homepage`_. Download the Linux Self Extracting Web Installer for Version
2022.2 and install it. Select Vivado as product and Vivado HL WebPACK as Edition. You can use this
edition's license for free if you do not sell the bitstream, and disable everything except the
Artix-7 Platform to save disk storage. Elements except to find the Vivado toolchain under
``/opt/xilinx``.

.. code-block:: text

    chmod +x ~/Downloads/Xilinx_Unified_2022.2_1014_8888_Lin64.bin
    ~/Downloads/Xilinx_Unified_2022.2_1014_8888_Lin64.bin

.. _Xilinx's homepage: https://www.xilinx.com/support/download.html

Docker
######

The Elements SDK supports running inside Docker. Currently, only self-build images can be used.

Custom Image
************

A Docker Compose configuration is provided for systems that do not run with the recommended
versions. The Docker will have included all required packages for the SDK, except vendor toolchains.
Build the image (which can take some minutes).

.. code-block:: text

    docker-compose build

Next, start the Docker in the background.

.. code-block:: text

    docker-compose up -d

Afterwards, west can be used identical to the CLI.

.. code-block:: text

    sudo docker exec -it elements-sdk_zephyr_1 west build -p always -b helium1-ecpix5 \
        elements-zephyr-samples/demo/leds/

Finally, stop the Docker.

.. code-block:: text

    docker-compose stop

Development
***********

The docker image can also be used to develop. Therefore, the repos on the host system should be
forwarded to the container to make all changes public. Open the ``docker-compose.yml`` file and
uncomment the lines in ``volumes`` which should be made public.

Afterwards, go into `zephyr/` and download Zephyr with all repositories.

.. code-block:: text

    chmod +x init.sh
    .init.sh -z

GUI Support
***********

Some GUI applications require access to the host system's X server. Run the following command in
the host shell to grant them.

.. code-block:: text

    xhost local:root

Support
#######

The following boards are supported with this version.

+------------------------+--------------+------------------+---------------+------------+
| Board                  | Elements SoC | FPGA Board       | Vendor        | FPGA Chip  |
+========================+==============+==================+===============+============+
| helium1-ecpix5         | Helium1      | ECPIX-5          | LambdaConcept | ECP5       |
+------------------------+--------------+------------------+---------------+------------+
| helium1-nexysa7        | Helium1      | Nexys A7         | Digilent      | Artix-7    |
+------------------------+--------------+------------------+---------------+------------+
| neon1-ecpix5           | Neon1        | ECPIX-5          | LambdaConcept | ECP5       |
+------------------------+--------------+------------------+---------------+------------+
| neon1-nexysa7          | Neon1        | Nexys A7         | Digilent      | Artix-7    |
+------------------------+--------------+------------------+---------------+------------+
| argon1-ecpix5          | Argon1       | ECPIX-5          | LambdaConcept | ECP5       |
+------------------------+--------------+------------------+---------------+------------+

Usage
#####

Elements is fully integrated into the Zephyr west development process. Simply build software for
a Elements board. Afterwards, the build cache contains enough information to `synthesize` the
design.

.. code-block:: text

    west build -p always -b ecpix5/helium1 elements-zephyr-application/app/demo/
    west elements-synthesize
    west flash

Run `flash` with the `--spi`` argument to flash the bitstream into the SPI flash.

.. code-block:: text

    west flash --spi

Run `debug` and pass the OpenOCD binary path as well as search path.

.. code-block:: text

    west debug --openocd elements-openocd/src/openocd --openocd-search elements-openocd/

Additionally, a design can only be generated instead of synthesized to inspect the generated
Verilog code.

.. code-block:: text

    west build -p always -b ecpix5/helium1 elements-zephyr-application/app/demo/
    west elements-generate

Lastly, a design can be simulated and viewed with GTKWave.

.. code-block:: text

    west build -p always -b ecpix5/helium1 elements-zephyr-application/app/demo/
    west elements-simulate

Flash SPI-Nor Flash
###################

Pad the Zephyr binary because flashrom can't handle images which not align with pages.

.. code-block:: text

    dd if=/dev/zero of=flash.bin bs=1MiB count=32
    dd if=build/zephyr/zephyr.bin of=flash.bin conv=notrunc

Use a bus pirate to flash the padded Zephyr image to the SPI-Nor flash.

.. code-block:: text

    flashrom -p buspirate_spi:dev=/dev/ttyUSB0,spispeed=1M -c MT25QL256 -l layout.txt -i ROM -N -w flash.bin

Known Issues
############

* ``west debug`` only works with bitstreams synthesized with Vivado.
* F4PGA does not support PLLs on Xilinx architectures right now.
* PLLs are not working on the ECPIX-5 board when the bitstream gets
  loaded from the flash.

.. inclusion-end-marker-do-not-remove

License
#######

Copyright (c) 2024 aesc silicon. Released under the `MIT license`_.

.. _MIT license: ../COPYING.MIT
