#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../../"
cd $CORTEX_ROOT
source clean_dockers.sh images
pip install -r requirements.txt
python "$CORTEX_ROOT"/devops/axonius_system.py system up --restart
python "$CORTEX_ROOT"/devops/axonius_system.py service gui up --restart --rebuild --hard --yes-hard
