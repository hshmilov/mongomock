#! /usr/bin/env bash
# This script runs as a prescript for this docker image.
# For more information: https://github.com/tiangolo/uwsgi-nginx-flask-docker/blob/master/python3.7/start.sh

# Run mongodb
mkdir -p /data/db
mongod &
