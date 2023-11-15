#!/bin/bash

ELEMENTS_RELEASE=release-v23.1
ELEMENTS_DEV=v3.5.0-aesc
ZEPHYR_SDK_RELEASE=0.16.3

OSS_CAD_SUITE_DATE="2023-10-30"
OSS_CAD_SUITE_STAMP="${OSS_CAD_SUITE_DATE//-}"

F4PGA_INSTALL_DIR="${PWD}/f4pga"
F4PGA_XC7_PACKAGES='install-xc7 xc7a50t_test xc7a100t_test'
F4PGA_XC7_TIMESTAMP='20220920-124259'
F4PGA_XC7_HASH='007d1c1'


function init_venv {
	virtualenv -p python3.10 .venv
	if [ "$1" = false ]; then
		source .venv/bin/activate
	else
		echo "Installing all Python packages on host system!"
	fi
	pip install west
	pip install checksumdir

	if [ "$2" = false ]; then
		git clone https://github.com/aesc-silicon/elements-zephyr -b $ELEMENTS_RELEASE
	else
		git clone https://github.com/aesc-silicon/elements-zephyr -b $ELEMENTS_DEV
	fi
	west init --local --mf west.yml elements-zephyr/
	west update
	west zephyr-export
	pip install -r elements-zephyr/scripts/requirements.txt
}

function fetch_zephyr_sdk {
	wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_RELEASE}/zephyr-sdk-${ZEPHYR_SDK_RELEASE}_linux-x86_64.tar.xz
	wget -O - https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_RELEASE}/sha256.sum | shasum --check --ignore-missing
	tar xvf zephyr-sdk-${ZEPHYR_SDK_RELEASE}_linux-x86_64.tar.xz
	cd zephyr-sdk-${ZEPHYR_SDK_RELEASE}
	./setup.sh -c
	cd ../
	rm zephyr-sdk-${ZEPHYR_SDK_RELEASE}_linux-x86_64.tar.xz
}

function fetch_oss_cad_suite_build {
	wget https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_SUITE_DATE}/oss-cad-suite-linux-x64-${OSS_CAD_SUITE_STAMP}.tgz
	tar -xvf oss-cad-suite-linux-x64-${OSS_CAD_SUITE_STAMP}.tgz
	rm oss-cad-suite-linux-x64-${OSS_CAD_SUITE_STAMP}.tgz
}

function fetch_f4pga {
	git clone https://github.com/chipsalliance/f4pga-examples
	wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O f4pga-examples/conda_installer.sh
}

function fetch_f4pga_xc7 {
	FPGA_FAM=xc7

	cd f4pga-examples/
	bash conda_installer.sh -u -b -p $F4PGA_INSTALL_DIR/$FPGA_FAM/conda;
	source "$F4PGA_INSTALL_DIR/$FPGA_FAM/conda/etc/profile.d/conda.sh";
	conda env create -f $FPGA_FAM/environment.yml

	mkdir -p $F4PGA_INSTALL_DIR/$FPGA_FAM

	for PKG in $F4PGA_XC7_PACKAGES; do
		wget -qO- https://storage.googleapis.com/symbiflow-arch-defs/artifacts/prod/foss-fpga-tools/symbiflow-arch-defs/continuous/install/${F4PGA_XC7_TIMESTAMP}/symbiflow-arch-defs-${PKG}-${F4PGA_XC7_HASH}.tar.xz | tar -xJC $F4PGA_INSTALL_DIR/${FPGA_FAM}
	done
	cd ../
}

function build_nextpnr_xilinx {
	mkdir nextpnr-xilinx
	cd nextpnr-xilinx

	git clone --recurse-submodules -j8 https://github.com/f4pga/prjxray.git
	cd prjxray
	mkdir build
	cd build
	cmake -DCMAKE_INSTALL_PREFIX=${PWD}/../../ ..
	make -j$(nproc)
	cd ../../

	git clone --recurse-submodules -j8 https://github.com/openXC7/nextpnr-xilinx.git
	cd nextpnr-xilinx
	cmake -DARCH=xilinx -DBUILD_GUI=OFF -DCMAKE_INSTALL_PREFIX=${PWD}/../ .
	make -j$(nproc)
	make install
	cd ../
}

function print_usage {
	echo "init.sh [-z] [-v] [-d] [-f] [-h]"
	echo "\t-z: Download and install Zephyr only"
	echo "\t-v: Don't install into virtualenv"
	echo "\t-d: Download Zephyr development branch"
	echo "\t-f: Don't download the F4PGA toolchain"
	echo "\t-h: Show this help message"
}

no_venv=false
dev=false
skip_f4pga=false
while getopts zvdfh flag
do
	case "${flag}" in
		z) scope="ZEPHYR";;
		v) no_venv=true;;
		d) dev=true;;
		f) skip_f4pga=true;;
		h) print_usage
			exit 1;;
	esac
done

if ! test -d ".venv"; then
	init_venv $no_venv $dev
fi

if test "$scope" == "ZEPHYR"; then
	echo "Initialize scope set to Zephyr only. Stop here!"
	exit 0
fi

if ! test -d "zephyr-sdk-${ZEPHYR_SDK_RELEASE}"; then
	fetch_zephyr_sdk
fi
if ! test -d "oss-cad-suite"; then
	fetch_oss_cad_suite_build
fi
if ! test -d "f4pga-examples"; then
	if [ "$skip_f4pga" = false ]; then
		fetch_f4pga
		fetch_f4pga_xc7
	else
		echo "Skipped fetching F4PGA toolchain."
	fi
fi

if ! test -f "nextpnr-xilinx/bin/nextpnr-xilinx"; then
	build_nextpnr_xilinx
fi
