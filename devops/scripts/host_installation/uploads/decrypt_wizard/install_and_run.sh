#!/bin/bash

set -e

INSTALL_LOCK=/tmp/install.lock

if [ -f $INSTALL_LOCK ]; then
    echo "install lock exists, exiting"
    exit 1
fi

function finish {
    rm $INSTALL_LOCK
}

trap finish EXIT

touch $INSTALL_LOCK

DECRYPTION_KEY=$1
INSTALLER_NAME=axonius_install.py

sudo gpg --no-use-agent -dq -o "${INSTALLER_NAME}" --passphrase "${DECRYPTION_KEY}" version.zip
ls -la axonius_install.py

cd /home/ubuntu
python3 ./axonius_install.py --first-time
cd cortex
./machine_boot.sh
cd ..
chown -R ubuntu:ubuntu cortex
rm -rf /home/ubuntu/axonius_install.py
