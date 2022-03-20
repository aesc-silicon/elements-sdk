#!/bin/bash

if [ "$#" -ne 1 ]; then
	echo "usage: ./.init.sh <x.yy.z>"
	exit
fi

ZEPHYR_SDK_VERSION=$1

python3 -m pip install west
python3 -m pip install pyelftools
. venv/bin/activate
pip3 install -r zephyr/scripts/requirements.txt
pip3 install -r requirements.txt

west init -l zephyr

wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-linux-x86_64-setup.run
if ! test -f zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-linux-x86_64-setup.run; then
	echo "wget error: Unable to fetch SDK"
	exit 2
fi
chmod +x zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-linux-x86_64-setup.run
./zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-linux-x86_64-setup.run -- -d $PWD/zephyr-sdk-${ZEPHYR_SDK_VERSION} -y -nocmake
rm zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-linux-x86_64-setup.run

wget https://github.com/stnolting/riscv-gcc-prebuilt/releases/download/rv32i-2.0.0/riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz
if ! test -f riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz; then
	echo "wget error: Unable to fetch riscv32-unknown-gcc"
	exit 2
fi
mkdir riscv32-unknown-elf
tar -xvf riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz -C riscv32-unknown-elf/
rm riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz

INSTALL_DIR=${PWD}/symbiflow
mkdir -p $INSTALL_DIR/xc7/install
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O conda_installer.sh
bash conda_installer.sh -u -b -p $INSTALL_DIR/xc7/conda;

source "${INSTALL_DIR}/xc7/conda/etc/profile.d/conda.sh";
conda env create -f ${PWD}/environment.yml

wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/459/20211116-000105/symbiflow-arch-defs-install-ef6fff3c.tar.xz | tar -xJC $INSTALL_DIR/xc7/install
wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/459/20211116-000105/symbiflow-arch-defs-xc7a50t_test-ef6fff3c.tar.xz | tar -xJC $INSTALL_DIR/xc7/install
wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/459/20211116-000105/symbiflow-arch-defs-xc7a100t_test-ef6fff3c.tar.xz | tar -xJC $INSTALL_DIR/xc7/install

cd openocd
./bootstrap && ./configure && make -j `nproc`
cd ../

if ! test -f "openocd/src/openocd"; then
	echo "openocd does not exist."
	exit 2
fi

git clone https://github.com/Kitware/CMake.git cmake -b v3.20.0
cd cmake
./bootstrap && make -j `nproc`
cd ../

if ! test -f "cmake/bin/cmake"; then
	echo "cmake does not exist."
	exit 2
fi

git clone https://github.com/verilator/verilator verilator -b v4.218
cd verilator
autoconf && ./configure && make -j `nproc`
cd ../

if ! test -f "verilator/bin/verilator"; then
	echo "verilator does not exist."
	exit 2
fi
