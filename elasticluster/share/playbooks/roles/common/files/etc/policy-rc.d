#! /bin/sh
#
# THIS FILE IS CONTROLLED BY ELASTICLUSTER
# local modifications will be overwritten
# the next time `elasticluster setup` is run!


# Prevent auto-starting daemons upon package installation.
# See:
# 1. https://people.debian.org/~hmh/invokerc.d-policyrc.d-specification.txt
# 2. https://major.io/2014/06/26/install-debian-packages-without-starting-daemons/

me="$(basename $0)"

usage () {
cat <<EOF
Usage: $me [options] "initscript ID" "actions" ["runlevel"]

Determine local system policy with respect to taking "actions" upon service
"initscript ID" on part of 'invoke-rc.d'.

For a detailed specification, see:
https://people.debian.org/~hmh/invokerc.d-policyrc.d-specification.txt

Options:

  --quiet     No error messages are generated

  --help, -h  Print this help text.

EOF
}


## helper functions
die () {
  rc="$1"
  shift
  (echo -n "$me: ERROR: ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
  exit $rc
}

warn () {
  (echo -n "$me: WARNING: ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
}


## parse command-line

short_opts='h'
long_opts='help,quiet,list'

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
        --help|-h)
            usage
            exit 0
            ;;
        --list)
            # FIXME: According to the spec (see link 1. above), the `--list`
            # option should ''instead of verifying policy, list (in a "human
            # parseable" way) all policies defined for the given initscript id
            # (for all runlevels if no runlevels are specified; otherwise, list
            # it only for the runlevels specified), as well as all known actions
            # and their fallbacks for the given initscript id (note that actions
            # and fallback actions might be global and not particular to a
            # single initscript id).' This is a **substantial** change in
            # behavior, and one that is significantly harder to implement.
            die 102 "Option '--list' not implemented."
            ;;
        --quiet)
            # silence warnings
            warn() { :; }
            ;;
        --)
            shift
            break
            ;;
    esac
    shift
done


## main

case "$2" in
    *start*)
        warn "Automatic start of services prohibited by policy (see '/etc/policy-rc.d')"
        exit 101
        ;;
    *)
        # allow any other action (Debian's default)
        exit 0
        ;;
esac

# we should not get to this point; if it ever happens, it's a bug
# -- hence, "subsystem error"
exit 102
