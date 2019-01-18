#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Creating venv"
python3 -m virtualenv --python=python3.6 venv

python3 ./devops/create_pth.py

source venv/bin/activate

echo "Installing python3 requirements"
pip install -r requirements.txt

# install axoniussdk
pip install -e api/axoniussdk/

# Most of our python2 code is in unit tests. so just use the actual file
echo "Installing python2 requirements"
pip2 install --user -r ./libs/axonius-base-image/requirements2.txt
