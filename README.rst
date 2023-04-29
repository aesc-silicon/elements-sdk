Elements SDK
============

The Elements software development kit (SDK) is a hard-/software co-design tool to develop, debug and maintain all stacks of an open-source System on Chip (SoC).

All RISC-V designs are integrated into the normal development flows of existing projects like Zephyr. Therefore, it can be integrated into existing development teams.

Features
########

* Open-Source FPGA flow
* Portfolio of configurable peripherals with OS support
* Predefined SOC platforms
* Supported Operation Systems: Zephyr
* Toolchain files are generated automatically

Focus on defining a custom SOC and writing your application!

Zephyr
######

Elements is fully integrated into Zephyr's meta-tool West and aims to provide RISC-V designs to
developers without deep knowledge about hardware design. Therefore, extra commands were added to
West to generate, synthesize, and simulate designs.

See `zephyr/README`_ for more information.

License
#######

Copyright (c) 2023 aesc silicon. Released under the `MIT license`_.

.. _MIT license: COPYING.MIT
.. _zephyr/README: zephyr/README.rst
