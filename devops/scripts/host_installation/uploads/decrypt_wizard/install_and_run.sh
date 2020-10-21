#!/bin/bash

set -e
LOCKS_DIR=/tmp/ax-locks
INSTALL_LOCK=$LOCKS_DIR/install.lock

if [ -f $INSTALL_LOCK ]; then
    echo "install lock exists, exiting"
    exit 1
fi

function finish {
    rm $INSTALL_LOCK
}

trap finish EXIT

mkdir -p $LOCKS_DIR
touch $INSTALL_LOCK

DECRYPTION_KEY=$1
INSTALLER_NAME=axonius_install.py

gpg --batch --no-use-agent -dq -o "${INSTALLER_NAME}" --passphrase "${DECRYPTION_KEY}" version.zip
ls -la axonius_install.py
chmod +x axonius_install.py

cd /home/ubuntu
./axonius_install.py -- --first-time
cd cortex
./machine_boot.sh
cd devops/scripts/watchdog/
./run_host_tasks.sh
cd ../../../../
chown -R ubuntu:ubuntu cortex
rm -rf /home/ubuntu/axonius_install.py
