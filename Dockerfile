#
# Dockerfile for ElastiCluster
#
# Originally contributed by Hatef Monajemi, 2017
# (see https://github.com/gc3-uzh-ch/elasticluster/pull/504#issuecomment-343693251)
#

################################################
# Install python
# install gcc compiler
################################################
From python:2.7-slim
RUN apt-get update \
        && apt-get install -y build-essential vim

#################################################
# add everything from Dockerfile's directory
# to container's elasticluster dir
#################################################
COPY elasticluster-feature-gpus-on-google-cloud/ /elasticluster/


###############################
# Install ElastiCluster
###############################
WORKDIR /elasticluster/src
RUN pip install -e .
WORKDIR /


####################################################################
# Make ports 80 available to the world outside this container
####################################################################
EXPOSE 80


##########################################
# create an empty file ~/.ssh/id_rsa.pub
# elasticluster requires ~/.ssh/id_rsa.pub
##########################################
RUN mkdir ~/.ssh \
        && touch ~/.ssh/id_rsa \
        && touch ~/.ssh/id_rsa.pub

#####################
# set the config file
#####################
RUN elasticluster list-templates
RUN cp /elasticluster/config-template-gce-gpu ~/.elasticluster/config

ENTRYPOINT /bin/bash
