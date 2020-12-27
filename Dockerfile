FROM ubuntu:20.04

ARG SSH_KEY

RUN apt-get update && apt-get install -y \
    ssh \
    git \
    libtool-bin \
    autotools-dev \
    automake \
    pkg-config \
    libyaml-dev \
    python3 \
    python3.8-dev \
    python3-pip \
    virtualenv \
    gdb

RUN curl https://storage.googleapis.com/git-repo-downloads/repo > /bin/repo
RUN chmod a+rx /bin/repo

# Authorize SSH Host
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan github.com > /root/.ssh/known_hosts

# Add the keys and set permissions
RUN echo "$SSH_KEY" > /root/.ssh/id_rsa &&\
  chmod 0600 /root/.ssh/id_rsa

RUN git clone git@github.com:phytec-labs/elements-sdk.git
WORKDIR elements-sdk/

RUN repo init -u git@github.com:phytec-labs/elements-manifest.git
RUN repo sync

RUN virtualenv -p python3 venv
RUN . venv/bin/activate

RUN pip3 install west
RUN pip3 install -r zephyr/scripts/requirements.txt

RUN west init -l zephyr
RUN west update

# download toolchain
RUN https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.12.0/zephyr-toolchain-riscv64-0.12.0-x86_64-linux-setup.run
RUN chmod +x zephyr-toolchain-riscv64-0.12.0-setup.run
RUN ./zephyr-toolchain-riscv64-0.12.0-setup.run -- -d $PWD/zephyr-sdk-0.12.0 -y

WORKDIR openocd
RUN ./bootstrap
RUN ./configure
RUN make -j8
RUN make install
WORKDIR ../

RUN rm /root/.ssh/id_rsa
