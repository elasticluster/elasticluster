#!/usr/bin/env python
# -*- coding: utf-8 -*-# 
# @(#)gc3_config.py
# 
# 
# Copyright (C) 2013, GC3, University of Zurich. All rights reserved.
# 
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

__docformat__ = 'reStructuredText'
__author__ = 'Antonio Messina <antonio.s.messina@gmail.com>'

from ConfigParser import RawConfigParser
import re
from StringIO import StringIO

from elasticluster import log

# NODELIST          NODES PARTITION       STATE CPUS    S:C:T MEMORY TMP_DISK WEIGHT FEATURES REASON
# compute[001-002]      2    cloud*        idle    1    1:1:1    491     5026      1   (null) none
slurm_sinfo_regexp =  re.compile('^(?P<hostnames>[^ \t]+)\s+'
                                 '(?P<num>[0-9]+)\s+'
                                 '(?P<partition>[^ \t]+)\s+'
                                 '(?P<state>[^ \t]+)\s+'
                                 '(?P<cpus>[0-9]+)\s+'
                                 '(?P<S>[0-9]+):(?P<C>[0-9]+):(?P<T>[0-9]+)\s+'
                                 '(?P<memory>[0-9]+)\s+'
                                 '(?P<tmp_disk>[0-9]+)\s+'
                                 '(?P<weight>[0-9]+)\s+'
                                 '(?P<features>[^ ]+)\s+'
                                 '(?P<reason>[^ \t]+)')

slurm_scontrol_maxtime_regexp = re.compile('.*\sMaxTime=(?P<MaxTime>[^ \t]+)\s+')

def inspect_slurm_cluster(ssh, node_information):
    (_in, _out, _err) = ssh.exec_command("sinfo -Nel")
    # Skip all lines until we catch the header
    for line in _out:
        if line.startswith('NODELIST'):
            break

    nodes = []
    for line in _out:
        match = slurm_sinfo_regexp.match(line)
        if match:
            num_nodes = int(match.group('num'))
            num_cores = int(match.group('cpus')) * num_nodes
            memory = int(match.group('memory')) * num_nodes
            memory_per_core = float(match.group('memory')) / num_cores
            nodes.append([num_nodes, num_cores, memory, memory_per_core])
        else:
            log.warning("Unable to parse output of sinfo: following line doesn't match node regexp: '%s'" % line.strip())
    node_information['num_nodes'] = sum(i[0] for i in nodes)
    node_information['max_cores'] = sum(i[1] for i in nodes)
    node_information['max_cores_per_job'] = max(i[1] for i in nodes)
    node_information['max_memory_per_core'] = max(i[2] for i in nodes)

    (_in, _out, _err) = ssh.exec_command("scontrol -o show part")
    # Assuming only one partition
    line = _out.read()
    match = slurm_scontrol_maxtime_regexp.match(line)
    node_information['max_walltime'] = '672hours'
    if match:
        maxtime = match.group('MaxTime')
        if maxtime != 'UNLIMITED':
            node_information['max_walltime'] = maxtime
    
    return node_information


def inspect_pbs_cluster(ssh):
    pass


def inspect_node(node):
    """
    This function accept a `elasticluster.cluster.Node` class,
    connects to a node and tries to discover the kind of batch system
    installed, and some other information.
    """
    node_information = {}
    ssh = node.connect()
    
    (_in, _out, _err) = ssh.exec_command("(type >& /dev/null -a srun && echo slurm) \
                      || (type >& /dev/null -a qconf && echo sge) \
                      || (type >& /dev/null -a pbsnodes && echo pbs) \
                      || echo UNKNOWN")
    node_information['type'] = _out.read().strip()

    (_in, _out, _err) = ssh.exec_command("arch")
    node_information['architecture'] = _out.read().strip()

    if node_information['type'] == 'slurm':
        inspect_slurm_cluster(ssh, node_information)
    ssh.close()
    return node_information

def create_gc3_config_snippet(cluster):
    """
    Create a configuration file snippet to be used with GC3Pie.
    """
    auth_section = 'auth/elasticluster_%s' % cluster.name
    resource_section = 'resource/elasticluster_%s' % cluster.name

    cfg = RawConfigParser()
    cfg.add_section(auth_section)

    frontend_node = cluster.get_frontend_node()
    cfg.set(auth_section, 'type', 'ssh')
    cfg.set(auth_section, 'username', frontend_node.image_user)

    cluster_info = inspect_node(frontend_node)
    cfg.add_section(resource_section)
    cfg.set(resource_section, 'enabled', 'yes')
    cfg.set(resource_section, 'transport', 'ssh')
    cfg.set(resource_section, 'frontend', frontend_node.preferred_ip)
    cfg.set(resource_section, 'type', cluster_info['type'])
    cfg.set(resource_section, 'architecture', cluster_info['architecture'])
    cfg.set(resource_section, 'max_cores', cluster_info.get('max_cores', 1))
    cfg.set(resource_section, 'max_cores_per_job', cluster_info.get('max_cores_per_job', 1))
    cfg.set(resource_section, 'max_memory_per_core', cluster_info.get('max_memory_per_core', '2GB'))
    cfg.set(resource_section, 'max_walltime', cluster_info.get('max_walltime', '672hours'))
    
    cfgstring = StringIO()
    cfg.write(cfgstring)

    return cfgstring.getvalue()
    
