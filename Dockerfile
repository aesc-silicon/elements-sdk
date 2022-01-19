FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive" TZ="Europe/Berlin"

RUN apt-get update && apt-get install -y \
    ssh \
    git \
    curl \
    libtool-bin \
    autotools-dev \
    automake \
    pkg-config \
    libyaml-dev \
    libssl-dev \
    gdb \
    ninja-build \
    python3 \
    python3.8-dev \
    python3-pip \
    virtualenv \
    openjdk-11-jre-headless \
    iverilog

RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list
RUN curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/scalasbt-release.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/scalasbt-release.gpg
RUN apt-get update && apt-get install -y sbt

RUN mkdir ~/.ssh
RUN ssh-keyscan github.com > ~/.ssh/known_hosts

# initialize SDK
RUN git clone https://github.com/phytec-labs/elements-sdk.git
WORKDIR elements-sdk/

RUN virtualenv -p python3 venv

RUN . venv/bin/activate && pip3 install pyyaml packaging

RUN ./elements.py init --manifest default.xml

# download sbt/java files
RUN cd zibal && sbt clean compile
