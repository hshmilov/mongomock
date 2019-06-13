#!/bin/bash
set -e

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "Downloading upgrade.."
cd /home/ubuntu/cortex
rm -rf ./adapters/tanium_adapter/connection.py.old
rm -rf ./adapters/tanium_adapter/service.py.old
rm -rf ./adapters/tanium_adapter/consts.py.old
mv ./adapters/tanium_adapter/connection.py ./adapters/tanium_adapter/connection.py.old
mv ./adapters/tanium_adapter/service.py ./adapters/tanium_adapter/service.py.old
mv ./adapters/tanium_adapter/consts.py ./adapters/tanium_adapter/consts.py.old
wget https://s3.us-east-2.amazonaws.com/axonius-releases/patches/06062019/tanium_adapter/connection.py -O ./adapters/tanium_adapter/connection.py
wget https://s3.us-east-2.amazonaws.com/axonius-releases/patches/06062019/tanium_adapter/service.py -O ./adapters/tanium_adapter/service.py
wget https://s3.us-east-2.amazonaws.com/axonius-releases/patches/06062019/tanium_adapter/consts.py -O ./adapters/tanium_adapter/consts.py

echo "Re-running tanium adapter..."
./axonius.sh adapter tanium up --restart --prod

echo "Done"
