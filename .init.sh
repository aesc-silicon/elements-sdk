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

west init -l zephyr

wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run
chmod +x zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run
./zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run -- -d $PWD/zephyr-sdk-${ZEPHYR_SDK_VERSION} -y -nocmake
rm zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run

wget https://github.com/stnolting/riscv-gcc-prebuilt/releases/download/rv32i-1.0.0/riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz
mkdir riscv32-unknown-elf
tar -xvf riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz -C riscv32-unknown-elf/
rm riscv32-unknown-elf.gcc-10.2.0.rv32i.ilp32.newlib.tar.gz

mkdir -p symbiflow/xc7/install
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O conda_installer.sh
bash conda_installer.sh -u -b -p ${PWD}/symbiflow/xc7/conda;
source "${PWD}/symbiflow/xc7/conda/etc/profile.d/conda.sh";
conda env create -f environment.yml

wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/201/20210325-000253/symbiflow-arch-defs-install-1c7a3d1e.tar.xz | tar -xJC ${PWD}/symbiflow/xc7/install
wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/201/20210325-000253/symbiflow-arch-defs-xc7a50t_test-1c7a3d1e.tar.xz | tar -xJC ${PWD}/symbiflow/xc7/install
wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/201/20210325-000253/symbiflow-arch-defs-xc7a100t_test-1c7a3d1e.tar.xz | tar -xJC ${PWD}/symbiflow/xc7/install

cd openocd
./bootstrap
./configure
make -j8
cd ../
