# Dockerfile for ElastiCluster
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
# Originally contributed by Hatef Monajemi, 2017
# (see https://github.com/gc3-uzh-ch/elasticluster/pull/504#issuecomment-343693251)
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#

FROM python:2.7-slim


# Prepare the image:
# 1. move user `root`'s home to `/home` where we shall mount
#    the corresponding host directories where user data resides
# 2. create mountpoints for volumes
RUN : \
    && mkdir -p /usr/src/elasticluster /home/.ssh /home/.elasticluster \
    && sed -re '1s|:/root:|:/home:|' -i /etc/passwd \
    ;
VOLUME /home/.ssh
VOLUME /home/.elasticluster


# Copy ElastiCluster sources
COPY ./ /usr/src/elasticluster/
COPY ./etc/docker/sitecustomize.py /usr/local/lib/python2.7/site-packages/sitecustomize.py
COPY ./etc/docker/environment /etc/environment


# Install ElastiCluster
#
# This happens in three stages:
# 1. install OS-level deps of Python packages; note that we install
#    explicitly both the development version of a library (needed by
#    `setup.py` in some Python packages) and the DLL-only version of
#    the same -- this is to avoid that DDLs are removed by
#    `apt-get autoremove` later on
# 2. install ElastiCluster and dependent Python packages (with `pip install`)
# 3. cleanup and remove software used for installation to get a leaner image
#
WORKDIR /usr/src/elasticluster/
RUN : \
    && apt-get update \
    && apt-get install --yes --no-install-recommends \
           make \
           g++ \
           gcc \
           libc6 libc6-dev \
           libexpat1 libexpat1-dev \
           libffi6 libffi-dev \
           libssl1.0.0 libssl-dev \
           openssh-client \
    && pip install -e . \
    && rm -rf /home/.cache \
    && apt-get remove --purge -y \
           make \
           g++ \
           gcc \
           libc6-dev \
           libexpat1-dev \
           libffi-dev \
           libssl-dev \
    && apt-get autoremove --yes \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/cache/debconf/*.dat-old \
    ;


# Run this command by default
WORKDIR /home
ENTRYPOINT ["/usr/local/bin/python", "-m", "elasticluster"]
CMD ["--help"]
