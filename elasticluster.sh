#! /bin/sh
#
# Seamless interface to Run ElastiCluster in a Docker image.
# Tries to install Docker if it cannot be found.
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#

me="$(basename $0)"


## defaults

docker_image_name='riccardomurri/elasticluster'
docker_image_tag='latest'


## helper functions

# see /usr/include/sysexit.h
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
      echo -n "${TXT_RED}${TXT_BOLD}$me: ERROR:${TXT_NOCOLOR} ";
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


## main

if ! have_command docker; then
    cat <<__EOF__
${TXT_BOLD}${TXT_YELLOW}${me} requires the 'docker' command,
which could not be found on \$PATH${TXT_NOCOLOR}${TXT_NORMAL}

I can now try to install Docker; this requires the 'sudo' command with
unrestricted administrative access.  If you do not have administrative
access to this machine, please ask your system administrator to
install Docker.

To know more about Docker, visit http://www.docker.com/

${TXT_BOLD}Press Ctrl+C now to abort, or Enter/Return to try installing Docker.${TXT_NORMAL}
__EOF__
    read _

    # work in a temporary directory
    require_command mktemp
    tmpdir=$(mktemp -d -t)
    if [ -z "$tmpdir" ]; then
        die $EX_CANTCREAT "Cannot create temporary download directory. Aborting."
    fi
    orig_wd="$PWD"
    trap "cd '$orig_wd'; rm -rf '$tmpdir';" EXIT TERM ABRT INT QUIT
    cd "$tmpdir"
    if have_command wget; then
        wget -nv -O get-docker.sh https://get.docker.com
    elif have_command curl; then
        curl -fsSL get.docker.com -o get-docker.sh
    else
        die $EX_UNAVAILABLE <<__EOF__

Docker installation requires either the 'wget' or the 'curl' commands,
and none is available. Aborting.

Please install either 'wget' or 'curl'.
__EOF__
    fi

    # run Docker installation
    if have_command sudo; then
        sudo /bin/sh get-docker.sh
        if [ $? -ne 0 ]; then
            die $EX_NOPERM "Failed to install Docker. Cannot continue."
        fi
    elif have_command su; then
        su -c "/bin/sh $PWD/get-docker.sh"
        if [ $? -ne 0 ]; then
            die $EX_NOPERM "Failed to install Docker. Cannot continue."
        fi
    else
        die $EX_UNAVAILABLE <<__EOF__

Docker installation requires either the 'sudo' or the 'su' commands,
and none is available. Aborting.

Please ask your system administrator to install Docker.
__EOF__
    fi

    cd "$orig_wd"
fi

# docker should have been installed by now...
require_command docker

# set up mount commands for host directories
volumes="-v $HOME/.ssh:/home/.ssh -v $HOME/.elasticluster:/home/.elasticluster"
if [ -n "$SSH_AUTH_SOCK" ]; then
    volumes="${volumes} -v $SSH_AUTH_SOCK:/home/.ssh-agent.sock"
fi

usage () {
    # show ElastiCLuster's main help
    docker run --rm --tty "${docker_image_name}:${docker_image_tag}" --help

    # add post-scriptum
cat <<EOF

In addition, the following options can be used to control execution of
ElastiCluster in Docker:

  --latest
      Same as '--pull --release latest'

  --pull
      Update Docker image to the latest version available

  --release TAG
      Use the Docker image with the given TAG (default tag: "latest")

EOF
}

# parse command-line for additional options
argv=''
while [ $# -gt 0 ]; do
    case "$1" in
        --config|-c)
            cfgfile="$2"
            volumes="${volumes} -v $(dirname "$cfgfile"):/mnt/config"
            argv="$argv --config /mnt/config"
            shift
            ;;
        --help|-h)
            usage;
            exit 0
            ;;
        --latest)
            pull='yes'
            docker_image_tag='latest'
            ;;
        --pull)
            pull='yes'
            ;;
        --release)
            docker_image_tag="$2"
            shift
            ;;
        *)
            argv="$argv $1"
            ;;
    esac
    shift
done

# put args back for elasticluster python to interpret
set -- $argv

# pull (update) Docker image
elasticluster_docker_image="${docker_image_name}:${docker_image_tag}"
if [ "$pull" = 'yes' ]; then
    docker pull "$elasticluster_docker_image"
fi

# ensure mount points exist
for dir in "$HOME/.ssh" "$HOME/.elasticluster"; do
    test -d "$dir" || mkdir -v "$dir"
done

# prepare environment to export to Docker
# (necessary e.g. to preserve OpenStack auth)
envfile=$(mktemp -t elasticluster.XXXXXXXXXXXX.env)
if [ -z "$envfile" ]; then
    die 1 "Cannot create temporary file."
fi
trap "rm -f '$envfile';" EXIT INT QUIT ABRT TERM
env HOME="$HOME" SSH_AUTH_SOCK=/home/.ssh-agent.sock > "$envfile"

# go!
exec docker run --rm --interactive --tty --env-file "$envfile" $volumes $elasticluster_docker_image "$@"
