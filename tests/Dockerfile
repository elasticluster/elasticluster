#
# build a Docker image for running ElastiCluster tests with different
# Python versions.
#
# Build from ElastiCluster sources root directory with:
#
#         docker build -t s3it/pythonista tests.
#
# Then run with:
#
#         docker run --rm -i -t -u 1000 -v $PWD:/src -w /src s3it/pythonista
#

# well supported base image with all Python versions and popular tools preinstalled
FROM ikalnitsky/pythonista

# create a user corresponding to the local user
RUN useradd -d /src -u 1000 -s /bin/bash -U --no-log-init python

# add
RUN apt-get update && apt-get install -y \
  build-essential ca-certificates gcc g++

