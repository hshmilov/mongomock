#!/bin/bash

set -e

function finish {
    rm /tmp/install.lock
}

trap finish EXIT

cd /home/ubuntu
python3 ./axonius_install.py --first-time
cd cortex
./machine_boot.sh
cd ..
chown -R ubuntu:ubuntu cortex
rm -rf /home/ubuntu/axonius_install.py
