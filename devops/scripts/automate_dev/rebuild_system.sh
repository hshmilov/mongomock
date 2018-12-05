#!/usr/bin/env bash

source clean_dockers.sh images
pip install -r requirements.txt
python "$CORTEX_ROOT"/devops/axonius_system.py system up --restart
python "$CORTEX_ROOT"/devops/axonius_system.py service gui up --restart --rebuild --hard --yes-hard
