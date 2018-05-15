# Ensure UID/GID in Docker container match those of outside environment
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#

import os
from os import chmod, chown, environ, getuid, makedirs, \
    setuid, setgid, stat, symlink, walk
from os.path import dirname, exists, join
from pwd import getpwuid


# read user and group ID of the configuration and storage directory
si = stat('/home/.elasticluster')
uid = si.st_uid
gid = si.st_gid

# ensure there is an /etc/passwd entry corresponding to this UID/GID
try:
    getpwuid(uid)
except KeyError:
    # create entry in /etc/passwd
    with open('/etc/passwd', 'a') as etc_passwd:
        etc_passwd.write(
            "{username}:x:{uid}:{gid}::/home:/bin/sh\n"
            .format(
                username=environ.get('USER', 'user'),
                uid=uid, gid=gid))

# ensure Ansible's work directory exists and is writable
ansible_d = '/home/.ansible'
if not exists(ansible_d):
    makedirs(ansible_d)
for rootdir, _, filenames in walk(ansible_d):
    chown(rootdir, uid, gid)
    chmod(rootdir, 0o755)
    for filename in filenames:
        path = join(rootdir, filename)
        chown(path, uid, gid)
        chmod(path, 0o755)

# symlink outside home path to /home, so that path names embedded in
# conf files (e.g. `~/.ssh/config`) continue to work
home = environ.get('HOME', '/home')
if home != '/home':
    if not exists(home):
        parent = dirname(home)
        if not exists(parent):
            makedirs(dirname(home))
        symlink('/home', home)

# ensure we can use the SSH agent if present
if exists('/home/.ssh-agent.sock'):
    environ['SSH_AUTH_SOCK'] = '/home/.ssh-agent.sock'

# set real and effective user ID so that we can read/write in there
if uid != getuid():
    setgid(gid)
    setuid(uid)
