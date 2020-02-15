# Dockerfile for ElastiCluster
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
# Originally contributed by Hatef Monajemi, 2017
# (see https://github.com/gc3-uzh-ch/elasticluster/pull/504#issuecomment-343693251)
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#

FROM python:2.7-alpine


# Prepare the image:
# 1. move user `root`'s home to `/home` where we shall mount
#    the corresponding host directories where user data resides
# 2. create mountpoints for volumes
RUN : \
    && mkdir -p /home /home/.ssh /home/.elasticluster \
    && sed -re '1s|:/root:|:/home:|' -i /etc/passwd \
    ;
VOLUME /home/.ssh
VOLUME /home/.elasticluster


# Copy ElastiCluster sources
COPY ./ /home

# TODO: clean the following comments

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
WORKDIR /home


# install ca-certificates so that HTTPS works consistently
# the other runtime dependencies for Python are installed later

RUN set -ex \
    && apk update \
    && apk add --no-cache ca-certificates \
    && apk update \
    && apk add --no-cache --virtual .fetch-deps\
           curl \
           g++ \
           gcc \
           libc-dev \
           expat expat-dev \
           libffi libffi-dev \
           libssl1.1 openssl-dev \
           make \
           openssh-client \
    && pip install -e . \
    && rm -rf /home/.cache \
    && apk del .fetch-deps \
    ;


# Deploy adapter script (needs to be done last, otherwise it fails
# when running Python commands above)
COPY ./etc/docker/sitecustomize.py /usr/local/lib/python2.7/site-packages/sitecustomize.py


# Run this command by default
ENTRYPOINT ["/usr/local/bin/python", "-m", "elasticluster"]
CMD ["--help"]
