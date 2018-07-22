#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

python3 -m virtualenv --python=python3 venv

python3 ./devops/create_pth.py

source venv/bin/activate

echo "Installing python3 requirements"
sudo apt-get install -y python3.6-dev
pip install -r requirements.txt

# Most of our python2 code is in unit tests. so just use the actual file
echo "Installing python2 requirements"
pip2 install --user -r ./libs/axonius-base-image/requirements2.txt