FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive" TZ="Europe/Berlin"

RUN apt-get update && apt-get install -y \
    ssh \
    git \
    libtool-bin \
    autotools-dev \
    automake \
    pkg-config \
    libyaml-dev \
    cmake \
    python3 \
    python3.8-dev \
    python3-pip \
    virtualenv \
    gdb \
    curl

RUN curl https://storage.googleapis.com/git-repo-downloads/repo > /bin/repo
RUN chmod a+rx /bin/repo

# initialize SDK
RUN git clone https://github.com/phytec-labs/elements-sdk.git
WORKDIR elements-sdk/

RUN python3 /bin/repo init -u https://github.com/phytec-labs/elements-manifest.git
RUN python3 /bin/repo sync

RUN virtualenv -p python3 venv

RUN pip3 install west
RUN venv/bin/pip install -r zephyr/scripts/requirements.txt

RUN venv/bin/west init -l zephyr

# download toolchain
RUN wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.12.0/zephyr-toolchain-riscv64-0.12.0-x86_64-linux-setup.run
RUN chmod +x zephyr-toolchain-riscv64-0.12.0-setup.run
RUN ./zephyr-toolchain-riscv64-0.12.0-setup.run -- -d $PWD/zephyr-sdk-0.12.0 -y -nocmake

# install openocd
WORKDIR openocd
RUN ./bootstrap
RUN ./configure
RUN make -j8
RUN make install

WORKDIR ../
