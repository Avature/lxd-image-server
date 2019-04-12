# Build lxd-image-server's Debian package within a container for any platform
#
#   docker build --tag lxd-image-server-builder --build-arg distro=debian:9 .
#   docker build --tag lxd-image-server-builder --build-arg distro=ubuntu:bionic .
#
#   mkdir -p dist && docker run --rm lxd-image-server-builder tar -C /dpkg -c . | tar -C dist -xv

ARG distro="ubuntu:bionic"
FROM ${distro} AS dpkg-build
RUN apt-get update -qq -o Acquire::Languages=none \
    && env DEBIAN_FRONTEND=noninteractive apt-get install \
        -yqq --no-install-recommends -o Dpkg::Options::=--force-unsafe-io \
        build-essential debhelper dh-exec python3 python-pip python-dev dh-virtualenv \
    && apt-get clean && rm -rf "/var/lib/apt/lists"/*
WORKDIR /dpkg-build
COPY ./ ./
RUN dpkg-buildpackage -us -uc -b && mkdir -p /dpkg && cp -pl /lxd-image-server[-_]* /dpkg  && dpkg-deb -I /dpkg/lxd-image-server_*.deb
