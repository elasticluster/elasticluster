#! /bin/sh
#

## defaults

me="$(basename $0)"

# where Ansible looks for a Python interpreter
default_python='/usr/bin/python'


## usage
usage () {
cat <<EOF
Usage: $me [options] [PATH]

Ensure that Ansible's basic Python requirements are installed.
If a Python 2.x interpreter does not exists at PATH (default:
'$default_python'), then try to install one using distro-specific
installation commands.

Options:

  --help, -h
      Print this help text.

EOF
}


## helper functions

# see /usr/include/sysexit.h
EX_USAGE=1
EX_UNAVAILABLE=69
EX_SOFTWARE=70
EX_OSERR=71

have_command () {
    command -v "$1" >/dev/null 2>/dev/null
}

die () {
    rc="$1"
    shift
    (echo -n "$me: ERROR: "; if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
    exit $rc
}

warn () {
    (echo -n "$me: WARNING: "; if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
}

require_command () {
    if ! have_command "$1"; then
        die 1 "Could not find required command '$1' in system PATH. Aborting."
    fi
}

do_or_die () {
    echo "Running installation command '$@' ..."
    "$@"; rc=$?
    if [ ${rc:-1} -ne 0 ]; then
        die $EX_OSERR "Installation command '$@' failed. Aborting."
    fi
    return $rc
}

## parse command-line

short_opts='h'
long_opts='help'

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
        --help|-h) usage; exit 0 ;;
        --) shift; break ;;
    esac
    shift
done

python="${1:-$default_python}"


## main

if ! [ -x "$python" ]; then

    # detect what Linux distribution we're running on
    # (this code originally from: https://unix.stackexchange.com/a/6348/274)
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        os=$ID
        ver=$VERSION_ID
    elif have_command lsb_release; then
        # linuxbase.org
        os=$(lsb_release -si)
        ver=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        # For some versions of Debian/Ubuntu without lsb_release command
        . /etc/lsb-release
        os=$DISTRIB_ID
        ver=$DISTRIB_RELEASE
    elif [ -f /etc/debian_version ]; then
        # Older Debian/Ubuntu/etc.
        os='Debian'
        ver=$(cat /etc/debian_version)
    elif [ -f /etc/redhat-release ]; then
        # Older Red Hat, CentOS, etc.
        os='RedHat'
    else
        die $EX_UNAVAILABLE "Unsupported OS - cannot install Python 2.7"
    fi

    # try to install Python 2.7 (or 2.6 + simplejson)
    case "$os" in
        [Dd]ebian|[Uu]buntu)
            # need to update otherwise the following `apt-get install`
            # may fail as the local DB of package versions is outdated
            apt-get update
            do_or_die apt-get install -y python2.7 python-simplejson
            ;;
        [Rr]ed[Hh]at)
            case "$ver" in
                7*) do_or_die yum install -y python2 python2-simplejson ;;
                6*) do_or_die yum install -y python2 python-simplejson ;;
            esac
            ;;
    esac

fi

# cross check that Python exists
if ! test -x "$python"; then
    die $EX_SOFTWARE "Python interpreter '$python' not found, even after installation. Aborting."
fi

# output Python version and exit successfully
echo "Displaying installed Python version ..."
exec "$python" --version
