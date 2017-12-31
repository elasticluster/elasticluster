#! /bin/sh
#
# THIS FILE IS CONTROLLED BY ELASTICLUSTER
# local modifications will be overwritten
# the next time `elasticluster setup` is run!


#
# Shell script to check that all features needed for SLURM cgroup
# support are available and enabled on this system.
#
# This script is part of ElastiCluster and can be modified
# and distributed under the same terms.
#
# Copyright 2017, 2018 Riccardo Murri <riccardo.murri@gmail.com>
# Parts of this script have been adapted from
# https://github.com/moby/moby/blob/master/contrib/check-config.sh
#
me="$(basename $0)"

usage () {
cat <<EOF
Usage: $me [options]

Check that all features needed for SLURM cgroup support are available
and enabled on this system.

Options:

  --abort        Stop at first error (default)
  --color {yes|no|auto}
                 Whether to use terminal color codes in output.
                 If 'auto', then use color iff STDOUT is connected
                 to a terminal.
  --kconfig, -c PATH
                 Read Linux kernel configuration file at PATH.
  --report, --keep-going, -k
                 Do not stop at first error.
  --verbose, -v  Print out results.
  --help, -h     Print this help text.


EOF
}


## defaults

cgroups='general blkio cpuacct cpuset devices freezer memory'
color='auto'
on_error='abort'

## exit codes

EX_OK=0
EX_USAGE=1

# see /usr/include/sysexit.h
EX_DATAERR=65
EX_NOINPUT=66
EX_UNAVAILABLE=69
EX_SOFTWARE=70
EX_OSERR=71
EX_OSFILE=72


## helper functions

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

with_color () {
    local color="$1";
    shift;

    local pre="${TXT_NOCOLOR}";
    local post="${TXT_NOCOLOR}";

    case "$color" in
        bold*) pre="${TXT_BOLD}";;
        dim*) pre="${TXT_DIM}";;
        standout*) pre="${TXT_STANDOUT}";;
    esac

    case "$color" in
        *black)       pre="${pre}${TXT_BLACK}";;
        *blue)        pre="${pre}${TXT_BLUE}";;
        *cyan)        pre="${pre}${TXT_CYAN}";;
        *green)       pre="${pre}${TXT_GREEN}";;
        *magenta)     pre="${pre}${TXT_MAGENTA}";;
        *red)         pre="${pre}${TXT_RED}";;
        *white)       pre="${pre}${TXT_WHITE}";;
        *yellow)      pre="${pre}${TXT_YELLOW}";;
        none|nocolor) pre="${TXT_NOCOLOR}";;
    esac

    echo -n "${pre}"; echo -n "$@"; echo "${post}";
}

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

short_opts='c:hkv'
long_opts='abort,color:,help,kconfig:,report,verbose'

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
        --abort)
            on_error='abort'
            ;;
        -c|--kconfig)
            KCONFIG="$2"
            shift
            ;;
        --color)
            case "$2" in
                auto)          color='auto' ;;
                always|yes|'') color='yes' ;;
                never|no)      color='no' ;;
            esac
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -k|--report|--keep-going)
            on_error='report'
            ;;
        -v|--verbose)
            verbose='yes'
            ;;
        --)
            shift
            break
            ;;
    esac
    shift
done

if [ $# -eq 0 ]; then
    set -- $cgroups
fi


## main

# decide whether output is colored or not
if [ "$color" = 'auto' ]; then
    if [ -t 1 ]; then
        color='yes'
    else
        color='no'
    fi
fi

# turn off color?
if [ "$color" != 'yes' ]; then
    with_color() { shift; echo "$@"; }
fi


# find kernel config file if not given
if [ -z "$KCONFIG" ]; then
    kernel_version=$(uname -r)
    # kernel_major=$(expr match "$kernel_version" '\([0-9]\+\)\.[0-9]\+.*')
    # kernel_minor=$(expr match "$kernel_version" '[0-9]\+\.\([0-9]\+\)\.[0-9]\+.*')

    for kconfig in \
        /proc/config.gz \
        "/boot/config-${kernel_version}" \
        "/usr/src/linux-${kernel_version}/.config" \
        "/usr/src/linux/.config" \
        ;
    do
        if [ -r "$kconfig" ]; then
            KCONFIG="$kconfig"
            break
        fi
    done
fi
if [ -z "$KCONFIG" ]; then
    die $EX_OSFILE "Cannot locate Linux kernel config file; please specify path with '--kconfig'."
fi


# machinery to check kernel config
require_command zcat

is_set() {
    cfg="${2:-$KCONFIG}"
    case "$cfg" in
        *.gz) zcat "$cfg" | grep -q "$1=[ym]" ;;
        *) grep -q -e "$1=[ym]" "$cfg" ;;
    esac
}


_enabled=$(with_color green 'yes')
_disabled=$(with_color red 'no')

check_kconfig_setting() {
    local config_opt="CONFIG_$1";
    local rc="$EX_SOFTWARE";

    if is_set "${config_opt}"; then
        if [ "$verbose" = 'yes' ]; then
            echo "  ${config_opt}: $_enabled"
        fi
        rc=0
    else
        if [ "$verbose" = 'yes' ]; then
            echo "  ${config_opt}: $_disabled"
        fi
        if [ "$on_error" = 'abort' ]; then
            die $EX_UNAVAILABLE "Kernel config option ${config_opt} missing or disabled."
        else
            rc=1
            FAILED=$(expr 1 + $FAILED)
        fi
    fi
    return $rc
}

check_kconfig_settings() {
    for flag in "$@"; do
        check_kconfig_setting "$flag"
    done
}


FAILED=0

for cgroup in "$@"; do
    if [ "$verbose" = 'yes' ]; then
        echo "${cgroup}:"
    fi

    case "$cgroup" in
        # see file `init/Kconfig` in the Linux kernel sources
        # for the meaning of most of these options
        general)
            check_kconfig_settings CGROUPS
            ;;
        blkio)
            check_kconfig_settings BLK_CGROUP
            ;;
        cpu)
            check_kconfig_settings CGROUP_SCHED
            ;;
        cpuacct)
            check_kconfig_settings CGROUP_SCHED CGROUP_CPUACCT
            ;;
        cpuset)
            check_kconfig_settings CGROUP_SCHED CPUSETS
            ;;
        devices)
            check_kconfig_settings CGROUP_DEVICE
            ;;
        freezer)
            check_kconfig_settings CGROUP_FREEZER
            ;;
        memory)
            check_kconfig_settings MEMCG MEMCG_SWAP
            # MEMCG_SWAP_ENABLED
            ;;
    esac

done

exit $FAILED
