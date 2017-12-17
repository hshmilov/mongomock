#!/usr/bin/env bash

source prepare_python_env.sh
cd "$(dirname "$0")"
cd devops
python3 axonius_system.py $@