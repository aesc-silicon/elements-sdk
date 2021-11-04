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
    python3 \
    python3.8-dev \
    python3-pip \
    virtualenv \
    gdb \
    curl

RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list
RUN curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/scalasbt-release.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/scalasbt-release.gpg
RUN apt-get update && apt-get install -y sbt

# initialize SDK
RUN git clone https://github.com/phytec-labs/elements-sdk.git
WORKDIR elements-sdk/

RUN virtualenv -p python3 venv

RUN pip3 install pyyaml packaging

RUN python3 elements-fpga.py init
