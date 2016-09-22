# THIS FILE IS CONTROLLED BY ELASTICLUSTER
# local modifications will be overwritten
# the next time `elasticluster setup` is run!
#

# the `USER_IS_ROOT` env. var. is used in Lmod's
# initialization file; see: https://github.com/TACC/Lmod/issues/26
if [ $(id -u) -eq 0 ]; then
    export USER_IS_ROOT=1
fi
