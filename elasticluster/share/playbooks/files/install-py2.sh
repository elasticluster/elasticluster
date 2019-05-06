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

# eatmydata support
real_python=$(expr "$python" : '\(.*\)+eatmydata')
if [ -n "$real_python" ]; then
    # install `libeatmydata.so` and the `eatmydata` command
    case "$os" in
        [Dd]ebian|[Uu]buntu)
            apt-get install -y eatmydata
            ;;
        [Rr]ed[Hh]at)
            case "$ver" in
                7*)
                    sudo yum install -y yum-plugin-copr
                    sudo yum copr enable -y loveshack/livhpc
                    ;;
                6*)
                    # CentOS 6 does not have YUM's COPR plugin so just create the repo file
                    mkdir -p /etc/yum.repos.d
                    cat > /etc/yum.repos.d/copr-livhpc.repo <<__EOF__
# see: https://copr.fedorainfracloud.org/coprs/loveshack/livhpc/
[loveshack-livhpc]
name=Copr repo
baseurl=https://copr-be.cloud.fedoraproject.org/results/loveshack/livhpc/epel-6-$basearch/
type=rpm-md
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://copr-be.cloud.fedoraproject.org/results/loveshack/livhpc/pubkey.gpg
repo_gpgcheck=0
enabled=1
enabled_metadata=1
__EOF__
                    ;;
            esac
            sudo yum install -y libeatmydata
            ;;
    esac
    # create wrapper script to call Python with libeatmydata preloaded
    cat > "$python" <<__EOF__
#! /bin/sh

exec /usr/bin/eatmydata -- '$real_python' "\$@"
__EOF__
    chmod a+rx "$python"
else
    real_python="$python"
fi

# cross check that Python exists
if ! test -x "$real_python"; then
    die $EX_SOFTWARE "Python interpreter '$real_python' not found, even after installation. Aborting."
fi

# output Python version and exit successfully
echo "Displaying installed Python version ..."
exec "$python" --version
