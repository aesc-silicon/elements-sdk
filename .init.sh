#!/bin/bash

if [ "$#" -ne 1 ]; then
	echo "usage: ./.init.sh <x.yy.z>"
	exit
fi

ZEPHYR_SDK_VERSION = $1

pip3 install west
. venv/bin/activate
pip3 install -r zephyr/scripts/requirements.txt

west init -l zephyr

wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run
chmod +x zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run
./zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run -- -d $PWD/zephyr-sdk-${ZEPHYR_SDK_VERSION} -y -nocmake
rm zephyr-toolchain-riscv64-${ZEPHYR_SDK_VERSION}-x86_64-linux-setup.run

cd openocd
./bootstrap
./configure
make -j8
cd ../
