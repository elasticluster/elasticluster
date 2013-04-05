#! /usr/bin/env python
#
#   Copyright (C) 2013 GC3, University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__author__ = 'Nicolas Baer <nicolas.baer@uzh.ch>'


from providers.cloud_providers import BotoCloudProvider
from conf import Configuration

class Cluster(object):
    """
    TODO: document
    """


    def __init__(self, name):
        self.name = name
        self._options = None
        
        
        
    def start(self):
        self._options = Configuration.Instance().read_cluster_section(self.name)
        
        
        
        # TODO: change this to be more flexible, e.g. use some sort of proxy
        provider = BotoCloudProvider()
        
        
        # TODO: where to read how many instances i should start?
        provider.start_instance(self.name, "compute")
        