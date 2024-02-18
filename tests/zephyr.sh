#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
LOGS=`date +%F_%T`

LOCATION="${PWD}/$(dirname $0)"
ZEPHYR_PATH="${LOCATION}/../zephyr"
LOG_PATH="${LOCATION}/${LOGS}"

function synthesize_board {
	echo -e "Start synthesizing $1"
	rm -rf build
	echo -e "\tBuild: ..."
	tput cuu1
	west build -p always -b $1 $2 > ${LOG_PATH}/synthesize/$1.build.log 2>&1
	if [ $? -eq 0 ]
	then
		tput el
		echo -e "\tBuild: ${GREEN}PASSED${NC}"
	else
		tput el
		echo -e "\tBuild: ${RED}FAILED${NC}"
		exit 1
	fi
	echo -e "\tGenerate: ..."
	tput cuu1
	west generate > ${LOG_PATH}/synthesize/$1.gen.log 2>&1
	if [ $? -eq 0 ] 
	then
		tput el
		echo -e "\tGenerate: ${GREEN}PASSED${NC}"
	else
		tput el
		echo -e "\tGenerate: ${RED}FAILED${NC}"
		exit 1
	fi
	echo -e "\tSynthesize: ..."
	tput cuu1
	west synthesize > ${LOG_PATH}/synthesize/$1.syn.log 2>&1
	if [ $? -eq 0 ] 
	then
		tput el
		echo -e "\tSynthesize: ${GREEN}PASSED${NC}"
	else
		tput el
		echo -e "\tSynthesize: ${RED}FAILED${NC}"
		exit 1
	fi
}

function test_board {
	echo -e "Start testing $1 - $2"
	rm -rf build
	echo -e "\tBuild: ..."
	tput cuu1
	application=elements-zephyr-samples/startup/$2
	west build -p always -b $1 $application > ${LOG_PATH}/test/$1.$2.build.log 2>&1
	if [ $? -eq 0 ]
	then
		tput el
		echo -e "\tBuild: ${GREEN}PASSED${NC}"
	else
		tput el
		echo -e "\tBuild: ${RED}FAILED${NC}"
		exit 1
	fi
	echo -e "\tTest: ..."
	tput cuu1
	west test $2 > ${LOG_PATH}/test/$1.$2.test.log 2>&1
	if [ $? -eq 0 ] 
	then
		tput el
		echo -e "\tTest: ${GREEN}PASSED${NC}"
	else
		tput el
		echo -e "\tTest: ${RED}FAILED${NC}"
		exit 1
	fi

}

source ${ZEPHYR_PATH}/.venv/bin/activate
mkdir -p ${LOG_PATH}/synthesize
mkdir -p ${LOG_PATH}/test/
echo "Generating log directory: ${LOG_PATH}"
cd ${ZEPHYR_PATH}

synthesize_board hydrogen1-ecpix5 elements-zephyr-samples/demo/leds
test_board hydrogen1-ecpix5 boot
test_board hydrogen1-ecpix5 mtimer
test_board hydrogen1-ecpix5 reset

synthesize_board helium1-ecpix5 elements-zephyr-samples/demo/leds
test_board helium1-ecpix5 boot
test_board helium1-ecpix5 mtimer
test_board helium1-ecpix5 reset

synthesize_board hydrogen1-nexysa7 elements-zephyr-samples/demo/leds
test_board hydrogen1-nexysa7 boot
test_board hydrogen1-nexysa7 mtimer
test_board hydrogen1-nexysa7 reset

synthesize_board helium1-nexysa7 elements-zephyr-samples/demo/leds
test_board helium1-nexysa7 boot
test_board helium1-nexysa7 mtimer
test_board helium1-nexysa7 reset

synthesize_board lithium1-ecpix5 elements-zephyr-samples/demo/leds
