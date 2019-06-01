#!/bin/bash
# A boilerplate for upgrade commands (upgrading specific files)
set -e

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "Downloading upgrade.."
cd /home/ubuntu/cortex
rm -rf ./adapters/crowd_strike_adapter/connection.py.old
mv ./adapters/crowd_strike_adapter/connection.py ./adapters/crowd_strike_adapter/connection.py.old
wget https://s3.us-east-2.amazonaws.com/axonius-releases/patches/31052019/crowd_strike_adapter/connection.py -O ./adapters/crowd_strike_adapter/connection.py

echo "Re-running crowdstrike adapter..."
./axonius.sh adapter crowd_strike up --restart --prod

echo "Done"
