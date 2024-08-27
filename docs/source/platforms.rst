Hydrogen
########

This is a very basic platform as entry point for small microcontrollers with real-time
capabilities.

It contains a 32-bit RISC-V CPU (RV32IMC) without caches and an AXI4 crossbar. Moreover, an
on-chip RAM with a configurable size is connected as boot source and a mandatory machine timer and
platform-level interrupt controller (PLIC) is added.

Helium
######

The helium platform is a foundation for microcontroller designs with a needs for more performance
then the hydrogen.

It is very identical to the hydrogen platform but the CPU has instruction- and data-caches and
branch predicition.
