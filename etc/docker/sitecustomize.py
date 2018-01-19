# Ensure UID/GID in Docker container match those of outside environment
#
# Copyright (c) 2018 Riccardo Murri <riccardo.murri@gmail.com>
# Originally contributed by Hatef Monajemi, 2017
# (see https://github.com/gc3-uzh-ch/elasticluster/pull/504#issuecomment-343693251)
#
# This file is part of ElastiCluster.  It can be distributed and
# modified under the same conditions as ElastiCluster.
#

import os
import pwd

# read user and group ID of the configuration and storage directory
si = os.stat('/home/.elasticluster')
uid = si.st_uid
gid = si.st_gid

try:
    pwd.getpwuid(uid)
except KeyError:
    # create entry in /etc/passwd
    with open('/etc/passwd', 'a') as etc_passwd:
        etc_passwd.write(
            "{username}:x:{uid}:{gid}::/home:/bin/sh\n"
            .format(
                username=os.environ.get('USER', 'user'),
                uid=uid, gid=gid))

# set real and effective user ID so that we can read/write in there
if uid != os.getgid():
    os.setgid(gid)
    os.setuid(uid)

# ensure we can use the SSH agent if present
if os.path.exists('/home/.ssh-agent.sock'):
    os.environ['SSH_AUTH_SOCK'] = '/home/.ssh-agent.sock'
