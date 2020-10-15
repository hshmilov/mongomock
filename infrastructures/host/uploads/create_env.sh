#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Installing python3 requirements"
pip3 install -r /tmp/requirements.txt

# install axoniussdk
pip3 install -e /tmp/axoniussdk

# install ax_cli
pip3 install -e /tmp/ax_cli

# Most of our python2 code is in unit tests. so just use the actual file
echo "Installing python2 requirements"
pip2 install --user -r /tmp/requirements2.txt

# Hack to prevent import errors in python3.6
rm -f /usr/local/bin/*.pyc
mv /usr/local/bin/*.py /home/axonius/.local/lib/python2.7/site-packages
