#! /bin/sh
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#
me="$(basename $0)"

usage () {
cat <<EOF
Usage: $me [options]

Build a Docker image running ElastiCluster.

Options:

  --help, -h
      Print this help text.
  --keep, -k
      Do not delete the temporary directory used for building
  --no-act, -n
      Do not actually execute any build command; just print
      what would have been done.
  --tag, -t NAME:TAG
      Passed unchanged to the 'docker build' command.
EOF
}


## helper functions

EX_OK=0           # successful termination
EX_USAGE=1        # command line usage error
EX_DATAERR=65     # data format error
EX_NOINPUT=66     # cannot open input
EX_NOUSER=67      # addressee unknown
EX_NOHOST=68      # host name unknown
EX_UNAVAILABLE=69 # service unavailable
EX_SOFTWARE=70    # internal software error
EX_OSERR=71       # system error (e.g., can't fork)
EX_OSFILE=72      # critical OS file missing
EX_CANTCREAT=73   # can't create (user) output file
EX_IOERR=74       # input/output error
EX_TEMPFAIL=75    # temp failure; user is invited to retry
EX_PROTOCOL=76    # remote error in protocol
EX_NOPERM=77      # permission denied
EX_CONFIG=78      # configuration error

have_command () {
    command -v "$1" >/dev/null 2>/dev/null
}

if have_command tput; then
    TXT_NORMAL=$(tput sgr0)

    TXT_BOLD=$(tput bold)
    TXT_DIM=$(tput dim)
    TXT_STANDOUT=$(tput smso)

    TXT_BLACK=$(tput setaf 0)
    TXT_BLUE=$(tput setaf 4)
    TXT_CYAN=$(tput setaf 6)
    TXT_GREEN=$(tput setaf 2)
    TXT_MAGENTA=$(tput setaf 5)
    TXT_RED=$(tput setaf 1)
    TXT_WHITE=$(tput setaf 7)
    TXT_YELLOW=$(tput setaf 3)
    TXT_NOCOLOR=$(tput op)
else
    TXT_NORMAL=''

    TXT_BOLD=''
    TXT_DIM=''
    TXT_STANDOUT=''

    TXT_BLACK=''
    TXT_BLUE=''
    TXT_CYAN=''
    TXT_GREEN=''
    TXT_MAGENTA=''
    TXT_RED=''
    TXT_WHITE=''
    TXT_YELLOW=''
    TXT_NOCOLOR=''
fi

die () {
  rc="$1"
  shift
  (
      echo -n "${TXT_BOLD}$me: ${TXT_RED}ERROR:${TXT_NOCOLOR} ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi
      echo -n "${TXT_NORMAL}"
  ) 1>&2
  exit $rc
}

warn () {
    (
        echo -n "$me: ${TXT_YELLOW}WARNING:${TXT_NOCOLOR} ";
        if [ $# -gt 0 ]; then echo "$@"; else cat; fi
    ) 1>&2
}

require_command () {
  if ! have_command "$1"; then
    die 1 "Could not find required command '$1' in system PATH. Aborting."
  fi
}

is_absolute_path () {
    expr match "$1" '/' >/dev/null 2>/dev/null
}


## parse command-line

short_opts='hknt:'
long_opts='dry-run,help,keep,no-act,just-print,tag:'

# test which `getopt` version is available:
# - GNU `getopt` will generate no output and exit with status 4
# - POSIX `getopt` will output `--` and exit with status 0
getopt -T > /dev/null
rc=$?
if [ "$rc" -eq 4 ]; then
    # GNU getopt
    args=$(getopt --name "$me" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- $args
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    set -- $args
fi

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        -k|--keep) keep=yes ;;
        -n|--dry-run|--no-act|--just-print) maybe=echo ;;
        -t|--tag) opt_tag="-t $2"; shift ;;
        --) shift; break ;;
    esac
    shift
done


## main

require_command docker
require_command mktemp

# sanity check
if ! [ -d 'elasticluster' ] && ! [ 'elasticluster/__init__.py' ]; then
    die $EX_NOINPUT \
        "Please run this script in the top-level directory of ElastiCluster sources."
fi
if ! [ -d '.git' ]; then
    die $EX_DATAERR \
        "Please run this script in Git source checkout of ElastiCluster sources."
fi

# make temporary build directory
build_dir=$(mktemp -d "elasticluster.${me}.XXXXXXXX.d")
if [ -z "$build_dir" ]; then
    die $EX_CANTCREAT "Cannot create build directory. Aborting."
fi
if [ "$keep" != 'yes' ]; then
    trap "rm -rf '$build_dir';" EXIT ABRT INT QUIT TERM
fi

# do it!
$maybe set -ex
$maybe git clone "$PWD" "$build_dir"
$maybe cd "$build_dir"
if [ -z "$maybe" ]; then
    docker build --iidfile id.txt $opt_tag . | tee build.log
    docker tag $(cat id.txt) riccardomurri/elasticluster:latest
else
    $maybe docker build .
fi
